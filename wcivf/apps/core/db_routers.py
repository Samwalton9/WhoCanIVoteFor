class FeedbackRouter(object):
    apps_that_use_feedback_router = ["feedback"]

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_feedback_router:
            return "feedback"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_feedback_router:
            return "feedback"
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True


class PrincipleRDSRouter:
    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        return "principle"

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Managed by CI / Lambda
        return False
