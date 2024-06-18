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
    apps_that_use_principle_router = ["hustings"]

    def db_for_read(self, model, **hints):
        return "default"

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.apps_that_use_principle_router:
            return "principle"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow any relation between objects in different databases.
        """
        db1 = (
            hints.get("instance")
            and hints["instance"]._state.db
            or obj1._state.db
        )
        db2 = obj2._state.db
        if db1 and db2:
            if db1 == db2:
                return True
            return True  # Allow cross-database relations
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Managed by CI / Lambda
        return False
