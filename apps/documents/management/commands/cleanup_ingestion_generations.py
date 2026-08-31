from django.core.management.base import BaseCommand

from apps.documents.recovery import cleanup_due_generations


class Command(BaseCommand):
    help = "Delete due stale document-ingestion generations from vector storage."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        cleaned = cleanup_due_generations(limit=options["limit"])
        self.stdout.write(f"cleaned={cleaned}")
