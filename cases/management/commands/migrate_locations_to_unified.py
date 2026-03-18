"""
Management command to migrate location relationships to unified entity system.

This command migrates any remaining direct location relationships to use the
CaseEntityRelationship through-model with 'related' type, ensuring locations
are properly identified by their nes_id pattern.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from cases.models import Case, CaseEntityRelationship, RelationshipType


class Command(BaseCommand):
    help = "Migrate location relationships to unified entity system"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )

        migrated_count = 0
        skipped_count = 0

        with transaction.atomic():
            # Get all cases with location relationships
            cases_with_locations = Case.objects.prefetch_related('locations').filter(
                locations__isnull=False
            ).distinct()

            for case in cases_with_locations:
                for location in case.locations.all():
                    # Verify this is actually a location entity
                    if not (location.nes_id and location.nes_id.startswith('entity:location/')):
                        self.stdout.write(
                            self.style.WARNING(
                                f"Skipping {case.case_id} -> {location.display_name} "
                                f"(not a location entity: {location.nes_id})"
                            )
                        )
                        continue

                    # Check if this relationship already exists in unified system
                    existing_relationship = CaseEntityRelationship.objects.filter(
                        case=case,
                        entity=location,
                        relationship_type=RelationshipType.RELATED
                    ).first()

                    if existing_relationship:
                        self.stdout.write(
                            f"Skipping {case.case_id} -> {location.display_name} "
                            f"(already exists in unified system)"
                        )
                        skipped_count += 1
                        continue

                    if not dry_run:
                        # Create unified relationship
                        CaseEntityRelationship.objects.create(
                            case=case,
                            entity=location,
                            relationship_type=RelationshipType.RELATED,
                            notes=""
                        )

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'Would migrate' if dry_run else 'Migrated'} "
                            f"{case.case_id} -> {location.display_name} "
                            f"(location -> related entity)"
                        )
                    )
                    migrated_count += 1

            if dry_run:
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)

        self.stdout.write(
            self.style.SUCCESS(
                f"\n{'Would migrate' if dry_run else 'Migrated'} {migrated_count} location relationships"
            )
        )
        self.stdout.write(f"Skipped {skipped_count} existing relationships")
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nRun without --dry-run to apply these changes"
                )
            )