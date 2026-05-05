from django.contrib import admin

from .models import (
    KnowledgeChunk,
    KnowledgeCollection,
    KnowledgeEmbedding,
    KnowledgeSource,
)


@admin.register(KnowledgeCollection)
class KnowledgeCollectionAdmin(admin.ModelAdmin):
    list_display = ["name", "display_name", "access_level", "is_active", "updated_at"]
    list_filter = ["access_level", "is_active"]
    search_fields = ["name", "display_name", "description"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(KnowledgeSource)
class KnowledgeSourceAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "collection",
        "source_type",
        "access_level",
        "is_active",
        "owner",
        "updated_at",
    ]
    list_filter = ["access_level", "is_active", "source_type", "collection"]
    search_fields = ["title", "checksum", "source_url", "storage_path"]
    autocomplete_fields = ["collection", "owner", "allowed_users", "allowed_groups"]
    filter_horizontal = ["allowed_users", "allowed_groups"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = [
        "source",
        "chunk_index",
        "page_start",
        "page_end",
        "section_title",
        "table_title",
    ]
    list_filter = ["source__collection", "source__access_level", "source__is_active"]
    search_fields = ["text", "section_title", "table_title", "content_hash"]
    autocomplete_fields = ["source"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(KnowledgeEmbedding)
class KnowledgeEmbeddingAdmin(admin.ModelAdmin):
    list_display = ["chunk", "embedding_model", "dimensions", "updated_at"]
    list_filter = ["embedding_model", "dimensions"]
    search_fields = ["chunk__source__title", "embedding_model"]
    autocomplete_fields = ["chunk"]
    readonly_fields = ["created_at", "updated_at"]
