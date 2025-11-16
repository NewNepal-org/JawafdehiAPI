from django.db import models
from django.contrib.auth.models import User
from datetime import datetime
import uuid


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
        ("under_review", "Under Review"),
        ("current", "Current"),
        ("closed", "Closed"),
    ]
    
    allegation_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    state = models.CharField(max_length=50, choices=STATE_CHOICES, default="draft")
    title = models.CharField(max_length=200)
    alleged_entities = models.JSONField(default=list)
    related_entities = models.JSONField(default=list)
    location_id = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField()
    key_allegations = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    first_public_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self):
        return self.title


class Timeline(models.Model):
    allegation = models.ForeignKey(Allegation, on_delete=models.CASCADE, related_name="timelines")
    date = models.DateField()
    title = models.CharField(max_length=200)
    description = models.TextField()
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ["order", "date"]
    
    def __str__(self):
        return f"{self.allegation.title} - {self.title}"


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
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ["timestamp"]
    
    def __str__(self):
        return f"{self.action} - {self.allegation.title} at {self.timestamp}"


class Evidence(models.Model):
    evidence_id = models.CharField(max_length=100, unique=True, editable=False)
    allegation = models.ForeignKey(Allegation, on_delete=models.CASCADE, related_name="evidences")
    source = models.ForeignKey(DocumentSource, on_delete=models.CASCADE, related_name="evidences")
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.evidence_id:
            date_str = datetime.now().strftime("%Y%m%d")
            uuid_str = str(uuid.uuid4())[:8]
            self.evidence_id = f"evidence:{date_str}:{uuid_str}"
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ["order"]
        unique_together = ["allegation", "source"]
    
    def __str__(self):
        return f"{self.allegation.title} - {self.source.title}"


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
