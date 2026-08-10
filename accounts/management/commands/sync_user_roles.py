from django.core.management.base import BaseCommand

from accounts.roles import assign_role, ensure_role_groups
from core.models import Student, Teacher


class Command(BaseCommand):
    help = "Create role groups and assign linked teachers and students to them."

    def handle(self, *args, **options):
        ensure_role_groups()
        teacher_count = 0
        student_count = 0

        for teacher in Teacher.objects.exclude(user__isnull=True).only("user_id"):
            assign_role(teacher.user, "teacher")
            teacher_count += 1
        for student in Student.objects.exclude(user__isnull=True).only("user_id"):
            assign_role(student.user, "student")
            student_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"Role groups are ready. Assigned Teacher to {teacher_count} user(s) and Student to {student_count} user(s)."
        ))
