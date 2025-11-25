from django.db import migrations


def create_contributor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Create Contributor group
    contributor_group, created = Group.objects.get_or_create(name="Contributor")

    # Get content types
    allegation_ct = ContentType.objects.get(app_label="cases", model="allegation")
    source_ct = ContentType.objects.get(app_label="cases", model="documentsource")
    evidence_ct = ContentType.objects.get(app_label="cases", model="evidence")
    timeline_ct = ContentType.objects.get(app_label="cases", model="timeline")

    # Get permissions
    permissions = Permission.objects.filter(
        content_type__in=[allegation_ct, source_ct, evidence_ct, timeline_ct],
        codename__in=[
            "add_allegation", "change_allegation", "view_allegation",
            "add_documentsource", "change_documentsource", "view_documentsource",
            "add_evidence", "change_evidence", "view_evidence",
            "add_timeline", "change_timeline", "view_timeline",
        ]
    )

    contributor_group.permissions.set(permissions)


def reverse_contributor_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Contributor").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cases", "0009_rename_app_label"),
    ]

    operations = [
        migrations.RunPython(create_contributor_group, reverse_contributor_group),
    ]
