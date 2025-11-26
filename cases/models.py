from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from datetime import datetime
import uuid
from nes.core.identifiers.validators import validate_entity_id


class DocumentSource(models.Model):
    SOURCE_TYPE_CHOICES = [
        ("government", "Government"),
        ("ngo", "NGO"),
        ("social_media", "Social Media"),
        ("media", "Media"),
        ("crowdsourced", "Crowdsourced"),
        ("other", "Other"),
    ]
    
    source_id = models.CharField(max_length=100, unique=True, editable=False)
    title = models.CharField(max_length=300)
    description = models.TextField()
    url = models.URLField(blank=True, null=True)
    source_type = models.CharField(max_length=50, choices=SOURCE_TYPE_CHOICES)
    related_entity_ids = models.JSONField(default=list)
    case = models.ForeignKey('Allegation', on_delete=models.CASCADE, related_name='documents', null=True, blank=True)
    
    class Meta:
        permissions = [
            ('add_document', 'Can add document'),
            ('change_document', 'Can change document'),
            ('delete_document', 'Can delete document'),
        ]
    
    def clean(self):
        for entity_id in self.related_entity_ids:
            validate_entity_id(entity_id)
    
    def save(self, *args, **kwargs):
        if not self.source_id:
            date_str = datetime.now().strftime("%Y%m%d")
            uuid_str = str(uuid.uuid4())[:8]
            self.source_id = f"source:{date_str}:{uuid_str}"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title


class Allegation(models.Model):
    TYPE_CHOICES = [
        ("corruption", "Corruption"),
        ("misconduct", "Misconduct"),
        ("breach_of_trust", "Breach of Trust"),
        ("broken_promise", "Broken Promise"),
        ("media_trial", "Media Trial"),
    ]
    
    STATUS_CHOICES = [
        ("under_investigation", "Under Investigation"),
        ("closed", "Closed"),
    ]
    
    STATE_CHOICES = [
        ("draft", "Draft"),
        ("in_review", "In Review"),
        ("published", "Published"),
        ("closed", "Closed"),
    ]
    
    allegation_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    state = models.CharField(max_length=50, choices=STATE_CHOICES, default="draft")
    title = models.CharField(max_length=200)
    alleged_entities = models.JSONField(default=list)
    related_entities = models.JSONField(default=list)
    location_id = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField()
    key_allegations = models.JSONField(default=list)
    timeline = models.JSONField(default=list)
    evidence = models.JSONField(default=list)
    case_date = models.DateField(null=True, blank=True)
    contributors = models.ManyToManyField(User, related_name='assigned_cases', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ["-created_at"]
        permissions = [
            ('publish_case', 'Can publish case'),
            ('assign_contributor', 'Can assign contributors to case'),
        ]
    
    def clean(self):
        if not self.alleged_entities:
            raise ValidationError({"alleged_entities": "At least one alleged entity is required."})
        for entity_id in self.alleged_entities:
            validate_entity_id(entity_id)
        for entity_id in self.related_entities:
            validate_entity_id(entity_id)
        if not self.key_allegations or len(self.key_allegations) < 1:
            raise ValidationError({"key_allegations": "At least one key allegation is required."})
        for entry in self.timeline:
            if not isinstance(entry, dict):
                raise ValidationError({"timeline": "Each timeline entry must be an object."})
            if 'date' not in entry or 'title' not in entry or 'description' not in entry:
                raise ValidationError({"timeline": "Each timeline entry must have date, title, and description fields."})
        for entry in self.evidence:
            if not isinstance(entry, dict):
                raise ValidationError({"evidence": "Each evidence entry must be an object."})
            if 'source_id' not in entry or 'description' not in entry:
                raise ValidationError({"evidence": "Each evidence entry must have source_id and description fields."})
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        AllegationRevision.objects.create(
            allegation=self,
            content_snapshot={
                'allegation_type': self.allegation_type,
                'state': self.state,
                'title': self.title,
                'alleged_entities': self.alleged_entities,
                'related_entities': self.related_entities,
                'location_id': self.location_id,
                'description': self.description,
                'key_allegations': self.key_allegations,
                'timeline': self.timeline,
                'evidence': self.evidence,
                'case_date': str(self.case_date) if self.case_date else None,
            }
        )
    
    def __str__(self):
        return self.title


class AllegationRevision(models.Model):
    allegation = models.ForeignKey(Allegation, on_delete=models.CASCADE, related_name="revisions")
    content_snapshot = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return f"{self.allegation.title} - {self.created_at}"


class Modification(models.Model):
    ACTION_CHOICES = [
        ("created", "Created"),
        ("submitted", "Submitted"),
        ("reviewed", "Reviewed"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("updated", "Updated"),
        ("response_added", "Response Added"),
    ]
    
    allegation = models.ForeignKey(Allegation, on_delete=models.CASCADE, related_name="modifications")
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField()
    
    class Meta:
        ordering = ["timestamp"]
    
    def __str__(self):
        return f"{self.action} - {self.allegation.title} at {self.timestamp}"


class Response(models.Model):
    allegation = models.ForeignKey(Allegation, on_delete=models.CASCADE, related_name="responses")
    response_text = models.TextField()
    entity_id = models.CharField(max_length=200)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    
    class Meta:
        ordering = ["-submitted_at"]
    
    def __str__(self):
        return f"Response to {self.allegation.title}"
