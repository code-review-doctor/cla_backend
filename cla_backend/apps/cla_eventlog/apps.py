from django.apps import AppConfig
from registry import event_registry


class EventLogConfig(AppConfig):
    name = "cla_eventlog"

    def ready(self):
        autodiscover()


def autodiscover():
    """
    Auto-discover INSTALLED_APPS events.py modules and fail silently when
    not present. This forces an import on them to register any admin bits they
    may want.
    """
    import copy
    from django.conf import settings
    from importlib import import_module
    from django.utils.module_loading import module_has_submodule

    for app in settings.PROJECT_APPS:
        mod = import_module(app)
        # Attempt to import the app's admin module.
        try:
            before_import_registry = copy.copy(event_registry._registry)
            import_module("%s.events" % app)
        except Exception:
            # Reset the model registry to the state before the last import as
            # this import will have to reoccur on the next request and this
            # could raise NotRegistered and AlreadyRegistered exceptions
            # (see #8245).
            event_registry._registry = before_import_registry

            # Decide whether to bubble up this error. If the app just
            # doesn't have an admin module, we can ignore the error
            # attempting to import it, otherwise we want it to bubble up.
            if module_has_submodule(mod, "events"):
                raise
