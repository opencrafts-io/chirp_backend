from django.db import migrations


def populate_group_memberships(apps, schema_editor):
    Group = apps.get_model('groups', 'Group')
    GroupMembership = apps.get_model('groups', 'GroupMembership')
    User = apps.get_model('users', 'User')

    for group in Group.objects.all():
        # Migrate creator
        try:
            creator = User.objects.get(user_id=group.creator_id)
            GroupMembership.objects.get_or_create(
                group=group,
                user=creator,
                defaults={'role': 'creator'}
            )
        except User.DoesNotExist:
            pass

        # Migrate moderators
        moderators = group.moderators if isinstance(group.moderators, list) else []
        moderator_names = group.moderator_names if isinstance(group.moderator_names, list) else []
        for user_id, user_name in zip(moderators, moderator_names):
            try:
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=group,
                    user=user,
                    defaults={'role': 'moderator'}
                )
            except User.DoesNotExist:
                pass

        # Migrate members
        members = group.members if isinstance(group.members, list) else []
        member_names = group.member_names if isinstance(group.member_names, list) else []
        for user_id, user_name in zip(members, member_names):
            try:
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=group,
                    user=user,
                    defaults={'role': 'member'}
                )
            except User.DoesNotExist:
                pass

        # Migrate banned users
        banned_users = group.banned_users if isinstance(group.banned_users, list) else []
        banned_user_names = group.banned_user_names if isinstance(group.banned_user_names, list) else []
        for user_id, user_name in zip(banned_users, banned_user_names):
            try:
                user = User.objects.get(user_id=user_id)
                GroupMembership.objects.get_or_create(
                    group=group,
                    user=user,
                    defaults={'role': 'banned'}
                )
            except User.DoesNotExist:
                pass


def reverse_populate_group_memberships(apps, schema_editor):
    # This migration is not reversible as it creates new data
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('groups', '0009_groupmembership'),
        ('users', '0003_populate_foreign_keys'),
    ]

    operations = [
        migrations.RunPython(populate_group_memberships, reverse_populate_group_memberships),
    ]
