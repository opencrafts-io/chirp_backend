from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('posts', '0004_post_post_created_at_idx_post_post_community_idx_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='post',
            name='post_community_idx',
        ),
        migrations.RemoveIndex(
            model_name='post',
            name='post_author_idx',
        ),
    ]
