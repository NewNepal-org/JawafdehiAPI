from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from django.contrib.auth.models import AnonymousUser, User
from django.db.models import QuerySet

from .models import AccessLevel, KnowledgeChunk, KnowledgeCollection, KnowledgeSource

TOKEN_RE = re.compile(r"[\w\u0900-\u097F]+", flags=re.UNICODE)


@dataclass(frozen=True)
class KnowledgeAccessContext:
    """Who is retrieving knowledge."""

    user: User | AnonymousUser | None = None
    public: bool = False

    @classmethod
    def public_context(cls) -> "KnowledgeAccessContext":
        return cls(user=None, public=True)


@dataclass(frozen=True)
class RetrievedKnowledgeChunk:
    chunk: KnowledgeChunk
    score: float

    def as_evidence(self) -> dict:
        source = self.chunk.source
        collection = source.collection
        return {
            "chunk_id": self.chunk.id,
            "document_id": source.id,
            "collection_id": collection.id,
            "collection_name": collection.name,
            "source_id": source.id,
            "source_title": source.title,
            "source_type": source.source_type,
            "source_url": source.source_url,
            "storage_path": source.storage_path,
            "page_start": self.chunk.page_start,
            "page_end": self.chunk.page_end,
            "section_title": self.chunk.section_title,
            "table_title": self.chunk.table_title,
            "text": self.chunk.text,
            "score": self.score,
            "metadata": {
                "source": source.metadata,
                "chunk": self.chunk.metadata,
            },
        }


class KnowledgeRetriever:
    """Simple lexical retriever used by public chat and future internal chat."""

    def retrieve(
        self,
        *,
        query: str,
        access_context: KnowledgeAccessContext,
        collections: Iterable[KnowledgeCollection] | QuerySet[KnowledgeCollection] = (),
        max_results: int = 5,
    ) -> list[RetrievedKnowledgeChunk]:
        max_results = max(1, max_results)
        query_tokens = _tokens(query)
        if not query_tokens:
            return []

        chunks = self._base_queryset(collections)
        if access_context.public:
            chunks = self._public_queryset(chunks)
        else:
            chunks = self._user_queryset(chunks, access_context.user)

        ranked: list[RetrievedKnowledgeChunk] = []
        for chunk in chunks[:1000]:
            score = _score(query_tokens, chunk)
            if score > 0:
                ranked.append(RetrievedKnowledgeChunk(chunk=chunk, score=score))

        ranked.sort(
            key=lambda item: (
                item.score,
                item.chunk.source.collection.name,
                -item.chunk.chunk_index,
            ),
            reverse=True,
        )
        return ranked[:max_results]

    def _base_queryset(
        self,
        collections: Iterable[KnowledgeCollection] | QuerySet[KnowledgeCollection],
    ) -> QuerySet[KnowledgeChunk]:
        chunks = KnowledgeChunk.objects.select_related("source", "source__collection")
        if collections:
            collection_ids = [collection.id for collection in collections]
            chunks = chunks.filter(source__collection_id__in=collection_ids)
        return chunks.filter(source__is_active=True, source__collection__is_active=True)

    def _public_queryset(
        self, chunks: QuerySet[KnowledgeChunk]
    ) -> QuerySet[KnowledgeChunk]:
        return chunks.filter(
            source__access_level=AccessLevel.PUBLIC,
            source__collection__access_level=AccessLevel.PUBLIC,
        )

    def _user_queryset(
        self, chunks: QuerySet[KnowledgeChunk], user: User | AnonymousUser | None
    ) -> QuerySet[KnowledgeChunk]:
        if user is None or not getattr(user, "is_authenticated", False):
            return chunks.none()

        if _is_admin_or_moderator(user):
            return chunks

        allowed_source_ids = [
            source.id
            for source in KnowledgeSource.objects.select_related(
                "case", "document_source"
            ).prefetch_related("allowed_users", "allowed_groups")
            if _can_user_access_source(user, source)
        ]
        return chunks.filter(source_id__in=allowed_source_ids)


def _tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_RE.findall(text or "")
        if len(token) > 1 or token.isdigit()
    }


def _score(query_tokens: set[str], chunk: KnowledgeChunk) -> float:
    chunk_tokens = _tokens(
        " ".join(
            [
                chunk.source.title,
                chunk.source.collection.display_name,
                chunk.section_title,
                chunk.table_title,
                chunk.text,
            ]
        )
    )
    overlap = query_tokens & chunk_tokens
    if not overlap:
        return 0.0

    exact_bonus = 0.0
    lowered_text = chunk.text.lower()
    for token in query_tokens:
        if token in lowered_text:
            exact_bonus += 0.1

    return float(len(overlap)) + exact_bonus


def _is_admin_or_moderator(user: User) -> bool:
    return (
        user.is_superuser
        or user.groups.filter(name__in=["Admin", "Moderator"]).exists()
    )


def _can_user_access_source(user: User, source: KnowledgeSource) -> bool:
    if (
        source.access_level == AccessLevel.PUBLIC
        and source.collection.access_level == AccessLevel.PUBLIC
    ):
        return True
    if source.owner_id == user.id:
        return True
    if source.allowed_users.filter(id=user.id).exists():
        return True
    if source.allowed_groups.filter(user=user).exists():
        return True
    if source.case_id and source.case.contributors.filter(id=user.id).exists():
        return True
    if (
        source.document_source_id
        and source.document_source.contributors.filter(id=user.id).exists()
    ):
        return True
    if source.document_source_id and _document_source_linked_to_user_case(
        user, source.document_source.source_id
    ):
        return True
    return False


def _document_source_linked_to_user_case(user: User, source_id: str) -> bool:
    from cases.models import Case

    for case in Case.objects.filter(contributors=user).only("evidence"):
        for evidence_item in case.evidence or []:
            if (
                isinstance(evidence_item, dict)
                and evidence_item.get("source_id") == source_id
            ):
                return True
    return False
