from django.db import migrations


def rename_app_label(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.filter(app_label='allegations').update(app_label='cases')


def reverse_rename_app_label(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    ContentType.objects.filter(app_label='cases').update(app_label='allegations')


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0007_alter_modification_notes'),
        ('contenttypes', '__first__'),
    ]

    operations = [
        migrations.RunPython(rename_app_label, reverse_rename_app_label),
    ]
