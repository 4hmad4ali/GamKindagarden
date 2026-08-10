from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.db.models.signals import post_migrate

        post_migrate.connect(
            self._bootstrap_roles,
            dispatch_uid='accounts.bootstrap_roles',
        )

    @staticmethod
    def _bootstrap_roles(**kwargs):
        """Create role groups whenever migrations finish without changing users."""
        try:
            from .roles import ensure_role_groups
            ensure_role_groups()
        except (OperationalError, ProgrammingError):
            # The auth tables may not exist yet during an interrupted migration.
            pass
