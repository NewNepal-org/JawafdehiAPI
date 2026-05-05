import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError

from knowledge.models import (
    AccessLevel,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeSource,
)
from knowledge.retrieval import KnowledgeAccessContext, KnowledgeRetriever

User = get_user_model()


def create_user_with_role(username, email, role):
    user = User.objects.create_user(username=username, email=email, password="testpass")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.add(group)
    if role in {"Admin", "Moderator", "Contributor"}:
        user.is_staff = True
    if role == "Admin":
        user.is_superuser = True
    user.save()
    return user


def make_collection(**overrides):
    data = {
        "name": "annual_reports",
        "display_name": "Annual Reports",
        "description": "CIAA annual reports",
    }
    data.update(overrides)
    return KnowledgeCollection.objects.create(**data)


def make_source(collection, **overrides):
    data = {
        "collection": collection,
        "title": "Annual Report 2079",
        "source_type": "annual_report",
    }
    data.update(overrides)
    return KnowledgeSource.objects.create(**data)


def make_chunk(source, **overrides):
    data = {
        "source": source,
        "chunk_index": 0,
        "text": "In fiscal year 2079, 120 corruption cases were registered.",
        "content_hash": "hash-2079-0",
    }
    data.update(overrides)
    return KnowledgeChunk.objects.create(**data)


@pytest.mark.django_db
def test_knowledge_defaults_private():
    collection = make_collection()
    source = make_source(collection)

    assert collection.access_level == AccessLevel.PRIVATE
    assert source.access_level == AccessLevel.PRIVATE


@pytest.mark.django_db
def test_public_retrieval_only_uses_public_active_configured_collections():
    configured = make_collection(access_level=AccessLevel.PUBLIC)
    configured_source = make_source(
        configured,
        access_level=AccessLevel.PUBLIC,
        source_url="https://jawafdehi.org/reports/2079.pdf",
    )
    make_chunk(configured_source, text="2079 annual report registered 120 cases.")

    unconfigured = make_collection(
        name="faq", display_name="FAQ", access_level=AccessLevel.PUBLIC
    )
    unconfigured_source = make_source(
        unconfigured,
        title="FAQ",
        access_level=AccessLevel.PUBLIC,
        source_url="https://jawafdehi.org/faq",
    )
    make_chunk(
        unconfigured_source,
        text="2079 annual report registered 999 cases.",
        content_hash="hash-faq",
    )

    private_collection = make_collection(
        name="internal", display_name="Internal", access_level=AccessLevel.PRIVATE
    )
    private_source = make_source(private_collection, title="Private report")
    make_chunk(
        private_source,
        text="2079 annual report registered 888 private cases.",
        content_hash="hash-private",
    )

    results = KnowledgeRetriever().retrieve(
        query="2079 annual report registered cases",
        access_context=KnowledgeAccessContext.public_context(),
        collections=KnowledgeCollection.objects.filter(id=configured.id),
        max_results=5,
    )

    assert [result.chunk.source_id for result in results] == [configured_source.id]


@pytest.mark.django_db
def test_anonymous_cannot_retrieve_private_chunks():
    collection = make_collection()
    source = make_source(collection)
    make_chunk(source)

    results = KnowledgeRetriever().retrieve(
        query="2079 corruption cases",
        access_context=KnowledgeAccessContext.public_context(),
        collections=KnowledgeCollection.objects.filter(id=collection.id),
        max_results=5,
    )

    assert results == []


@pytest.mark.django_db
def test_admin_and_contributor_access_private_knowledge_by_role_or_share():
    collection = make_collection()
    source = make_source(collection)
    make_chunk(source)
    admin = create_user_with_role("admin", "admin@example.com", "Admin")
    contributor = create_user_with_role(
        "contributor", "contributor@example.com", "Contributor"
    )
    outsider = create_user_with_role("outsider", "outsider@example.com", "Contributor")
    source.allowed_users.add(contributor)

    admin_results = KnowledgeRetriever().retrieve(
        query="2079 corruption cases",
        access_context=KnowledgeAccessContext(user=admin),
        collections=KnowledgeCollection.objects.filter(id=collection.id),
        max_results=5,
    )
    contributor_results = KnowledgeRetriever().retrieve(
        query="2079 corruption cases",
        access_context=KnowledgeAccessContext(user=contributor),
        collections=KnowledgeCollection.objects.filter(id=collection.id),
        max_results=5,
    )
    outsider_results = KnowledgeRetriever().retrieve(
        query="2079 corruption cases",
        access_context=KnowledgeAccessContext(user=outsider),
        collections=KnowledgeCollection.objects.filter(id=collection.id),
        max_results=5,
    )

    assert [result.chunk.source_id for result in admin_results] == [source.id]
    assert [result.chunk.source_id for result in contributor_results] == [source.id]
    assert outsider_results == []


@pytest.mark.django_db
def test_import_knowledge_artifacts_is_idempotent(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    chunks_path = tmp_path / "chunks.json"
    chunks_path.write_text(
        json.dumps(
            [
                {
                    "text": "Annual report 2079 registered 120 cases.",
                    "chunk_index": 0,
                    "page_start": 12,
                    "page_end": 12,
                    "section_title": "Registered cases",
                    "embedding_model": "test-embedding",
                    "embedding": [0.1, 0.2, 0.3],
                }
            ]
        ),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "collection": {
                    "name": "annual_reports",
                    "display_name": "Annual Reports",
                    "access_level": "public",
                },
                "source": {
                    "title": "Annual Report 2079",
                    "source_type": "annual_report",
                    "access_level": "public",
                    "source_url": "https://jawafdehi.org/reports/2079.pdf",
                    "checksum": "checksum-2079",
                },
                "chunks_file": "chunks.json",
            }
        ),
        encoding="utf-8",
    )

    call_command("import_knowledge_artifacts", str(manifest_path))
    call_command("import_knowledge_artifacts", str(manifest_path))

    assert KnowledgeCollection.objects.count() == 1
    assert KnowledgeSource.objects.count() == 1
    assert KnowledgeChunk.objects.count() == 1
    chunk = KnowledgeChunk.objects.get()
    assert chunk.page_start == 12
    assert chunk.embeddings.get().dimensions == 3


@pytest.mark.django_db
def test_import_rejects_public_sources_without_citation_target(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "collection": {"name": "annual_reports", "access_level": "public"},
                "source": {
                    "title": "Annual Report 2079",
                    "access_level": "public",
                },
                "chunks": [{"text": "Report text"}],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CommandError, match="require source_url or storage_path"):
        call_command("import_knowledge_artifacts", str(manifest_path))
