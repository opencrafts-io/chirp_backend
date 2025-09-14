from django.db import migrations


def populate_foreign_keys(apps, schema_editor):
    User = apps.get_model('users', 'User')
    Post = apps.get_model('posts', 'Post')
    Comment = apps.get_model('posts', 'Comment')
    Message = apps.get_model('dmessages', 'Message')
    ConversationMessage = apps.get_model('conversations', 'ConversationMessage')

    # Populate Post foreign keys
    for post in Post.objects.all():
        try:
            user = User.objects.get(user_id=post.user_id)
            post.user_ref = user
            post.save()
        except User.DoesNotExist:
            pass

    # Populate Comment foreign keys
    for comment in Comment.objects.all():
        try:
            user = User.objects.get(user_id=comment.user_id)
            comment.user_ref = user
            comment.save()
        except User.DoesNotExist:
            pass

    # Populate Message foreign keys
    for message in Message.objects.all():
        try:
            sender = User.objects.get(user_id=message.sender_id)
            message.sender_ref = sender
        except User.DoesNotExist:
            pass

        try:
            recipient = User.objects.get(user_id=message.recipient_id)
            message.recipient_ref = recipient
        except User.DoesNotExist:
            pass

        message.save()

    # Populate ConversationMessage foreign keys
    for conv_msg in ConversationMessage.objects.all():
        try:
            user = User.objects.get(user_id=conv_msg.sender_id)
            conv_msg.sender_ref = user
            conv_msg.save()
        except User.DoesNotExist:
            pass


def reverse_populate_foreign_keys(apps, schema_editor):
    # This migration is not reversible as it modifies existing data
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_populate_users'),
    ]

    operations = [
        migrations.RunPython(populate_foreign_keys, reverse_populate_foreign_keys),
    ]
