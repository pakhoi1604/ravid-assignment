from django.core.management.base import BaseCommand

from apps.documents.dispatch import publish_due_dispatches, reset_expired_dispatch_claims


class Command(BaseCommand):
    help = "Publish due document-ingestion dispatch outbox rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        reset_expired_dispatch_claims()
        published = publish_due_dispatches(limit=options["limit"])
        self.stdout.write(f"published={published}")
