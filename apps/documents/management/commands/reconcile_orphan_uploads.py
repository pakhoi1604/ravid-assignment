from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.documents.models import Document


class Command(BaseCommand):
    help = "Delete old uploaded media files that are no longer referenced by Document rows."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stdout.write("deleted=0")
            return

        referenced = set(Document.objects.exclude(file="").values_list("file", flat=True))
        cutoff = timezone.now().timestamp() - settings.INGESTION_ORPHAN_UPLOAD_GRACE_SECONDS
        deleted = 0
        for path in sorted(media_root.rglob("*")):
            if deleted >= options["limit"]:
                break
            if not path.is_file():
                continue
            relative = str(path.relative_to(media_root))
            if relative in referenced or path.stat().st_mtime > cutoff:
                continue
            deleted += 1
            if not options["dry_run"]:
                path.unlink()
        self.stdout.write(f"deleted={deleted}")
