import datetime
from django.db import models
from django.contrib.auth.models import User


#  UserProfile 


class UserProfile(models.Model):
    """پروفایل کاربر - عکس، تلفون، بخش، بایو"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True, default='Administration')
    bio = models.TextField(blank=True)

    def __str__(self):
        return f"Profile: {self.user.username}"

    class Meta:
        verbose_name = 'پروفایل'
        verbose_name_plural = 'پروفایل‌ها'



# 1️ Employee


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    employee_id = models.CharField(max_length=20, unique=True)
    salary = models.DecimalField(max_digits=12, decimal_places=2)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = 'کارمند'
        verbose_name_plural = 'کارمندان'



#  Teacher


class Teacher(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    subject = models.CharField(max_length=100)
    employee_id = models.CharField(max_length=20, unique=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"{self.user.first_name} {self.user.last_name}"
        return self.email

    class Meta:
        verbose_name = 'معلم'
        verbose_name_plural = 'معلمان'



# Student


class Student(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    address = models.TextField()
    student_id = models.CharField(max_length=20, unique=True)
    class_field = models.CharField(max_length=50)
    enrollment_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = 'شاگرد'
        verbose_name_plural = 'شاگردان'



# Attendance


class Attendance(models.Model):
    CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('leave', 'مرخصی'),
    ]
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField()
    check_in_time = models.TimeField(blank=True, null=True)
    check_out_time = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee} - {self.date}"

    class Meta:
        verbose_name = 'حضوری'
        verbose_name_plural = 'حضوری‌ها'
        ordering = ['-date']



# Class


class Class(models.Model):
    class_name = models.CharField(max_length=100)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes')
    room_number = models.CharField(max_length=20)
    capacity = models.IntegerField()
    level = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.class_name

    class Meta:
        verbose_name = 'کلاس'
        verbose_name_plural = 'کلاس‌ها'



#  Medical


class Medical(models.Model):
    HEALTH_STATUS_CHOICES = [
        ('excellent', 'عالی'),
        ('good', 'خوب'),
        ('normal', 'معمولی'),
        ('needs_care', 'نیاز به مراقبت'),
    ]
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='medical_record')
    checkup_date = models.DateField(default=datetime.date.today)
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    blood_pressure = models.CharField(max_length=20, blank=True)
    temperature = models.FloatField(null=True, blank=True)
    health_status = models.CharField(max_length=50, choices=HEALTH_STATUS_CHOICES)
    diagnosis = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Medical: {self.student}"

    class Meta:
        verbose_name = 'معاینات پزشکی'
        verbose_name_plural = 'معاینات پزشکی'



#  Transaction   TRANSACTION_TYPE داخل کلاس


class Transaction(models.Model):
    #  این لیست باید داخل کلاس باشد نه بیرون
    TRANSACTION_TYPE = [
        ('income', 'درآمد'),
        ('expense', 'هزینه'),
    ]

    transaction_id = models.CharField(max_length=50, unique=True)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_date = models.DateField()
    description = models.CharField(max_length=500)
    category = models.CharField(max_length=100)
    status = models.CharField(max_length=20, default='completed')
    student = models.ForeignKey(
        Student,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transactions'
    )
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"

    class Meta:
        verbose_name = 'تراکنش'
        verbose_name_plural = 'تراکنش‌ها'
        ordering = ['-transaction_date']



# StudentPayment


class StudentPayment(models.Model):
    PAYMENT_STATUS = [
        ('pending', 'در انتظار'),
        ('completed', 'تکمیل شده'),
        ('overdue', 'تاخیر'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='payments')
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='student_payment',
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_type = models.CharField(max_length=50)
    month = models.IntegerField()
    year = models.IntegerField()
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    created_date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} - {self.year}/{self.month}"

    class Meta:
        verbose_name = 'پرداخت شاگرد'
        verbose_name_plural = 'پرداخت‌های شاگردان'
        ordering = ['-year', '-month']
        unique_together = ('student', 'month', 'year')

#  TeacherPlan 


class TeacherPlan(models.Model):
    """پلان درسی معلم"""
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='plans')
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=200, blank=True)
    goal = models.TextField(blank=True)
    material = models.TextField(blank=True)
    activities = models.TextField(blank=True)
    evaluation = models.TextField(blank=True)
    class_name = models.CharField(max_length=100, blank=True)
    date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.topic}"

    class Meta:
        verbose_name = 'پلان درسی'
        verbose_name_plural = 'پلان‌های درسی'
        ordering = ['-date']



#  TeacherPresence - 


class TeacherPresence(models.Model):
    """حضوری معلم"""
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('leave', 'مرخصی'),
    ]
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='teacher_presence')
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher} - {self.date} - {self.status}"

    class Meta:
        verbose_name = 'حضوری معلم'
        verbose_name_plural = 'حضوری معلمان'
        ordering = ['-date']



#  StudentPresence 

class StudentPresence(models.Model):
    """حضوری شاگرد توسط معلم"""
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent', 'غایب'),
        ('leave', 'مرخصی'),
    ]
    student_name = models.CharField(max_length=200)
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.date} - {self.status}"

    class Meta:
        verbose_name = 'حضوری شاگرد'
        verbose_name_plural = 'حضوری شاگردان'
        ordering = ['-date']


# StudentHealthReport - گزارش صحی 


class StudentHealthReport(models.Model):
    """گزارش صحی شاگرد توسط معلم"""
    HEALTH_CHOICES = [
        ('excellent', 'عالی'),
        ('good', 'خوب'),
        ('normal', 'معمولی'),
        ('needs_care', 'نیاز به مراقبت'),
    ]
    student_name = models.CharField(max_length=200)
    date = models.DateField()
    height = models.FloatField(null=True, blank=True)
    weight = models.FloatField(null=True, blank=True)
    health_status = models.CharField(max_length=50, choices=HEALTH_CHOICES, default='good')
    diagnosis = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student_name} - {self.health_status}"

    class Meta:
        verbose_name = 'گزارش صحی'
        verbose_name_plural = 'گزارشات صحی'
        ordering = ['-date']



#  TeacherTimetable - جدول وقت  


class TeacherTimetable(models.Model):
    """جدول وقت معلم"""
    DAY_CHOICES = [
        ('شنبه', 'شنبه'),
        ('یکشنبه', 'یکشنبه'),
        ('دوشنبه', 'دوشنبه'),
        ('سه‌شنبه', 'سه‌شنبه'),
        ('چهارشنبه', 'چهارشنبه'),
    ]
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, null=True, blank=True, related_name='timetable')
    day = models.CharField(max_length=20, choices=DAY_CHOICES)
    time_slot = models.CharField(max_length=50)
    subject = models.CharField(max_length=100)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.day} {self.time_slot} - {self.subject}"

    class Meta:
        verbose_name = 'جدول وقت'
        verbose_name_plural = 'جدول وقت‌ها'
        unique_together = ('teacher', 'day', 'time_slot')


class DoctorPresence(models.Model):
    """حضور و غیاب داکتر"""
    STATUS_CHOICES = [
        ('present', 'حاضر'),
        ('absent',  'غایب'),
        ('late',    'دیر'),
    ]
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_presences')
    date   = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='present')
    note   = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'حضور داکتر'
        verbose_name_plural = 'حضور داکتران'
        ordering = ['-date']

    def __str__(self):
        return f"{self.doctor.username} - {self.date} - {self.status}"
