from django.contrib import admin
from django import forms
from tinymce.widgets import TinyMCE
from .models import Allegation, Response, DocumentSource, Modification
from .widgets import MultiEntityIDField, MultiTextField

admin.site.site_header = "Jawafdehi Mgmt"
admin.site.site_title = "Jawafdehi Management Portal"
admin.site.index_title = "Welcome to Jawafdehi Management Portal"


class DocumentSourceAdminForm(forms.ModelForm):
    related_entity_ids = MultiEntityIDField(
        required=False,
        label="Related Entity IDs"
    )
    
    class Meta:
        model = DocumentSource
        fields = "__all__"


class AllegationAdminForm(forms.ModelForm):
    alleged_entities = MultiEntityIDField(
        required=True,
        label="Alleged Entities"
    )
    related_entities = MultiEntityIDField(
        required=False,
        label="Related Entities"
    )
    key_allegations = MultiTextField(
        required=True,
        label="Key Allegations"
    )
    description = forms.CharField(widget=TinyMCE())
    state = forms.ChoiceField(
        choices=Allegation.STATE_CHOICES,
        widget=forms.RadioSelect
    )
    
    class Meta:
        model = Allegation
        fields = "__all__"


class ModificationInline(admin.TabularInline):
    model = Modification
    extra = 1
    fields = ["action", "user", "timestamp", "notes"]
    readonly_fields = ["action", "user", "timestamp"]
    can_delete = False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-timestamp')


@admin.register(DocumentSource)
class DocumentSourceAdmin(admin.ModelAdmin):
    form = DocumentSourceAdminForm
    list_display = ["source_id", "title", "source_type"]
    list_filter = ["source_type"]
    search_fields = ["source_id", "title", "description"]
    readonly_fields = ["source_id"]


@admin.register(Allegation)
class AllegationAdmin(admin.ModelAdmin):
    form = AllegationAdminForm
    inlines = [ModificationInline]
    list_display = ["title", "allegation_type", "state", "created_at"]
    list_filter = ["allegation_type", "state"]
    search_fields = ["title", "description", "key_allegations"]
    readonly_fields = ["created_at"]
    fieldsets = [
        ("Basic Info", {"fields": ["allegation_type", "state", "title", "case_date", "created_at"]}),
        ("Entities", {"fields": ["alleged_entities", "related_entities", "location_id"]}),
        ("Content", {"fields": ["key_allegations", "description", "timeline", "evidence"]}),
    ]
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, Modification) and not instance.pk:
                instance.user = request.user
                instance.action = "updated"
                instance.save()
        formset.save_m2m()


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ["allegation", "entity_id", "submitted_at", "verified_at"]
    list_filter = ["verified_at"]
    search_fields = ["response_text", "entity_id"]
    readonly_fields = ["submitted_at"]
