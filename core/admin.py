from django.contrib import admin
from .models import Teacher, Student, Employee, Medical, Class, Transaction, StudentPayment

admin.site.register(Teacher)
admin.site.register(Student)
admin.site.register(Employee)
admin.site.register(Medical)
admin.site.register(Class)
admin.site.register(Transaction)
admin.site.register(StudentPayment)
