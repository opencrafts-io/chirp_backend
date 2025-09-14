from django.db import migrations


def populate_users_from_existing_data(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Post = apps.get_model('posts', 'Post')
    Comment = apps.get_model('posts', 'Comment')
    Group = apps.get_model('groups', 'Group')
    Message = apps.get_model('dmessages', 'Message')
    ConversationMessage = apps.get_model('conversations', 'ConversationMessage')

    # Collect all unique users from existing data
    users_data = set()

    # From posts
    for post in Post.objects.all():
        users_data.add((post.user_id, post.user_name, post.email))

    # From comments
    for comment in Comment.objects.all():
        users_data.add((comment.user_id, comment.user_name, comment.email))

    # From groups (creator)
    for group in Group.objects.all():
        users_data.add((group.creator_id, group.creator_name, None))

    # From messages
    for message in Message.objects.all():
        users_data.add((message.sender_id, None, None))
        users_data.add((message.recipient_id, None, None))

    # From conversation messages
    for conv_msg in ConversationMessage.objects.all():
        users_data.add((conv_msg.sender_id, None, None))

    # Create User records
    for user_id, user_name, email in users_data:
        if user_id:  # Skip empty user_ids
            User.objects.get_or_create(
                user_id=user_id,
                defaults={
                    'user_name': user_name or f'User_{user_id}',
                    'email': email
                }
            )


def reverse_populate_users(apps, schema_editor):
    # This migration is not reversible as it creates new data
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0001_initial'),
        ('posts', '0013_comment_user_ref_post_user_ref'),
        ('groups', '0009_groupmembership'),
        ('dmessages', '0006_message_recipient_ref_message_sender_ref'),
        ('conversations', '0003_conversationmessage_sender_ref'),
    ]

    operations = [
        migrations.RunPython(populate_users_from_existing_data, reverse_populate_users),
    ]
