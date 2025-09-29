from django.apps import AppConfig


class PostsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'posts'


    def ready(self) -> None:
        """
        Ensure the app's signal handlers are registered when Django initializes the application.
        
        This method imports the module that registers signal handlers for the posts app (`posts.signals`) so those handlers are connected during app startup.
        """
        import posts.signals
