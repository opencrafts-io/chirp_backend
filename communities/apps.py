from django.apps import AppConfig


class CommunitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communities'

    label = 'groups'

    def ready(self) -> None:
        import communities.signals
