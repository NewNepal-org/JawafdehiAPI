from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from knowledge.models import (
    AccessLevel,
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeEmbedding,
    KnowledgeSource,
)


class Command(BaseCommand):
    help = "Import generic knowledge artifacts from a JSON manifest."

    def add_arguments(self, parser):
        parser.add_argument("manifest", help="Path to a knowledge artifact manifest")

    def handle(self, *args, **options):
        manifest_path = Path(options["manifest"]).resolve()
        if not manifest_path.is_file():
            raise CommandError(f"Manifest not found: {manifest_path}")

        manifest = _load_json(manifest_path)
        base_dir = manifest_path.parent

        collection = self._upsert_collection(manifest)
        source = self._upsert_source(manifest, collection)
        chunks = self._load_chunks(manifest, base_dir)

        imported = 0
        for index, row in enumerate(chunks):
            chunk = self._upsert_chunk(source, row, index)
            self._upsert_embedding(chunk, row)
            imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported} chunks into {collection.name}/{source.id}"
            )
        )

    def _upsert_collection(self, manifest: dict[str, Any]) -> KnowledgeCollection:
        collection_data = manifest.get("collection")
        if isinstance(collection_data, str):
            collection_payload = {"name": collection_data}
        elif isinstance(collection_data, dict):
            collection_payload = collection_data
        else:
            raise CommandError(
                "Manifest must include collection as a string or object."
            )

        name = collection_payload.get("name")
        if not name:
            raise CommandError("Collection name is required.")

        defaults = {
            "display_name": collection_payload.get("display_name")
            or name.replace("_", " ").title(),
            "description": collection_payload.get("description", ""),
            "access_level": collection_payload.get("access_level", AccessLevel.PRIVATE),
            "is_active": collection_payload.get("is_active", True),
        }
        _validate_access(defaults["access_level"], "collection.access_level")

        collection, _ = KnowledgeCollection.objects.update_or_create(
            name=name,
            defaults=defaults,
        )
        return collection

    def _upsert_source(
        self, manifest: dict[str, Any], collection: KnowledgeCollection
    ) -> KnowledgeSource:
        source_payload = manifest.get("source")
        if not isinstance(source_payload, dict):
            raise CommandError("Manifest must include source as an object.")

        title = source_payload.get("title")
        if not title:
            raise CommandError("Source title is required.")

        access_level = source_payload.get("access_level", AccessLevel.PRIVATE)
        _validate_access(access_level, "source.access_level")

        source_url = source_payload.get("source_url") or source_payload.get("url") or ""
        storage_path = source_payload.get("storage_path") or ""
        if access_level == AccessLevel.PUBLIC and not (source_url or storage_path):
            raise CommandError(
                "Public knowledge sources require source_url or storage_path for citations."
            )

        checksum = source_payload.get("checksum") or ""
        lookup = {"collection": collection, "checksum": checksum} if checksum else None
        if lookup is None:
            lookup = {"collection": collection, "title": title}

        source, _ = KnowledgeSource.objects.update_or_create(
            **lookup,
            defaults={
                "title": title,
                "source_type": source_payload.get("source_type", "document"),
                "source_url": source_url,
                "storage_path": storage_path,
                "metadata": source_payload.get("metadata", {}),
                "access_level": access_level,
                "is_active": source_payload.get("is_active", True),
            },
        )
        return source

    def _load_chunks(
        self, manifest: dict[str, Any], base_dir: Path
    ) -> list[dict[str, Any]]:
        if isinstance(manifest.get("chunks"), list):
            chunks = manifest["chunks"]
        elif manifest.get("chunks_file"):
            chunks_file = (base_dir / manifest["chunks_file"]).resolve()
            chunks = _load_json(chunks_file)
        else:
            raise CommandError("Manifest must include chunks or chunks_file.")

        if not isinstance(chunks, list):
            raise CommandError("Knowledge chunks must be a list.")
        return chunks

    def _upsert_chunk(
        self, source: KnowledgeSource, row: dict[str, Any], index: int
    ) -> KnowledgeChunk:
        if not isinstance(row, dict):
            raise CommandError(f"Chunk {index} must be an object.")

        text = str(row.get("text") or row.get("content") or "").strip()
        if not text:
            raise CommandError(f"Chunk {index} is missing text.")

        content_hash = row.get("content_hash") or _hash_text(text)
        chunk_index = int(row.get("chunk_index", index))
        defaults = {
            "text": text,
            "chunk_index": chunk_index,
            "page_start": _int_or_none(row.get("page_start") or row.get("page")),
            "page_end": _int_or_none(row.get("page_end") or row.get("page")),
            "section_title": row.get("section_title", ""),
            "table_title": row.get("table_title", ""),
            "metadata": row.get("metadata", {}),
        }
        chunk, _ = KnowledgeChunk.objects.update_or_create(
            source=source,
            chunk_index=chunk_index,
            defaults=defaults | {"content_hash": content_hash},
        )
        return chunk

    def _upsert_embedding(self, chunk: KnowledgeChunk, row: dict[str, Any]) -> None:
        embedding = row.get("embedding")
        if not embedding:
            return
        model = row.get("embedding_model") or "unknown"
        KnowledgeEmbedding.objects.update_or_create(
            chunk=chunk,
            embedding_model=model,
            defaults={
                "embedding": embedding,
                "vector": embedding,
                "dimensions": len(embedding),
                "metadata": row.get("embedding_metadata", {}),
            },
        )


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CommandError(f"Invalid JSON in {path}: {exc}") from exc


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _int_or_none(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _validate_access(value: str, path: str) -> None:
    if value not in {AccessLevel.PRIVATE, AccessLevel.PUBLIC}:
        raise CommandError(f"{path} must be one of: private, public.")
