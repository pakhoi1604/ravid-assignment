from django.core.management.base import BaseCommand

from apps.documents.recovery import recover_stale_ingestion_jobs


class Command(BaseCommand):
    help = "Rotate stale document-ingestion generations and enqueue retry dispatch rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        recovered = recover_stale_ingestion_jobs(
            limit=options["limit"],
            dry_run=options["dry_run"],
        )
        self.stdout.write(f"recovered={recovered}")
