"""Import CIAA cases from JSON files in R2/S3 bucket as draft cases."""

import json
import logging
import os
import sys

from cloudpathlib import AnyPath, S3Client
from django.core.management.base import BaseCommand, CommandError

from cases.services.ciaa_draft_case_service import CIAADraftCaseService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger(__name__)

# Default base path for CIAA dataset (can be overridden via env var or --base-path)
DEFAULT_BASE_PATH = os.getenv("CIAA_DATASET_BASE_PATH", "s3://ngm/uploads/ciaa/cases")


class Command(BaseCommand):
    help = "Import CIAA cases from JSON files produced by NGM service"

    def add_arguments(self, parser):
        """Define command-line arguments."""
        parser.add_argument(
            "--fiscal-year",
            type=str,
            help="Fiscal year (e.g., '2078-79'). If not provided, imports all available years",
        )
        parser.add_argument(
            "--base-path",
            type=str,
            default=None,
            help=f"Base path (default: {DEFAULT_BASE_PATH})",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Validate without saving"
        )

    def handle(self, *args, **options):
        """Execute the import command."""
        fiscal_year = options.get("fiscal_year")
        base_path = options.get("base_path") or os.getenv(
            "CIAA_DATASET_BASE_PATH", DEFAULT_BASE_PATH
        )
        dry_run = options["dry_run"]

        # Configure S3Client for R2 if using S3
        if base_path.startswith("s3://"):
            endpoint_url = os.getenv("AWS_ENDPOINT_URL") or os.getenv(
                "AWS_S3_ENDPOINT_URL"
            )
            if endpoint_url:
                S3Client(
                    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                    endpoint_url=endpoint_url,
                ).set_as_default_client()
                logger.info(f"Configured S3Client with endpoint: {endpoint_url}")

        logger.info(f"Starting import from: {base_path}")
        if dry_run:
            logger.warning("DRY-RUN MODE: No changes will be saved")

        try:
            base_path_obj = AnyPath(base_path)

            # If no fiscal year specified, discover all available fiscal years
            if not fiscal_year:
                fiscal_years = self._discover_fiscal_years(base_path_obj)
                if not fiscal_years:
                    logger.warning("No fiscal year directories found")
                    return
                logger.info(
                    f"Found {len(fiscal_years)} fiscal years: {', '.join(fiscal_years)}"
                )
            else:
                fiscal_years = [fiscal_year]

            total_created = total_skipped = total_failed = 0

            for fy in fiscal_years:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing fiscal year: {fy}")
                logger.info(f"{'='*60}")

                created, skipped, failed = self._import_fiscal_year(
                    base_path_obj, fy, dry_run
                )

                total_created += created
                total_skipped += skipped
                total_failed += failed

            self._log_summary(total_created, total_skipped, total_failed, dry_run)

            # Exit with error code if any imports failed
            if total_failed > 0:
                raise CommandError(f"Import completed with {total_failed} failures")

        except Exception as e:
            raise CommandError(f"Import failed: {e}")

    def _discover_fiscal_years(self, base_path: AnyPath) -> list[str]:
        """Discover all fiscal year directories in base path."""
        fiscal_years = []
        try:
            for item in base_path.iterdir():
                if item.is_dir() and "-" in item.name:
                    fiscal_years.append(item.name)
            return sorted(fiscal_years)
        except Exception as e:
            logger.error(f"Failed to discover fiscal years: {e}")
            return []

    def _import_fiscal_year(
        self, base_path: AnyPath, fiscal_year: str, dry_run: bool
    ) -> tuple[int, int, int]:
        """Import cases for a single fiscal year. Returns (created, skipped, failed)."""
        source_dir = base_path / fiscal_year

        json_files = list(source_dir.rglob("*.json"))
        json_files = [f for f in json_files if f.name != "index.json"]

        if not json_files:
            logger.warning(f"No JSON files found in {fiscal_year}")
            return 0, 0, 0

        logger.info(f"Found {len(json_files)} JSON files")

        service = CIAADraftCaseService()
        created = skipped = failed = 0
        skipped_not_confirmed = 0

        for idx, json_file in enumerate(json_files, 1):
            try:
                ciaa_json = json.loads(json_file.read_text(encoding="utf-8"))

                if ciaa_json.get("meta", {}).get("match_status") != "confirmed":
                    skipped_not_confirmed += 1
                    continue

                case_no = ciaa_json.get("case_no", "Unknown")
                case_title = ciaa_json.get("case_title", "")[:60]

                logger.info(
                    f"[{idx}/{len(json_files)}] Processing: {case_no} - {case_title}..."
                )

                result = service.import_case(ciaa_json, dry_run=dry_run)

                if result.status == "created":
                    created += 1
                    logger.info(f"DRAFTED: {case_no}")
                elif result.status == "skipped":
                    skipped += 1
                    logger.debug(f"SKIPPED: {case_no}")
                else:
                    failed += 1
                    logger.error(f"FAILED: {case_no} - {result.message}")

            except json.JSONDecodeError as e:
                failed += 1
                logger.error(f"JSON parse error in {json_file.name}: {e}")
            except Exception as e:
                failed += 1
                logger.error(f"Error processing {json_file.name}: {e}")

        if skipped_not_confirmed > 0:
            logger.info(
                f"Skipped {skipped_not_confirmed} cases (not confirmed match_status)"
            )

        return created, skipped, failed

    def _log_summary(self, created, skipped, failed, dry_run):
        logger.info("\n" + "=" * 60)
        logger.info("IMPORT SUMMARY")
        logger.info("=" * 60)
        if dry_run:
            logger.warning("DRY-RUN MODE (no changes saved)")
        logger.info(f"Created: {created}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"Failed: {failed}")
        logger.info("=" * 60)
