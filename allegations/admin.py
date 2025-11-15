from django.contrib import admin
from django import forms
from .models import Allegation, Response, DocumentSource, Evidence


class DocumentSourceAdminForm(forms.ModelForm):
    related_entity_ids_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "entity-id-1\nentity-id-2"}),
        help_text="Enter one entity ID per line",
        required=False,
        label="Related Entity IDs"
    )
    
    class Meta:
        model = DocumentSource
        fields = "__all__"
        exclude = ["related_entity_ids"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["related_entity_ids_text"].initial = "\n".join(self.instance.related_entity_ids)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        entity_ids = self.cleaned_data.get("related_entity_ids_text", "")
        instance.related_entity_ids = [e.strip() for e in entity_ids.split("\n") if e.strip()]
        if commit:
            instance.save()
        return instance


class AllegationAdminForm(forms.ModelForm):
    alleged_entities_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 5, "placeholder": "rabi-lamichhane\nkp-sharma-oli"}),
        help_text="Enter one entity ID per line",
        required=False,
        label="Alleged Entities"
    )
    related_entities_text = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "rastriya-swatantra-party"}),
        help_text="Enter one entity ID per line",
        required=False,
        label="Related Entities"
    )
    
    class Meta:
        model = Allegation
        fields = "__all__"
        exclude = ["alleged_entities", "related_entities"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["alleged_entities_text"].initial = "\n".join(self.instance.alleged_entities)
            self.fields["related_entities_text"].initial = "\n".join(self.instance.related_entities)
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        alleged = self.cleaned_data.get("alleged_entities_text", "")
        related = self.cleaned_data.get("related_entities_text", "")
        instance.alleged_entities = [e.strip() for e in alleged.split("\n") if e.strip()]
        instance.related_entities = [e.strip() for e in related.split("\n") if e.strip()]
        if commit:
            instance.save()
        return instance


class EvidenceInline(admin.TabularInline):
    model = Evidence
    extra = 1
    readonly_fields = ["evidence_id"]
    autocomplete_fields = ["source"]


@admin.register(DocumentSource)
class DocumentSourceAdmin(admin.ModelAdmin):
    form = DocumentSourceAdminForm
    list_display = ["source_id", "title", "source_type"]
    list_filter = ["source_type"]
    search_fields = ["source_id", "title", "description"]
    readonly_fields = ["source_id"]


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ["evidence_id", "allegation", "source", "order"]
    list_filter = ["allegation"]
    search_fields = ["evidence_id", "allegation__title", "source__title"]
    readonly_fields = ["evidence_id"]


@admin.register(Allegation)
class AllegationAdmin(admin.ModelAdmin):
    form = AllegationAdminForm
    inlines = [EvidenceInline]
    list_display = ["title", "allegation_type", "state", "status", "created_at"]
    list_filter = ["allegation_type", "state", "status"]
    search_fields = ["title", "description", "key_allegations"]
    readonly_fields = ["created_at"]
    fieldsets = [
        ("Basic Info", {"fields": ["allegation_type", "state", "title"]}),
        ("Entities", {"fields": ["alleged_entities_text", "related_entities_text", "location_id"]}),
        ("Content", {"fields": ["description", "key_allegations"]}),
        ("Status", {"fields": ["status", "first_public_date"]}),
        ("Timeline", {"fields": ["timeline"]}),
        ("Audit", {"fields": ["created_at", "modification_trail"]}),
    ]


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ["allegation", "entity_id", "submitted_at", "verified_at"]
    list_filter = ["verified_at"]
    search_fields = ["response_text", "entity_id"]
    readonly_fields = ["submitted_at"]
