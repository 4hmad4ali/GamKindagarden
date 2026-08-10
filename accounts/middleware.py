from django.core.exceptions import PermissionDenied

from .roles import has_role


ROLE_PATHS = {
    "/core/admin/": "admin",
    "/core/teacher/": "teacher",
    "/core/student/": "student",
    "/core/doctor/": "doctor",
    "/core/finance/": "finance",
}


class RoleAccessMiddleware:
    """Block direct URL access to dashboards outside a user's assigned role."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        for path_prefix, required_role in ROLE_PATHS.items():
            if request.path_info.startswith(path_prefix) and not has_role(request.user, required_role):
                raise PermissionDenied("You do not have permission to access this section.")
        return self.get_response(request)
