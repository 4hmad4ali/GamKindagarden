"""Server-side role resolution for dashboard access.

Roles are stored in Django's built-in ``auth_group`` table, never submitted by
the browser.  ``is_staff`` and ``is_superuser`` retain their normal meaning
and grant access to the management dashboard.
"""

from django.contrib.auth.models import Group


ROLE_GROUPS = {
    "admin": "Admin",
    "teacher": "Teacher",
    "student": "Student",
    "doctor": "Doctor",
    "finance": "Finance",
}

DASHBOARD_BY_ROLE = {
    "admin": "admin_dashboard",
    "teacher": "teacher_dashboard",
    "student": "student_dashboard",
    "doctor": "doctor_dashboard",
    "finance": "finance_dashboard",
}


def ensure_role_groups():
    """Create the fixed role groups if they do not already exist."""
    for name in ROLE_GROUPS.values():
        Group.objects.get_or_create(name=name)


def assign_role(user, role):
    """Assign exactly the supplied application role to a user."""
    group_name = ROLE_GROUPS[role]
    group, _ = Group.objects.get_or_create(name=group_name)
    user.groups.add(group)


def get_user_role(user):
    """Return the user's highest-priority dashboard role, if any."""
    if not user.is_authenticated:
        return None
    if user.is_superuser or user.is_staff:
        return "admin"

    group_names = set(user.groups.filter(name__in=ROLE_GROUPS.values()).values_list("name", flat=True))
    for role in ("admin", "teacher", "student", "doctor", "finance"):
        if ROLE_GROUPS[role] in group_names:
            return role
    return None


def dashboard_for_user(user):
    """Return the safe landing page for an authenticated user."""
    return DASHBOARD_BY_ROLE.get(get_user_role(user), "chat_dashboard")


def has_role(user, required_role):
    """Check server-side access to a role-specific route."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if required_role == "admin":
        return user.is_staff or user.groups.filter(name=ROLE_GROUPS["admin"]).exists()
    return user.groups.filter(name=ROLE_GROUPS[required_role]).exists()
