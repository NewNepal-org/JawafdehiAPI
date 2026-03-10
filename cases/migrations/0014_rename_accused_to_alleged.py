# Generated migration to rename 'accused' to 'alleged'

from django.db import migrations


def rename_accused_to_alleged(apps, schema_editor):
    """Update all 'accused' type values to 'alleged'."""
    CaseEntityRelationship = apps.get_model('cases', 'CaseEntityRelationship')
    CaseEntityRelationship.objects.filter(type='accused').update(type='alleged')


def rename_alleged_to_accused(apps, schema_editor):
    """Reverse migration: Update all 'alleged' type values back to 'accused'."""
    CaseEntityRelationship = apps.get_model('cases', 'CaseEntityRelationship')
    CaseEntityRelationship.objects.filter(type='alleged').update(type='accused')


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0013_remove_old_entity_fields'),
    ]

    operations = [
        migrations.RunPython(rename_accused_to_alleged, rename_alleged_to_accused),
    ]
