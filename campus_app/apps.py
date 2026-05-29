from django.apps import AppConfig


class CampusAppConfig(AppConfig):
    name = 'campus_app'

    def ready(self):
        import campus_app.signals
