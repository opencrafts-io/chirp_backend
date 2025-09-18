from django.core.management.base import BaseCommand

from utils.sync_users import sync_users


class Command(BaseCommand):
    help = "Sync users from Verisafe. Optionally limit count and skip clearing."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50, help="Max users to sync (default 50)")
        parser.add_argument("--no-clear", action="store_true", help="Do not clear users table before syncing")

    def handle(self, *args, **options):
        limit = options.get("limit")
        no_clear = options.get("no_clear")
        total = sync_users(clear_first=not no_clear, limit=limit)
        self.stdout.write(self.style.SUCCESS(f"Synced {total} users"))


