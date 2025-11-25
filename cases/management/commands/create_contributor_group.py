from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from allegations.models import Allegation, DocumentSource


class Command(BaseCommand):
    help = "Create Contributor group with appropriate permissions"

    def handle(self, *args, **options):
        group, created = Group.objects.get_or_create(name="Contributor")

        if created:
            self.stdout.write(self.style.SUCCESS("Created Contributor group"))
        else:
            self.stdout.write("Contributor group already exists")

        # Get content types
        allegation_ct = ContentType.objects.get_for_model(Allegation)
        source_ct = ContentType.objects.get_for_model(DocumentSource)

        # Define permissions for Contributor
        permissions = [
            Permission.objects.get(content_type=allegation_ct, codename="add_allegation"),
            Permission.objects.get(content_type=allegation_ct, codename="change_allegation"),
            Permission.objects.get(content_type=allegation_ct, codename="view_allegation"),
            Permission.objects.get(content_type=source_ct, codename="add_documentsource"),
            Permission.objects.get(content_type=source_ct, codename="change_documentsource"),
            Permission.objects.get(content_type=source_ct, codename="view_documentsource"),
        ]

        group.permissions.set(permissions)
        self.stdout.write(
            self.style.SUCCESS(
                f"Assigned {len(permissions)} permissions to Contributor group"
            )
        )
