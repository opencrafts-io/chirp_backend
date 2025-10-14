from django.apps import AppConfig


class CommunitiesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'communities'

    # label = 'groups'

    def ready(self) -> None:
        """
        Ensure application signal handlers are registered by importing the communities.signals module when the app is ready.
        
        This triggers registration of any signal handlers defined in communities.signals during Django startup.
        """
        import communities.signals
