"""Create the first GAAM administrator when a database is deployed."""

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError

from accounts.roles import assign_role, ensure_role_groups


class Command(BaseCommand):
    help = "Ensure the database has one initial superuser from protected environment variables."

    def handle(self, *args, **options):
        user_model = get_user_model()

        # Once an administrator exists, deployments must never reset a password
        # or unexpectedly alter accounts.
        if user_model.objects.filter(is_superuser=True).exists():
            self.stdout.write("An administrator already exists; bootstrap skipped.")
            return

        username = os.getenv("INITIAL_ADMIN_USERNAME", "").strip()
        password = os.getenv("INITIAL_ADMIN_PASSWORD", "")
        email = os.getenv("INITIAL_ADMIN_EMAIL", "").strip()

        if not username or not password:
            raise CommandError(
                "No superuser exists. Set INITIAL_ADMIN_USERNAME and "
                "INITIAL_ADMIN_PASSWORD in Railway Variables before deploying."
            )

        user = user_model.objects.filter(username=username).first()
        created = user is None

        if created:
            try:
                validate_password(password)
            except ValidationError as error:
                raise CommandError(" ".join(error.messages)) from error

            user = user_model(username=username, email=email, is_active=True)
            user.set_password(password)
        else:
            # Do not turn an existing non-admin account into a superuser just
            # because it happens to have the requested username.
            raise CommandError(
                f"The username '{username}' already exists but is not a superuser. "
                "Choose a different INITIAL_ADMIN_USERNAME or promote that user manually."
            )

        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save()

        ensure_role_groups()
        assign_role(user, "admin")

        self.stdout.write(self.style.SUCCESS(
            f"Initial administrator '{username}' created successfully."
        ))
