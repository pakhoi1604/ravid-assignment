from django.core.management.base import BaseCommand

from apps.documents.recovery import reindex_legacy_documents


class Command(BaseCommand):
    help = "Reset successful legacy documents without active generations for reindexing."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        reset = reindex_legacy_documents(limit=options["limit"], dry_run=options["dry_run"])
        self.stdout.write(f"reset={reset}")
