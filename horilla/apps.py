from django.apps import AppConfig

class HorillaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'horilla'

    def ready(self):
        import horilla.user_signals  # or horilla.signals if you put it there
