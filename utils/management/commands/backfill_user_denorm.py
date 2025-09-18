from django.core.management.base import BaseCommand
from django.db import transaction

from users.models import User
from posts.models import Post
from groups.models import Group


class Command(BaseCommand):
    help = "Backfill denormalized user fields on posts and groups from users table"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Print counts only; do not update")

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")

        post_updates = 0
        group_updates = 0

        with transaction.atomic():
            posts = Post._default_manager.select_related("user_ref").all()
            for post in posts:
                user = post.user_ref
                if not user:
                    try:
                        user = User._default_manager.get(user_id=post.user_id)
                    except User._default_manager.DoesNotExist:
                        continue
                changed = False
                if post.user_name != user.user_name:
                    post.user_name = user.user_name
                    changed = True
                if post.email != user.email:
                    post.email = user.email
                    changed = True
                if post.avatar_url != user.avatar_url:
                    post.avatar_url = user.avatar_url
                    changed = True
                if changed:
                    post_updates += 1
                    if not dry_run:
                        post.save(update_fields=["user_name", "email", "avatar_url"])

            groups = Group._default_manager.all()
            for group in groups:
                changed = False
                try:
                    creator = User._default_manager.get(user_id=group.creator_id)
                    if group.creator_name != creator.user_name:
                        group.creator_name = creator.user_name
                        changed = True
                except User.DoesNotExist:
                    pass

                if isinstance(group.moderators, list):
                    new_mod_names = []
                    for uid in group.moderators:
                        try:
                            new_mod_names.append(User._default_manager.get(user_id=uid).user_name)
                        except User.DoesNotExist:
                            new_mod_names.append("User")
                    if group.moderator_names != new_mod_names:
                        group.moderator_names = new_mod_names
                        changed = True

                if isinstance(group.members, list):
                    new_member_names = []
                    for uid in group.members:
                        try:
                            new_member_names.append(User._default_manager.get(user_id=uid).user_name)
                        except User.DoesNotExist:
                            new_member_names.append("User")
                    if group.member_names != new_member_names:
                        group.member_names = new_member_names
                        changed = True

                if isinstance(group.banned_users, list):
                    new_banned_names = []
                    for uid in group.banned_users:
                        try:
                            new_banned_names.append(User._default_manager.get(user_id=uid).user_name)
                        except User.DoesNotExist:
                            new_banned_names.append("User")
                    if group.banned_user_names != new_banned_names:
                        group.banned_user_names = new_banned_names
                        changed = True

                if changed:
                    group_updates += 1
                    if not dry_run:
                        group.save()

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(f"Post rows updated: {post_updates}"))
        self.stdout.write(self.style.SUCCESS(f"Group rows updated: {group_updates}"))


