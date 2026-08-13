#from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.db.models import Sum, Count, Q, Avg
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse
from accounts.roles import assign_role, ROLE_GROUPS
from django.utils import timezone
from .models import StudentPresence, DoctorPresence
from .models import Teacher, Student, Employee, Medical, Class, Transaction, StudentPayment, Attendance, TeacherPlan, TeacherPresence, StudentPresence, StudentHealthReport, TeacherTimetable, UserProfile


def _sync_payment_transaction(payment):
    """Keep the finance ledger aligned with a completed student payment."""
    if payment.status != 'completed':
        if payment.transaction_id:
            payment.transaction.delete()
            payment.transaction = None
            payment.save(update_fields=['transaction'])
        return

    transaction, _ = Transaction.objects.update_or_create(
        transaction_id=f'FEE-{payment.pk:08d}',
        defaults={
            'transaction_type': 'income',
            'amount': payment.paid_amount,
            'transaction_date': payment.created_date or timezone.localdate(),
            'description': f'Student fee: {payment.student} — {payment.payment_type} ({payment.month}/{payment.year})',
            'category': 'Student fee',
            'status': 'completed',
            'student': payment.student,
        },
    )
    if payment.transaction_id != transaction.id:
        payment.transaction = transaction
        payment.save(update_fields=['transaction'])


def _payment_payload(request, payment=None):
    """Validate one fee record before it reaches either the admin or finance UI."""
    student = Student.objects.filter(pk=request.POST.get('student_id', '').strip(), is_active=True).first()
    if not student:
        raise ValidationError('Please select an active student.')
    try:
        total_amount = Decimal(request.POST.get('total_amount', '').strip())
        paid_amount = Decimal(request.POST.get('paid_amount', '0').strip() or '0')
        month = int(request.POST.get('month', '').strip())
        year = int(request.POST.get('year', '').strip())
    except (InvalidOperation, ValueError):
        raise ValidationError('Enter valid payment amounts, month, and year.')

    status = request.POST.get('status', 'pending').strip()
    payment_type = request.POST.get('payment_type', '').strip()
    if total_amount <= 0 or paid_amount < 0 or paid_amount > total_amount:
        raise ValidationError('The paid amount must be between zero and the total amount.')
    if not 1 <= month <= 12 or year < 1300 or not payment_type:
        raise ValidationError('Enter a valid payment type, month, and year.')
    if status not in {'pending', 'completed', 'overdue'}:
        raise ValidationError('Select a valid payment status.')
    if status == 'completed':
        paid_amount = total_amount

    return {
        'student': student,
        'total_amount': total_amount,
        'paid_amount': paid_amount,
        'payment_type': payment_type,
        'month': month,
        'year': year,
        'status': status,
    }

#  
#  PROFILE CONTEXT HELPER
#  
def _get_profile_context(user):
    """عکس پروفایل، نام، تلفن و بایو را برای همه view ها برمی‌گرداند"""
    ctx = {
        'username': user.first_name or user.username,
        'profile_picture': None,
        'profile_phone': '',
        'profile_bio': '',
    }
    try:
        from .models import UserProfile
        profile_obj, _ = UserProfile.objects.get_or_create(user=user)
        if profile_obj.profile_picture:
            ctx['profile_picture'] = profile_obj.profile_picture.url
        ctx['profile_phone'] = profile_obj.phone or ''
        ctx['profile_bio']   = profile_obj.bio or ''
    except Exception:
        pass
    return ctx


#  
#  HOMEPAGE
#  

def homepage(request):
    """صفحه اصلی"""
    context = {
        'kindergarten': 'GAAM Kindergarten',
        'phone': '0788919112',
        'address': 'Microrayan 3rd, Kabul'
    }
    return render(request, 'homepage.html', context)

#  
#  ADMIN DASHBOARD
#  

@login_required(login_url='login_chat')
def admin_dashboard(request):
    """صفحه اول ادمین - Welcome"""
    context = _get_profile_context(request.user)
    context.update({
        'total_teachers': Teacher.objects.filter(is_active=True).count(),
        'total_students': Student.objects.filter(is_active=True).count(),
        'total_employees': Employee.objects.filter(is_active=True).count(),
        'total_admins': 1,
        'address': 'Microrayan 3rd, Kabul',
        'phone': '0788919112',
    })
    return render(request, 'admin_dashboard.html', context)


def _can_manage_privileged_accounts(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


_MANAGED_ACCOUNT_ROLES = {'admin', 'finance', 'doctor'}


def _set_managed_account_role(account, role):
    if role not in _MANAGED_ACCOUNT_ROLES:
        raise ValidationError('Choose Admin, Finance, or Doctor.')
    account.groups.remove(*account.groups.filter(name__in=[ROLE_GROUPS[item] for item in _MANAGED_ACCOUNT_ROLES]))
    account.is_staff = role == 'admin'
    assign_role(account, role)


@login_required(login_url='login_chat')
@user_passes_test(_can_manage_privileged_accounts, login_url='admin_dashboard')
def privileged_accounts(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '')
        try:
            if not all((username, first_name, last_name, email, password, role)):
                raise ValidationError('Complete all required account fields.')
            if len(password) < 8 or User.objects.filter(username__iexact=username).exists() or User.objects.filter(email__iexact=email).exists():
                raise ValidationError('Use a unique username and email, with a password of at least 8 characters.')
            with transaction.atomic():
                account = User.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email, password=password)
                _set_managed_account_role(account, role)
                account.save(update_fields=['is_staff'])
                UserProfile.objects.get_or_create(user=account)
            messages.success(request, 'حساب  با موفقیت اضافه شد.')
            return redirect('privileged_accounts')
        except ValidationError as error:
            messages.error(request, error.messages[0])
    accounts = User.objects.filter(Q(is_staff=True) | Q(groups__name__in=[ROLE_GROUPS[item] for item in _MANAGED_ACCOUNT_ROLES])).distinct().prefetch_related('groups').order_by('-date_joined')
    context = _get_profile_context(request.user)
    context.update({'accounts': accounts, 'admin_count': accounts.filter(is_staff=True).count(), 'finance_count': accounts.filter(groups__name=ROLE_GROUPS['finance']).distinct().count(), 'doctor_count': accounts.filter(groups__name=ROLE_GROUPS['doctor']).distinct().count()})
    return render(request, 'admin/privileged_accounts.html', context)


@login_required(login_url='login_chat')
@user_passes_test(_can_manage_privileged_accounts, login_url='admin_dashboard')
def privileged_account_edit(request, pk):
    account = get_object_or_404(User, pk=pk)
    if account == request.user or account.is_superuser:
        messages.error(request, 'این حساب محافظت‌شده قابل ویرایش نیست.')
        return redirect('privileged_accounts')
    if request.method == 'POST':
        try:
            email = request.POST.get('email', '').strip().lower()
            role = request.POST.get('role', '')
            password = request.POST.get('password', '')
            if not all((request.POST.get('first_name', '').strip(), request.POST.get('last_name', '').strip(), email)) or User.objects.filter(email__iexact=email).exclude(pk=account.pk).exists() or (password and len(password) < 8):
                raise ValidationError('Enter valid unique account details; passwords require at least 8 characters.')
            with transaction.atomic():
                account.first_name = request.POST['first_name'].strip()
                account.last_name = request.POST['last_name'].strip()
                account.email = email
                account.is_active = request.POST.get('is_active') == 'on'
                _set_managed_account_role(account, role)
                if password:
                    account.set_password(password)
                account.save()
            messages.success(request, 'حساب با موفقیت بروزرسانی شد.')
            return redirect('privileged_accounts')
        except ValidationError as error:
            messages.error(request, error.messages[0])
    role = 'admin' if account.is_staff else ('finance' if account.groups.filter(name=ROLE_GROUPS['finance']).exists() else 'doctor')
    context = _get_profile_context(request.user)
    context.update({'account': account, 'account_role': role})
    return render(request, 'admin/privileged_account_edit.html', context)


@login_required(login_url='login_chat')
@user_passes_test(_can_manage_privileged_accounts, login_url='admin_dashboard')
def privileged_account_delete(request, pk):
    account = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        if account == request.user or account.is_superuser:
            messages.error(request, 'این حساب محافظت‌شده قابل حذف نیست.')
        else:
            account.delete()
            messages.success(request, 'حساب با موفقیت حذف شد.')
    return redirect('privileged_accounts')

#  
# ATTENDANCE
#  

@login_required(login_url='login_chat')
def attendance_list(request):
    """
    لیست تمام رکاردهای حضوری
    - نمایش تمام رکاردها در جدول
    - دکمه ویرایش و حذف شامل کریں
    - فرم ثبت حضوری روزانه
    """
    today = timezone.localdate()
    attendances = Attendance.objects.all().order_by('-date', '-id')
    all_employees = Employee.objects.filter(is_active=True).order_by('first_name')
    today_statuses = dict(
        Attendance.objects.filter(date=today).values_list('employee_id', 'status')
    )
    for employee in all_employees:
        employee.today_status = today_statuses.get(employee.id, 'present')
    
    context = {
        'attendances': attendances,
        'all_employees': all_employees,
        'today': today,
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/attendance.html', context)


@login_required(login_url='login_chat')
def attendance_add(request):
    """
    اضافه کردن رکورد حضوری جدید
    - برای هر کارمند
    - یا برای تمام کارمندان در هر روز
    """
    if request.method == 'POST':
        try:
            # بررسی اینکه آیا این رکورد روزانه است یا منفرد
            if request.POST.get('bulk_attendance') == '1':
                # رکورد روزانه - برای تمام کارمندان
                today = timezone.localdate()
                all_employees = Employee.objects.filter(is_active=True)
                
                for emp in all_employees:
                    status = request.POST.get(f'employee_{emp.id}_status', 'present')
                    
                    # بررسی وجود رکورد امروز
                    attendance, created = Attendance.objects.get_or_create(
                        employee=emp,
                        date=today,
                        defaults={'status': status}
                    )
                    
                    # اگر موجود است، بروزرسانی کنید
                    if not created:
                        attendance.status = status
                        attendance.save()
                
                messages.success(request, ' حضوری روزانه با موفقیت ثبت شد')
            else:
                # رکورد منفرد
                employee = Employee.objects.get(id=request.POST.get('employee'))
                attendance = Attendance(
                    employee=employee,
                    date=request.POST.get('date'),
                    check_in_time=request.POST.get('check_in') or None,
                    check_out_time=request.POST.get('check_out') or None,
                    status=request.POST.get('status'),
                    notes=request.POST.get('notes')
                )
                attendance.save()
                messages.success(request, '✅ رکورد حضوری با موفقیت اضافه شد')
            
            return redirect('attendance_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    all_employees = Employee.objects.filter(is_active=True).order_by('first_name')
    return render(request, 'admin/attendance_form.html', 
                  {'employees': all_employees})


@login_required(login_url='login_chat')
def attendance_edit(request, pk):
    """
    ویرایش رکورد حضوری
    """
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        try:
            attendance.employee_id = request.POST.get('employee')
            attendance.date = request.POST.get('date')
            attendance.check_in_time = request.POST.get('check_in') or None
            attendance.check_out_time = request.POST.get('check_out') or None
            attendance.status = request.POST.get('status')
            attendance.notes = request.POST.get('notes')
            attendance.save()
            
            messages.success(request, '✅ رکورد با موفقیت بروزرسانی شد')
            return redirect('attendance_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    employees = Employee.objects.filter(is_active=True).order_by('first_name')
    return render(request, 'admin/attendance_form.html', {
        'attendance': attendance,
        'employees': employees,
        'edit_mode': True
    })


@login_required(login_url='login_chat')
def attendance_delete(request, pk):
    """
    حذف رکورد حضوری
    """
    attendance = get_object_or_404(Attendance, pk=pk)
    
    if request.method == 'POST':
        try:
            employee_name = str(attendance.employee)
            attendance.delete()
            messages.success(request, f'✅ رکورد {employee_name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('attendance_list')

#  
#  TEACHERS
#  

@login_required(login_url='login_chat')
def teachers_list(request):
    """
    لیست تمام معلمان
    - نمایش معلومات معلمان
    - دکمه‌های ویرایش و حذف
    - دکمه افزودن معلم جدید
    """
    teachers = Teacher.objects.all().select_related('user').order_by('-id')
    context = {
        'teachers': teachers,
        'total_teachers': teachers.count(),
        'active_teachers': teachers.filter(is_active=True).count(),
        'subjects_count': teachers.values('subject').distinct().count(),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/teachers.html', context)


@login_required(login_url='login_chat')
def _teacher_payload(request, teacher=None):
    """Validate and normalize teacher data before it is saved."""
    user_fields = ('first_name', 'last_name')
    teacher_fields = ('email', 'phone', 'subject', 'employee_id', 'hire_date')
    payload = {field: request.POST.get(field, '').strip() for field in (*user_fields, *teacher_fields)}

    if any(not payload[field] for field in payload):
        raise ValidationError('لطفاً تمام فیلدهای الزامی را تکمیل کنید.')

    payload['email'] = payload['email'].lower()
    payload['is_active'] = request.POST.get('is_active') == 'on'
    candidate = Teacher(**{field: payload[field] for field in teacher_fields}, is_active=payload['is_active'])
    if teacher:
        candidate.pk = teacher.pk
        candidate.user = teacher.user
        # This represents an existing row. Without this Django's uniqueness
        # validation checks the teacher's own employee ID as a duplicate.
        candidate._state.adding = False
    candidate.full_clean()
    return payload


@login_required(login_url='login_chat')
def teacher_add(request):
    """
    افزودن معلم جدید
    - ایجاد User و Teacher
    """
    if request.method == 'POST':
        try:
            username = request.POST.get('username', '').strip()
            password = request.POST.get('password', '')
            if not username:
                raise ValidationError({'username': 'نام کاربری برای حساب معلم الزامی است.'})
            if User.objects.filter(username__iexact=username).exists():
                raise ValidationError({'username': 'این نام کاربری قبلاً استفاده شده است.'})
            if len(password) < 8:
                raise ValidationError({'password': 'رمز عبور باید حداقل ۸ نویسه داشته باشد.'})

            with transaction.atomic():
                payload = _teacher_payload(request)
                user = User.objects.create_user(
                    username=username,
                    email=payload['email'],
                    first_name=payload['first_name'],
                    last_name=payload['last_name'],
                    password=password,
                )
                teacher = Teacher.objects.create(
                    user=user,
                    **{field: payload[field] for field in ('email', 'phone', 'subject', 'employee_id', 'hire_date', 'is_active')},
                )
                assign_role(user, 'teacher')
            
            messages.success(request, f'✅ معلم {user.first_name} با موفقیت اضافه شد')
            return redirect('teachers_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    return render(request, 'admin/teacher_form.html')


@login_required(login_url='login_chat')
def teacher_edit(request, pk):
    """
    ویرایش معلم
    """
    teacher = get_object_or_404(Teacher, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                payload = _teacher_payload(request, teacher)
                for field in ('email', 'phone', 'subject', 'employee_id', 'hire_date', 'is_active'):
                    setattr(teacher, field, payload[field])
                if teacher.user:
                    teacher.user.first_name = payload['first_name']
                    teacher.user.last_name = payload['last_name']
                    teacher.user.email = payload['email']
                    new_password = request.POST.get('password', '')
                    if new_password:
                        if len(new_password) < 8:
                            raise ValidationError({'password': 'رمز عبور باید حداقل ۸ نویسه داشته باشد.'})
                        teacher.user.set_password(new_password)
                    teacher.user.save()
                    assign_role(teacher.user, 'teacher')
                teacher.save()
            
            messages.success(request, '✅ معلم با موفقیت بروزرسانی شد')
            return redirect('teachers_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    context = {'teacher': teacher, 'edit_mode': True}
    return render(request, 'admin/teacher_form.html', context)


@login_required(login_url='login_chat')
def teacher_delete(request, pk):
    """
    حذف معلم
    """
    teacher = get_object_or_404(Teacher, pk=pk)
    
    if request.method == 'POST':
        try:
            teacher_name = str(teacher)
            user = teacher.user
            teacher.delete()
            if user:
                user.groups.remove(*user.groups.filter(name=ROLE_GROUPS['teacher']))
            messages.success(request, f'✅ معلم {teacher_name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('teachers_list')

#  
#  STUDENTS
#  

@login_required(login_url='login_chat')
def students_list(request):
    """
    لیست تمام شاگردان
    - نمایش اطلاعات شاگردان
    - دکمه‌های ویرایش و حذف
    - دکمه افزودن شاگرد جدید
    """
    students = Student.objects.select_related('user').all().order_by('-id')
    context = {
        'students': students,
        'total_students': students.count(),
        'active_students': students.filter(is_active=True).count(),
        'classes_count': students.values('class_field').distinct().count(),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/students.html', context)


@login_required(login_url='login_chat')
def _student_payload(request, student=None):
    """Validate and normalize student profile data before saving it."""
    fields = ('first_name', 'last_name', 'father_name', 'phone', 'email', 'address', 'student_id', 'class_field', 'enrollment_date')
    payload = {field: request.POST.get(field, '').strip() for field in fields}

    if any(not payload[field] for field in fields):
        raise ValidationError('لطفاً تمام فیلدهای الزامی را تکمیل کنید.')

    payload['email'] = payload['email'].lower()
    payload['is_active'] = request.POST.get('is_active') == 'on'

    if not Class.objects.filter(class_name=payload['class_field'], is_active=True).exists():
        raise ValidationError({'class_field': 'کلاس انتخاب‌شده معتبر یا فعال نیست.'})

    candidate = Student(**payload)
    if student:
        candidate.pk = student.pk
        candidate.user = student.user
        # This represents an existing row. Without this Django's uniqueness
        # validation checks the student's own ID as a duplicate.
        candidate._state.adding = False
    candidate.full_clean()
    return {field: getattr(candidate, field) for field in (*fields, 'is_active')}


@login_required(login_url='login_chat')
def student_add(request):
    """
    افزودن شاگرد جدید + ساختن User account اتوماتیک
    """
    if request.method == 'POST':
        try:
            username = request.POST.get('username','').strip()
            password = request.POST.get('password', '')
            if not username:
                raise ValidationError({'username': 'نام کاربری برای حساب شاگرد الزامی است.'})
            if User.objects.filter(username__iexact=username).exists():
                raise ValidationError({'username': 'این نام کاربری قبلاً استفاده شده است.'})
            if len(password) < 8:
                raise ValidationError({'password': 'رمز عبور باید حداقل ۸ نویسه داشته باشد.'})

            with transaction.atomic():
                payload = _student_payload(request)
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=payload['first_name'],
                    last_name=payload['last_name'],
                    email=payload['email'],
                )
                student = Student.objects.create(user=user, **payload)
                assign_role(user, 'student')
            
            messages.success(request, f'✅ شاگرد {student.first_name} اضافه شد | نام کاربری: {username}')
            return redirect('students_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    return render(request, 'admin/student_form.html', {
        'classes': Class.objects.filter(is_active=True).order_by('level', 'class_name'),
    })

@login_required(login_url='login_chat')
def student_edit(request, pk):
    """
    ویرایش شاگرد
    """
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for field, value in _student_payload(request, student).items():
                    setattr(student, field, value)
                if student.user:
                    student.user.first_name = student.first_name
                    student.user.last_name = student.last_name
                    student.user.email = student.email
                    new_password = request.POST.get('password', '')
                    if new_password:
                        if len(new_password) < 8:
                            raise ValidationError({'password': 'رمز عبور باید حداقل ۸ نویسه داشته باشد.'})
                        student.user.set_password(new_password)
                    student.user.save()
                student.save()
            messages.success(request, '✅ شاگرد بروزرسانی شد')
            return redirect('students_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    context = {
        'student': student,
        'edit_mode': True,
        'classes': Class.objects.filter(is_active=True).order_by('level', 'class_name'),
    }
    return render(request, 'admin/student_form.html', context)


@login_required(login_url='login_chat')
def student_delete(request, pk):
    """
    حذف شاگرد
    """
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        try:
            student_name = student.first_name
            student.delete()
            messages.success(request, f'✅ شاگرد {student_name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('students_list')

#  
#  FINANCE
#  

@login_required(login_url='login_chat')
def finance_list(request):
    """
    لیست تمام ترانسکشن‌های مالی
    - نمایش درآمد، هزینه، درآمد خالص
    - جدول تمام ترانسکشن‌ها
    - دکمه‌های Edit و Delete
    """
    transactions = Transaction.objects.select_related('student').all().order_by('-transaction_date', '-id')
    completed_transactions = transactions.filter(status='completed')

    # Only completed transactions are counted in realised financial totals.
    total_income = completed_transactions.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = completed_transactions.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    
    net_income = total_income - total_expense
    total_payments = completed_transactions.filter(
        transaction_type='income', student__isnull=False
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': net_income,
        'total_payments': total_payments,
        'pending_transactions': transactions.filter(status='pending').count(),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/finance.html', context)


@login_required(login_url='login_chat')
def _transaction_payload(request, transaction=None):
    """Validate and normalize transaction values before they affect financial records."""
    fields = ('transaction_type', 'amount', 'transaction_date', 'category', 'status')
    payload = {field: request.POST.get(field, '').strip() for field in fields}
    # A normal transaction is not a student-fee record. Fees are stored through
    # StudentPayment, where the student relationship is required.
    payload['description'] = request.POST.get('description', '').strip() or '—'

    if any(not payload[field] for field in fields):
        raise ValidationError('لطفاً تمام فیلدهای الزامی ترانسکشن را تکمیل کنید.')
    if payload['transaction_type'] not in {'income', 'expense'}:
        raise ValidationError({'transaction_type': 'نوع ترانسکشن معتبر نیست.'})
    if payload['status'] not in {'completed', 'pending'}:
        raise ValidationError({'status': 'وضعیت ترانسکشن معتبر نیست.'})

    payload['student_id'] = None

    candidate = Transaction(
        transaction_id=transaction.transaction_id if transaction else 'VALIDATION-ONLY',
        **payload,
    )
    if transaction:
        candidate.pk = transaction.pk
    candidate.full_clean(exclude=['transaction_id'])
    if candidate.amount <= 0:
        raise ValidationError({'amount': 'مبلغ باید بزرگ‌تر از صفر باشد.'})
    return {field: getattr(candidate, field) for field in (*fields, 'description', 'student_id')}


@login_required(login_url='login_chat')
def transaction_add(request):
    """
    افزودن ترانسکشن جدید - با auto-generate transaction_id
    """
    is_finance = request.resolver_match.url_name.startswith('finance_')
    if request.method == 'POST':
        try:
            import uuid
            from datetime import date as _date

            with transaction.atomic():
                # Use a generated immutable ID, avoiding user-supplied collisions.
                trx_id = f"TRX-{_date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                Transaction.objects.create(transaction_id=trx_id, **_transaction_payload(request))
            messages.success(request, 'ترانسکشن با موفقیت اضافه شد')
            if is_finance:
                return redirect('finance_transactions')
            return redirect('finance_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
            if is_finance:
                return redirect('finance_transaction_add')

    students = Student.objects.filter(is_active=True).order_by('first_name', 'last_name')
    if is_finance:
        context = _finance_page_context(request)
        context['all_students'] = students
        return render(request, 'finance/transactions/add.html', context)
    return render(request, 'admin/transaction_form.html', {'students': students})


@login_required(login_url='login_chat')
def transaction_edit(request, pk):
    """
    ویرایش ترانسکشن    """
    is_finance = request.resolver_match.url_name.startswith('finance_')
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        try:
            for field, value in _transaction_payload(request, transaction).items():
                setattr(transaction, field, value)
            transaction.save()
            
            messages.success(request, '✅ ترانسکشن با موفقیت بروزرسانی شد')
            if is_finance:
                return redirect('finance_transactions')
            return redirect('finance_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    students = Student.objects.filter(is_active=True).order_by('first_name', 'last_name')
    if is_finance:
        context = _finance_page_context(request)
        context.update({'transaction': transaction, 'all_students': students, 'edit_mode': True})
        return render(request, 'finance/transactions/add.html', context)
    return render(request, 'admin/transaction_form.html', {
        'transaction': transaction,
        'students': students,
        'edit_mode': True
    })


@login_required(login_url='login_chat')
def transaction_delete(request, pk):
    """
    حذف ترانسکشن    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        try:
            transaction.delete()
            messages.success(request, '✅ ترانسکشن با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    if request.resolver_match.url_name.startswith('finance_'):
        return redirect('finance_transactions')
    return redirect('finance_list')

#  
#  EMPLOYEES
#  

@login_required(login_url='login_chat')
def employees_list(request):
    """
    لیست تمام کارمندان
    - نمایش اطلاعات کارمندان
    - آمار: کل حقوق، میانگین حقوق
    - دکمه‌های Edit و Delete
    """
    employees = Employee.objects.all().order_by('-id')
    
    # محاسبه آمار
    total_employees = employees.count()
    active_employees = employees.filter(is_active=True).count()
    salary_summary = employees.aggregate(total=Sum('salary'), average=Avg('salary'))
    total_salary = salary_summary['total'] or 0
    avg_salary = salary_summary['average'] or 0
    
    context = {
        'employees': employees,
        'total_employees': total_employees,
        'active_employees': active_employees,
        'total_salary': total_salary,
        'avg_salary': avg_salary,
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/employees.html', context)


@login_required(login_url='login_chat')
def _employee_payload(request, employee=None):
    """Validate and normalize employee data before it is saved."""
    fields = ('first_name', 'last_name', 'position', 'phone', 'email', 'employee_id', 'salary', 'hire_date')
    payload = {field: request.POST.get(field, '').strip() for field in fields}

    if any(not payload[field] for field in fields):
        raise ValidationError('لطفاً تمام فیلدهای الزامی را تکمیل کنید.')

    payload['email'] = payload['email'].lower()
    payload['is_active'] = request.POST.get('is_active') == 'on'

    candidate = Employee(**payload)
    if employee:
        candidate.pk = employee.pk
        candidate.user = employee.user
    candidate.full_clean()

    if candidate.salary <= 0:
        raise ValidationError({'salary': 'حقوق باید بزرگ‌تر از صفر باشد.'})

    return {field: getattr(candidate, field) for field in (*fields, 'is_active')}


@login_required(login_url='login_chat')
def employee_add(request):
    """
    افزودن کارمند جدید
    """
    if request.method == 'POST':
        try:
            employee = Employee.objects.create(**_employee_payload(request))
            
            messages.success(request, f'✅ کارمند {employee.first_name} با موفقیت اضافه شد')
            return redirect('employees_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    ctx = {}
    ctx.update(_get_profile_context(request.user))
    return render(request, 'admin/employee_form.html', ctx)


@login_required(login_url='login_chat')
def employee_edit(request, pk):
    """
    ویرایش کارمند
    """
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        try:
            for field, value in _employee_payload(request, employee).items():
                setattr(employee, field, value)
            employee.save()
            
            messages.success(request, '✅ کارمند با موفقیت بروزرسانی شد')
            return redirect('employees_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    ctx = {'employee': employee, 'edit_mode': True}
    ctx.update(_get_profile_context(request.user))
    return render(request, 'admin/employee_form.html', ctx)


@login_required(login_url='login_chat')
def employee_delete(request, pk):
    """
    حذف کارمند
    """
    employee = get_object_or_404(Employee, pk=pk)
    
    if request.method == 'POST':
        try:
            employee_name = employee.first_name
            employee.delete()
            messages.success(request, f'✅ کارمند {employee_name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('employees_list')

#  
#  MEDICAL (DOCTOR)
#  

@login_required(login_url='login_chat')
def medical_list(request):
    """
    لیست تمام معاینات پزشکی
    - نمایش تمام معاینات
    - آمار: کل معاینات، شاگردان تحت مراقبت
    - دکمه‌های Edit و Delete
    """
    medical_records = Medical.objects.select_related('student').all().order_by('-checkup_date')
    
    # محاسبه آمار
    total_checkups = medical_records.count()
    students_checked = medical_records.values('student').distinct().count()
    healthy_students = medical_records.filter(
        Q(health_status='excellent') | Q(health_status='good')
    ).count()
    care_needed = medical_records.filter(health_status='needs_care').count()
    
    context = {
        'medical_records': medical_records,
        'total_checkups': total_checkups,
        'students_checked': students_checked,
        'healthy_students': healthy_students,
        'care_needed': care_needed,
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/medical.html', context)


@login_required(login_url='login_chat')
def _medical_payload(request, medical=None):
    """Validate and normalize the current health record for a student."""
    student_id = request.POST.get('student', '').strip()
    student = Student.objects.filter(pk=student_id).first()
    if not student or (not student.is_active and (not medical or medical.student_id != student.pk)):
        raise ValidationError({'student': 'شاگرد انتخاب‌شده معتبر یا فعال نیست.'})

    payload = {
        'student': student,
        'checkup_date': request.POST.get('checkup_date', '').strip(),
        'height': request.POST.get('height', '').strip() or None,
        'weight': request.POST.get('weight', '').strip() or None,
        'blood_pressure': request.POST.get('blood_pressure', '').strip(),
        'temperature': request.POST.get('temperature', '').strip() or None,
        'diagnosis': request.POST.get('diagnosis', '').strip(),
        'recommendations': request.POST.get('recommendations', '').strip(),
        'health_status': request.POST.get('health_status', '').strip(),
    }
    if not payload['checkup_date'] or not payload['health_status']:
        raise ValidationError('تاریخ معاینه و وضعیت سلامتی الزامی هستند.')

    candidate = Medical(**payload)
    if medical:
        candidate.pk = medical.pk
    candidate.full_clean()

    if candidate.height is not None and not 0 < candidate.height <= 300:
        raise ValidationError({'height': 'قد باید بین ۰ تا ۳۰۰ سانتی‌متر باشد.'})
    if candidate.weight is not None and not 0 < candidate.weight <= 300:
        raise ValidationError({'weight': 'وزن باید بین ۰ تا ۳۰۰ کیلوگرم باشد.'})
    if candidate.temperature is not None and not 25 <= candidate.temperature <= 45:
        raise ValidationError({'temperature': 'دما باید بین ۲۵ تا ۴۵ درجه سلسیوس باشد.'})

    return {
        'student_id': candidate.student_id,
        'checkup_date': candidate.checkup_date,
        'height': candidate.height,
        'weight': candidate.weight,
        'blood_pressure': candidate.blood_pressure,
        'temperature': candidate.temperature,
        'diagnosis': candidate.diagnosis,
        'recommendations': candidate.recommendations,
        'health_status': candidate.health_status,
    }


@login_required(login_url='login_chat')
def medical_add(request):
    """
    افزودن معاینه جدید
    """
    if request.method == 'POST':
        try:
            Medical.objects.create(**_medical_payload(request))
            
            messages.success(request, '✅ معاینه با موفقیت اضافه شد')
            return redirect('medical_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    students = Student.objects.filter(is_active=True).order_by('first_name', 'last_name')
    return render(request, 'admin/medical_form.html', {'students': students})


@login_required(login_url='login_chat')
def medical_edit(request, pk):
    """
    ویرایش معاینه
    """
    medical = get_object_or_404(Medical, pk=pk)
    
    if request.method == 'POST':
        try:
            for field, value in _medical_payload(request, medical).items():
                setattr(medical, field, value)
            medical.save()
            
            messages.success(request, '✅ معاینه با موفقیت بروزرسانی شد')
            return redirect('medical_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    students = Student.objects.filter(Q(is_active=True) | Q(pk=medical.student_id)).order_by('first_name', 'last_name')
    return render(request, 'admin/medical_form.html', {
        'medical': medical,
        'students': students,
        'edit_mode': True
    })


@login_required(login_url='login_chat')
def medical_delete(request, pk):
    """
    حذف معاینه
    """
    medical = get_object_or_404(Medical, pk=pk)
    
    if request.method == 'POST':
        try:
            student_name = medical.student.first_name
            medical.delete()
            messages.success(request, f'✅ معاینه {student_name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('medical_list')

#  
#  REPORTS
#  

_REPORT_MONTHS_FA = ('جنوری', 'فبروری', 'مارچ', 'اپریل', 'می', 'جون', 'جولای', 'اگست', 'سپتمبر', 'اکتوبر', 'نومبر', 'دسمبر')


def _admin_report_context(request):
    today = timezone.localdate()
    try:
        selected_month = int(request.GET.get('month', today.month))
        selected_year = int(request.GET.get('year', today.year))
    except (TypeError, ValueError):
        selected_month, selected_year = today.month, today.year
    if selected_month not in range(1, 13) or selected_year < 2000 or selected_year > today.year + 1:
        selected_month, selected_year = today.month, today.year

    student_summary = Student.objects.aggregate(
        total=Count('id'), active=Count('id', filter=Q(is_active=True)),
    )
    teacher_summary = Teacher.objects.aggregate(
        total=Count('id'), active=Count('id', filter=Q(is_active=True)),
    )
    employee_summary = Employee.objects.aggregate(
        total=Count('id'), active=Count('id', filter=Q(is_active=True)),
        active_salary=Sum('salary', filter=Q(is_active=True)),
    )
    attendance_summary = Attendance.objects.filter(
        date__year=selected_year, date__month=selected_month,
    ).aggregate(
        total=Count('id'), present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')), leave=Count('id', filter=Q(status='leave')),
    )
    finance_summary = Transaction.objects.filter(
        status='completed', transaction_date__year=selected_year, transaction_date__month=selected_month,
    ).aggregate(
        income=Sum('amount', filter=Q(transaction_type='income')),
        expenses=Sum('amount', filter=Q(transaction_type='expense')),
        income_count=Count('id', filter=Q(transaction_type='income')),
        expense_count=Count('id', filter=Q(transaction_type='expense')),
    )
    medical_summary = Medical.objects.filter(
        checkup_date__year=selected_year, checkup_date__month=selected_month,
    ).aggregate(
        total=Count('id'), excellent=Count('id', filter=Q(health_status='excellent')),
        needs_care=Count('id', filter=Q(health_status='needs_care')),
    )
    class_summary = Class.objects.aggregate(
        total=Count('id'), active=Count('id', filter=Q(is_active=True)),
        active_capacity=Sum('capacity', filter=Q(is_active=True)),
    )
    total_income = finance_summary['income'] or 0
    total_expenses = finance_summary['expenses'] or 0
    active_students = student_summary['active'] or 0
    active_capacity = class_summary['active_capacity'] or 0

    context = {
        # Students
        'total_students': student_summary['total'],
        'active_students': active_students,
        'inactive_students': student_summary['total'] - active_students,
        # Teachers
        'total_teachers': teacher_summary['total'],
        'active_teachers': teacher_summary['active'],
        'inactive_teachers': teacher_summary['total'] - teacher_summary['active'],
        # Employees
        'total_employees': employee_summary['total'],
        'active_employees': employee_summary['active'],
        'total_salary': employee_summary['active_salary'] or 0,
        # Attendance
        'total_attendance': attendance_summary['total'],
        'present_count': attendance_summary['present'],
        'absent_count': attendance_summary['absent'],
        'leave_count': attendance_summary['leave'],
        # Finance
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_balance': total_income - total_expenses,
        'total_income_count': finance_summary['income_count'],
        'total_expense_count': finance_summary['expense_count'],
        # Medical
        'total_medical': medical_summary['total'],
        'excellent_health': medical_summary['excellent'],
        'needs_care': medical_summary['needs_care'],
        # Classes
        'total_classes': class_summary['total'],
        'active_classes': class_summary['active'],
        'total_capacity': active_capacity,
        'capacity_usage': round((active_students / active_capacity) * 100) if active_capacity else 0,
        'report_date': today,
        'selected_month': selected_month,
        'selected_year': selected_year,
        'report_month_name': _REPORT_MONTHS_FA[selected_month - 1],
        'report_months': list(enumerate(_REPORT_MONTHS_FA, 1)),
        'report_years': list(range(today.year + 1, max(2019, today.year - 5), -1)),
    }
    context.update(_get_profile_context(request.user))
    return context


@login_required(login_url='login_chat')
def reports(request):
    return render(request, 'admin/reports.html', _admin_report_context(request))


def _admin_pdf_document(context):
    """Build a Farsi executive PDF report with no browser dependency."""
    from io import BytesIO
    from PIL import Image, ImageDraw, ImageFont

    forms = {
        'ا': ('\ufe8d', '\ufe8e'), 'آ': ('\ufe81', '\ufe82'), 'ب': ('\ufe8f', '\ufe90', '\ufe91', '\ufe92'),
        'پ': ('\ufb56', '\ufb57', '\ufb58', '\ufb59'), 'ت': ('\ufe95', '\ufe96', '\ufe97', '\ufe98'),
        'ث': ('\ufe99', '\ufe9a', '\ufe9b', '\ufe9c'), 'ج': ('\ufe9d', '\ufe9e', '\ufe9f', '\ufea0'),
        'چ': ('\ufb7a', '\ufb7b', '\ufb7c', '\ufb7d'), 'ح': ('\ufea1', '\ufea2', '\ufea3', '\ufea4'),
        'خ': ('\ufea5', '\ufea6', '\ufea7', '\ufea8'), 'د': ('\ufea9', '\ufeaa'), 'ذ': ('\ufeab', '\ufeac'),
        'ر': ('\ufead', '\ufeae'), 'ز': ('\ufeaf', '\ufeb0'), 'ژ': ('\ufb8a', '\ufb8b'),
        'س': ('\ufeb1', '\ufeb2', '\ufeb3', '\ufeb4'), 'ش': ('\ufeb5', '\ufeb6', '\ufeb7', '\ufeb8'),
        'ص': ('\ufeb9', '\ufeba', '\ufebb', '\ufebc'), 'ض': ('\ufebd', '\ufebe', '\ufebf', '\ufec0'),
        'ط': ('\ufec1', '\ufec2', '\ufec3', '\ufec4'), 'ظ': ('\ufec5', '\ufec6', '\ufec7', '\ufec8'),
        'ع': ('\ufec9', '\ufeca', '\ufecb', '\ufecc'), 'غ': ('\ufecd', '\ufece', '\ufecf', '\ufed0'),
        'ف': ('\ufed1', '\ufed2', '\ufed3', '\ufed4'), 'ق': ('\ufed5', '\ufed6', '\ufed7', '\ufed8'),
        'ک': ('\ufb8e', '\ufb8f', '\ufb90', '\ufb91'), 'گ': ('\ufb92', '\ufb93', '\ufb94', '\ufb95'),
        'ل': ('\ufedd', '\ufede', '\ufedf', '\ufee0'), 'م': ('\ufee1', '\ufee2', '\ufee3', '\ufee4'),
        'ن': ('\ufee5', '\ufee6', '\ufee7', '\ufee8'), 'و': ('\ufeed', '\ufeee'),
        'ه': ('\ufee9', '\ufeea', '\ufeeb', '\ufeec'), 'ی': ('\ufbfc', '\ufbfd', '\ufbfe', '\ufbff'),
    }

    def farsi(value):
        source = str(value)
        shaped = []
        for index, char in enumerate(source):
            glyphs = forms.get(char)
            if not glyphs:
                shaped.append(char); continue
            previous = forms.get(source[index - 1]) if index else None
            following = forms.get(source[index + 1]) if index + 1 < len(source) else None
            joins_previous = bool(previous and len(previous) == 4)
            joins_next = bool(len(glyphs) == 4 and following)
            shaped.append(glyphs[3] if joins_previous and joins_next else glyphs[1] if joins_previous else glyphs[2] if joins_next else glyphs[0])
        visual = ''.join(shaped)[::-1]
        import re
        return re.sub(r'[0-9.,]+', lambda match: match.group(0)[::-1], visual)

    image = Image.new('RGB', (1240, 1754), '#f8fafc')
    draw = ImageDraw.Draw(image)
    font_path = r'C:\Windows\Fonts\tahoma.ttf'
    title_font, section_font, body_font, value_font = (ImageFont.truetype(font_path, size) for size in (42, 25, 20, 23))

    def rtl(text, y, font, color='#172554', right=1165):
        draw.text((right, y), farsi(text), font=font, fill=color, anchor='ra')

    draw.rectangle((0, 0, 1240, 220), fill='#102a54')
    rtl('کودکستان گام', 48, title_font, '#ffffff')
    rtl('گزارش مدیریتی ماهانه', 112, section_font, '#dbeafe')
    rtl(f'دوره گزارش: {context["report_month_name"]} {context["selected_year"]}', 254, section_font)
    rtl(f'تاریخ تولید: {timezone.localdate().isoformat()}', 294, body_font, '#475569')
    draw.line((75, 338, 1165, 338), fill='#93c5fd', width=3)

    sections = [
        ('شاگردان و کلاس‌ها', [
            ('کل شاگردان', context['total_students']), ('شاگردان فعال', context['active_students']),
            ('کلاس‌های فعال', f"{context['active_classes']} / {context['total_classes']}"), ('استفاده از ظرفیت', f"{context['capacity_usage']}%"),
        ]),
        ('نیروی انسانی', [
            ('معلمان فعال', context['active_teachers']), ('کارمندان فعال', context['active_employees']),
            ('مجموع حقوق فعال', f"AFN {context['total_salary']}"),
        ]),
        ('عملیات ماهانه', [
            ('رکوردهای حضور', context['total_attendance']), ('حاضر', context['present_count']),
            ('غایب', context['absent_count']), ('معاینات صحی', context['total_medical']),
        ]),
        ('وضعیت مالی ماهانه', [
            ('درآمد تکمیل‌شده', f"AFN {context['total_income']}"), ('هزینه تکمیل‌شده', f"AFN {context['total_expenses']}"),
            ('تراز خالص', f"AFN {context['net_balance']}"), ('تعداد ترانسکشن‌ها', context['total_income_count'] + context['total_expense_count']),
        ]),
    ]
    for section_index, (section, rows) in enumerate(sections):
        column, row = section_index % 2, section_index // 2
        left, top, width = 75 + column * 550, 370 + row * 600, 515
        draw.rounded_rectangle((left, top, left + width, top + 52), radius=13, fill='#1d4ed8')
        rtl(section, top + 12, section_font, '#ffffff', left + width - 30)
        y = top + 64
        for label, value in rows:
            draw.rounded_rectangle((left, y, left + width, y + 48), radius=8, fill='#ffffff', outline='#dbeafe', width=2)
            rtl(label, y + 12, body_font, '#475569', left + width - 30)
            draw.text((left + 28, y + 11), str(value), font=value_font, fill='#102a54')
            y += 58
    rtl('مدیریت گام | محرمانه', 1668, body_font, '#64748b')
    buffer = BytesIO(); image.save(buffer, format='JPEG', quality=92, optimize=True); jpeg = buffer.getvalue()
    content = b'q 595 0 0 842 0 0 cm /Im0 Do Q'
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>', b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /XObject << /Im0 5 0 R >> >> /Contents 4 0 R >>',
        f'<< /Length {len(content)} >>\nstream\n'.encode() + content + b'\nendstream',
        f'<< /Type /XObject /Subtype /Image /Width 1240 /Height 1754 /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\nstream\n'.encode() + jpeg + b'\nendstream',
    ]
    output, offsets = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n'), [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output)); output.extend(f'{number} 0 obj\n'.encode()); output.extend(obj); output.extend(b'\nendobj\n')
    xref = len(output); output.extend(b'xref\n0 6\n0000000000 65535 f \n'); output.extend(b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])); output.extend(f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode())
    return bytes(output)


@login_required(login_url='login_chat')
def admin_report_pdf(request):
    context = _admin_report_context(request)
    response = HttpResponse(_admin_pdf_document(context), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="gaam-admin-report-{context["selected_year"]}-{context["selected_month"]:02d}.pdf"'
    return response

#  
# CLASSES
#  

@login_required(login_url='login_chat')
def _class_payload(request):
    """Validate and normalize the fields shared by class create and edit."""
    class_name = request.POST.get('class_name', '').strip()
    level = request.POST.get('level', '').strip()
    room_number = request.POST.get('room_number', '').strip()
    capacity_value = request.POST.get('capacity', '').strip()

    if not class_name or not level or not room_number or not capacity_value:
        raise ValueError('نام، سطح، اتاق و ظرفیت کلاس الزامی هستند.')
    try:
        capacity = int(capacity_value)
    except (TypeError, ValueError):
        raise ValueError('ظرفیت باید یک عدد صحیح باشد.')
    if capacity <= 0:
        raise ValueError('ظرفیت کلاس باید بیشتر از صفر باشد.')

    teacher = None
    teacher_id = request.POST.get('teacher')
    if teacher_id:
        teacher = Teacher.objects.filter(pk=teacher_id, is_active=True).first()
        if teacher is None:
            raise ValueError('معلم انتخاب‌شده معتبر یا فعال نیست.')

    return {
        'class_name': class_name,
        'level': level,
        'room_number': room_number,
        'capacity': capacity,
        'teacher': teacher,
        'is_active': request.POST.get('is_active') == 'on',
    }


@login_required(login_url='login_chat')
def classes_list(request):
    classes = Class.objects.all().select_related('teacher__user').order_by('class_name')
    student_counts = dict(
        Student.objects.filter(is_active=True)
        .values('class_field')
        .annotate(count=Count('id'))
        .values_list('class_field', 'count')
    )
    for c in classes:
        c.student_count = student_counts.get(c.class_name, 0)

    context = {
        'classes': classes,
        'teachers': Teacher.objects.filter(is_active=True).select_related('user'),
        'total_classes': Class.objects.count(),
        'active_classes': Class.objects.filter(is_active=True).count(),
        'total_students': Student.objects.filter(is_active=True).count(),
        'total_capacity': int(Class.objects.aggregate(s=Sum('capacity'))['s'] or 0),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/classes.html', context)


@login_required(login_url='login_chat')
def class_add(request):
    if request.method == 'POST':
        try:
            Class.objects.create(**_class_payload(request))
            messages.success(request, '✅ کلاس با موفقیت اضافه شد')
            return redirect('classes_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    # GET: نمایش فرم
    teachers = Teacher.objects.filter(is_active=True).select_related('user')
    context = {'teachers': teachers}
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/class_form.html', context)


@login_required(login_url='login_chat')
def class_edit(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    if request.method == 'POST':
        try:
            payload = _class_payload(request)
            old_name = class_obj.class_name
            with transaction.atomic():
                for field, value in payload.items():
                    setattr(class_obj, field, value)
                class_obj.save()
                if old_name != class_obj.class_name:
                    Student.objects.filter(class_field=old_name).update(
                        class_field=class_obj.class_name
                    )
            messages.success(request, '✅ کلاس با موفقیت ویرایش شد')
            return redirect('classes_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    # GET: نمایش فرم ویرایش
    teachers = Teacher.objects.filter(is_active=True).select_related('user')
    context = {'class': class_obj, 'teachers': teachers, 'edit_mode': True}
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/class_form.html', context)


@login_required(login_url='login_chat')
def class_delete(request, pk):
    class_obj = get_object_or_404(Class, pk=pk)
    if request.method == 'POST':
        try:
            name = class_obj.class_name
            class_obj.delete()
            messages.success(request, f'✅ کلاس {name} با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('classes_list')

#  
# 🔟 PROFILE
#  

def _get_or_create_profile(user):
    """Helper: get or create UserProfile safely"""
    try:
        from .models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=user)
        return profile
    except Exception:
        return None


@login_required(login_url='login_chat')
def profile(request):
    """صفحه پروفایل - با UserProfile"""
    ctx = _get_profile_context(request.user)
    context = {
        'user': request.user,
        'profile_picture':    ctx.get('profile_picture'),
        'profile_phone':      ctx.get('profile_phone', ''),
        'profile_bio':        ctx.get('profile_bio', ''),
        'username':           ctx.get('username', request.user.username),
    }
    try:
        from .models import UserProfile
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        context['profile_department'] = profile_obj.department or 'Administration'
    except Exception:
        context['profile_department'] = 'Administration'
    
    return render(request, 'admin/profile.html', context)


@login_required(login_url='login_chat')
def profile_update(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        user = request.user

        if form_type == 'info':
            try:
                user.first_name = request.POST.get('first_name', '').strip()
                user.last_name = request.POST.get('last_name', '').strip()
                user.email = request.POST.get('email', '').strip().lower()
                if not user.first_name or not user.last_name or not user.email:
                    raise ValidationError('نام، نام خانوادگی و ایمیل الزامی هستند.')
                user.full_clean()
                user.save()

                profile = _get_or_create_profile(user)
                if profile:
                    profile.phone = request.POST.get('phone', '').strip()
                    profile.department = request.POST.get('department', '').strip() or 'Administration'
                    profile.bio = request.POST.get('bio', '').strip()
                    profile.full_clean(exclude=['profile_picture'])
                    profile.save()

                messages.success(request, '✅ معلومات شخصی با موفقیت ذخیره شد')
            except ValidationError as error:
                messages.error(request, f'خطا: {error.messages[0]}')

        elif form_type == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not user.check_password(current_password):
                messages.error(request, '❌ پسورد فعلی اشتباه است')
            elif new_password != confirm_password:
                messages.error(request, '❌ پسورد جدید با تأیید آن مطابقت ندارد')
            elif len(new_password) < 8:
                messages.error(request, '❌ پسورد باید حداقل 8 کاراکتر باشد')
            else:
                try:
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, '✅ پسورد با موفقیت تغییر کرد')
                except Exception as e:
                    messages.error(request, f'❌ خطا: {str(e)}')

    return redirect('profile')


@login_required(login_url='login_chat')
def profile_upload_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            uploaded_picture = request.FILES['profile_picture']
            if uploaded_picture.size > 5 * 1024 * 1024:
                raise ValidationError('حجم عکس نباید بیشتر از ۵ مگابایت باشد.')
            if uploaded_picture.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise ValidationError('فقط فایل‌های JPEG، PNG یا WebP قابل قبول هستند.')
            profile = _get_or_create_profile(request.user)
            if profile:
                profile.profile_picture = uploaded_picture
                profile.full_clean()
                profile.save()
                messages.success(request, '✅ عکس پروفایل با موفقیت تغییر کرد')
            else:
                messages.error(request, '❌ پروفایل کاربر پیدا نشد')
        except ValidationError as error:
            messages.error(request, f'خطا در آپلود: {error.messages[0]}')
    return redirect('profile')


#  
# teacher_dashboard
#  

def _linked_teacher_for_user(user):
    """Return the teacher owned by this account, repairing only safe legacy links."""
    teacher = Teacher.objects.filter(user=user).first()
    if not teacher and user.email:
        teacher = Teacher.objects.filter(email__iexact=user.email, user__isnull=True).first()
        if teacher:
            teacher.user = user
            teacher.save(update_fields=['user'])
    return teacher


def _teacher_students_queryset(user):
    teacher = _linked_teacher_for_user(user)
    if not teacher:
        return teacher, Student.objects.none()
    class_names = Class.objects.filter(teacher=teacher, is_active=True).values_list('class_name', flat=True)
    return teacher, Student.objects.filter(class_field__in=class_names)


@login_required(login_url='login_chat')
def teacher_dashboard(request):
    """Teacher dashboard limited to the logged-in teacher's assigned classes."""
    teacher = _linked_teacher_for_user(request.user)

    today = timezone.localdate()
    assigned_classes = Class.objects.filter(teacher=teacher, is_active=True) if teacher else Class.objects.none()
    class_names = assigned_classes.values_list('class_name', flat=True)
    all_students = Student.objects.filter(class_field__in=class_names).order_by('-created_at')
    student_names = [f'{student.first_name} {student.last_name}'.strip() for student in all_students]
    student_presence = StudentPresence.objects.filter(student_name__in=student_names).order_by('-date')
    health_reports = StudentHealthReport.objects.filter(student_name__in=student_names).order_by('-date')
    teacher_presence = TeacherPresence.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPresence.objects.none()
    plans = TeacherPlan.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPlan.objects.none()
    timetable = TeacherTimetable.objects.filter(teacher=teacher).order_by('day', 'time_slot') if teacher else TeacherTimetable.objects.none()

    # Stats only for this teacher and their students.
    total_students = all_students.count()
    active_students = all_students.filter(is_active=True).count()
    inactive_students = total_students - active_students
    present_today = student_presence.filter(date=today, status='present').count()
    absent_today = student_presence.filter(date=today, status='absent').count()
    total_plans = plans.count()
    sp_present = student_presence.filter(status='present').count()
    sp_absent = student_presence.filter(status='absent').count()
    sp_leave = student_presence.filter(status='leave').count()
    tp_present = teacher_presence.filter(status='present').count()
    tp_absent = teacher_presence.filter(status='absent').count()
    tp_total         = tp_present + tp_absent
    tp_rate          = round(tp_present / tp_total * 100) if tp_total else 0
    h_excellent = health_reports.filter(health_status='excellent').count()
    h_good = health_reports.filter(health_status='good').count()
    h_care = health_reports.filter(health_status='needs_care').count()
    all_classes = assigned_classes

    # Profile
    try:
        from .models import UserProfile
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_phone      = profile_obj.phone or ''
        profile_department = profile_obj.department or 'تدریس'
        profile_bio        = profile_obj.bio or ''
        profile_picture    = profile_obj.profile_picture.url if profile_obj.profile_picture else None
    except Exception:
        profile_phone = profile_department = profile_bio = ''
        profile_picture = None

    context = {
        'teacher': teacher,
        'username': request.user.first_name or request.user.username,
        'today': str(today),
        # stats
        'total_students': total_students,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'present_today': present_today,
        'absent_today': absent_today,
        'total_plans': total_plans,
        'assigned_class_count': assigned_classes.count(),
        'sp_present': sp_present,
        'sp_absent': sp_absent,
        'sp_leave': sp_leave,
        'tp_present': tp_present,
        'tp_absent': tp_absent,
        'tp_rate': tp_rate,
        'h_excellent': h_excellent,
        'h_good': h_good,
        'h_care': h_care,
        # querysets
        'all_students': all_students,
        'student_presence': student_presence,
        'teacher_presence': teacher_presence,
        'health_reports': health_reports,
        'plans': plans,
        'timetable': timetable,
        'all_classes': all_classes,
        # timetable grid
        'time_slots': ['7:30 - 8:15','8:15 - 9:00','9:15 - 10:00','10:00 - 10:45','11:00 - 11:45','11:45 - 12:30'],
        'days_list': ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه'],
        # profile
        'profile_phone': profile_phone,
        'profile_department': profile_department,
        'profile_bio': profile_bio,
        'profile_picture': profile_picture,
    }
    return render(request, 'teacher/dashboard.html', context)


# ════════════════════════════════════════
# TEACHER: Students
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_students(request):
    return render(request, 'teacher/students/list.html', _teacher_page_context(request))


def _teacher_page_context(request):
    teacher, all_students = _teacher_students_queryset(request.user)
    all_students = all_students.order_by('-created_at')
    today = timezone.localdate()
    names = [f'{s.first_name} {s.last_name}'.strip() for s in all_students]
    student_presence = StudentPresence.objects.filter(student_name__in=names).order_by('-date')
    health_reports = StudentHealthReport.objects.filter(student_name__in=names).order_by('-date')
    teacher_presence = TeacherPresence.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPresence.objects.none()
    plans = TeacherPlan.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPlan.objects.none()
    timetable = TeacherTimetable.objects.filter(teacher=teacher).order_by('day', 'time_slot') if teacher else TeacherTimetable.objects.none()
    total = all_students.count()
    active = all_students.filter(is_active=True).count()
    tp_present = teacher_presence.filter(status='present').count()
    tp_absent = teacher_presence.filter(status='absent').count()
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    return {
        'teacher': teacher, 'username': request.user.first_name or request.user.username, 'today': str(today),
        'all_students': all_students, 'total_students': total, 'active_students': active, 'inactive_students': total - active,
        'all_classes': Class.objects.filter(teacher=teacher, is_active=True) if teacher else Class.objects.none(),
        'student_presence': student_presence, 'present_today': student_presence.filter(date=today, status='present').count(),
        'absent_today': student_presence.filter(date=today, status='absent').count(),
        'sp_present': student_presence.filter(status='present').count(), 'sp_absent': student_presence.filter(status='absent').count(),
        'sp_leave': student_presence.filter(status='leave').count(), 'health_reports': health_reports,
        'h_excellent': health_reports.filter(health_status='excellent').count(), 'h_good': health_reports.filter(health_status='good').count(),
        'h_care': health_reports.filter(health_status='needs_care').count(), 'teacher_presence': teacher_presence,
        'tp_present': tp_present, 'tp_absent': tp_absent, 'tp_rate': round(tp_present / (tp_present + tp_absent) * 100) if tp_present + tp_absent else 0,
        'plans': plans, 'total_plans': plans.count(), 'timetable': timetable,
        'time_slots': ['7:30 - 8:15', '8:15 - 9:00', '9:15 - 10:00', '10:00 - 10:45', '11:00 - 11:45', '11:45 - 12:30'],
        'days_list': ['شنبه', 'یکشنبه', 'دوشنبه', 'سه‌شنبه', 'چهارشنبه'],
        'profile_phone': profile.phone or '', 'profile_department': profile.department or '',
        'profile_bio': profile.bio or '', 'profile_picture': profile.profile_picture.url if profile.profile_picture else None,
    }


@login_required(login_url='login_chat')
def teacher_student_attendance(request):
    return render(request, 'teacher/attendance/students.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_health(request):
    return render(request, 'teacher/health/list.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_attendance(request):
    return render(request, 'teacher/attendance/teacher.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_plans(request):
    return render(request, 'teacher/plans/list.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_timetable(request):
    return render(request, 'teacher/timetable/index.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_profile(request):
    return render(request, 'teacher/profile.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_student_add(request):
    if request.method == 'POST':
        try:
            import uuid
            teacher = _linked_teacher_for_user(request.user)
            class_name = request.POST.get('cls', '').strip()
            if not teacher or not Class.objects.filter(teacher=teacher, is_active=True, class_name=class_name).exists():
                raise ValidationError('فقط کلاس‌های فعالِ اختصاص‌یافته به شما قابل انتخاب هستند.')
            student = Student(
                first_name=request.POST.get('fname', '').strip(),
                last_name=request.POST.get('lname', '').strip(),
                father_name=request.POST.get('father', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip().lower(),
                address=request.POST.get('address', '').strip(),
                student_id=f"STU-{uuid.uuid4().hex[:10].upper()}",
                class_field=class_name,
                enrollment_date=timezone.localdate(),
                is_active=request.POST.get('status', 'active') == 'active',
            )
            student.full_clean()
            student.save()
            messages.success(request, '✅ شاگرد اضافه شد')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
        return redirect('teacher_students')
    return render(request, 'teacher/students/add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_student_edit(request, pk):
    teacher, students = _teacher_students_queryset(request.user)
    student = get_object_or_404(students, pk=pk)
    if request.method == 'POST':
        try:
            class_name = request.POST.get('cls', '').strip()
            if not Class.objects.filter(teacher=teacher, is_active=True, class_name=class_name).exists():
                raise ValidationError('کلاس انتخاب‌شده برای شما معتبر نیست.')
            student.first_name = request.POST.get('fname', student.first_name)
            student.last_name = request.POST.get('lname', student.last_name)
            student.father_name = request.POST.get('father', student.father_name)
            student.phone = request.POST.get('phone', student.phone)
            student.class_field = class_name
            student.is_active = request.POST.get('status', 'active') == 'active'
            student.full_clean()
            student.save()
            messages.success(request, '✅ شاگرد ویرایش شد')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
        return redirect('teacher_students')
    context = _teacher_page_context(request)
    context['student'] = student
    return render(request, 'teacher/students/edit.html', context)


@login_required(login_url='login_chat')
def teacher_student_delete(request, pk):
    # Student accounts are administrative records. Teachers may update their
    # assigned students, but only an administrator may delete a student.
    messages.error(request, 'معلم اجازه حذف شاگرد را ندارد.')
    return redirect('teacher_students')


# ════════════════════════════════════════
# TEACHER: Student Presence
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_student_presence_add(request):
    if request.method == 'POST':
        try:
            _, students = _teacher_students_queryset(request.user)
            student = students.filter(pk=request.POST.get('student_id', '')).first()
            if not student:
                raise ValidationError({'student_id': 'شاگرد انتخاب‌شده در کلاس‌های شما نیست.'})
            candidate = StudentPresence(
                student_name=f'{student.first_name} {student.last_name}'.strip(),
                date=request.POST.get('date', '').strip(),
                status=request.POST.get('status', '').strip(),
                note=request.POST.get('note', '').strip(),
            )
            candidate.full_clean()
            if candidate.date > timezone.localdate():
                raise ValidationError({'date': 'ثبت حضور برای تاریخ آینده مجاز نیست.'})

            _, created = StudentPresence.objects.update_or_create(
                student_name=candidate.student_name,
                date=candidate.date,
                defaults={'status': candidate.status, 'note': candidate.note},
            )
            messages.success(request, '✅ حضوری ثبت شد' if created else '✅ حضوری همان روز بروزرسانی شد')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
        return redirect('teacher_student_attendance')
    return render(request, 'teacher/attendance/student_add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_student_presence_delete(request, pk):
    _, students = _teacher_students_queryset(request.user)
    student_names = [f'{student.first_name} {student.last_name}'.strip() for student in students]
    obj = get_object_or_404(StudentPresence.objects.filter(student_name__in=student_names), pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ حذف شد')
    return redirect('teacher_dashboard')


# ════════════════════════════════════════
# TEACHER: Student Health
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_health_add(request):
    if request.method == 'POST':
        try:
            # تبدیل قد و وزن از متن به عدد
            def to_float(val):
                if not val: return None
                try: return float(str(val).replace(',','.').strip())
                except: return None
            
            student_id = request.POST.get('student_id', '')
            student_name = request.POST.get('name','')
            _, students = _teacher_students_queryset(request.user)
            st = students.filter(pk=student_id).first()
            if not st:
                raise ValidationError('شاگرد انتخاب‌شده در کلاس‌های شما نیست.')
            student_name = f"{st.first_name} {st.last_name}".strip()
            
            try:
                StudentHealthReport.objects.create(
                    student_name=student_name,
                    student_id_fk=int(student_id) if student_id else None,
                    date=request.POST.get('date', datetime.today().date()),
                    height=to_float(request.POST.get('height')),
                    weight=to_float(request.POST.get('weight')),
                    health_status=request.POST.get('status','good'),
                    diagnosis=request.POST.get('diagnosis',''),
                )
            except Exception:
                # Fallback without FK
                StudentHealthReport.objects.create(
                    student_name=student_name,
                    date=request.POST.get('date', datetime.today().date()),
                    height=to_float(request.POST.get('height')),
                    weight=to_float(request.POST.get('weight')),
                    health_status=request.POST.get('status','good'),
                    diagnosis=request.POST.get('diagnosis',''),
                )
            messages.success(request, '✅ گزارش صحی ثبت شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
        return redirect('teacher_health')
    return render(request, 'teacher/health/add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_health_delete(request, pk):
    obj = get_object_or_404(StudentHealthReport, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ حذف شد')
    return redirect('teacher_dashboard')


# ════════════════════════════════════════
# TEACHER: Teacher Presence
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_presence_add(request):
    if request.method == 'POST':
        try:
            teacher = _linked_teacher_for_user(request.user)
            if not teacher:
                raise ValidationError('حساب شما به پروفایل معلم وصل نشده است.')

            record = TeacherPresence(
                teacher=teacher,
                date=request.POST.get('date', '').strip(),
                status=request.POST.get('status', 'present').strip(),
                check_in_time=request.POST.get('in_time') or None,
                check_out_time=request.POST.get('out_time') or None,
                note=request.POST.get('note', '').strip(),
            )
            record.full_clean()
            if record.date > timezone.localdate():
                raise ValidationError('ثبت حضوری برای تاریخ آینده مجاز نیست.')
            if record.check_in_time and record.check_out_time and record.check_out_time <= record.check_in_time:
                raise ValidationError('وقت خروج باید بعد از وقت ورود باشد.')

            # Update the day’s existing record rather than creating a duplicate.
            existing = TeacherPresence.objects.filter(teacher=teacher, date=record.date).order_by('id').first()
            if existing:
                existing.status = record.status
                existing.check_in_time = record.check_in_time
                existing.check_out_time = record.check_out_time
                existing.note = record.note
                existing.save(update_fields=['status', 'check_in_time', 'check_out_time', 'note'])
                messages.success(request, '✅ حضوری همان روز بروزرسانی شد')
            else:
                record.save()
                messages.success(request, '✅ حضوری ثبت شد')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
        return redirect('teacher_attendance')
    return render(request, 'teacher/attendance/teacher_add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_presence_delete(request, pk):
    teacher = _linked_teacher_for_user(request.user)
    obj = get_object_or_404(TeacherPresence.objects.filter(teacher=teacher), pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ حذف شد')
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=tp')


# ════════════════════════════════════════
# TEACHER: Plans
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_plan_add(request):
    if request.method == 'POST':
        try:
            teacher = Teacher.objects.filter(user=request.user).first()
            if not teacher and request.user.email:
                try:
                    t2 = Teacher.objects.get(email=request.user.email)
                    t2.user = request.user; t2.save(); teacher = t2
                except Exception: pass
            if not teacher and request.user.first_name:
                try:
                    qs = Teacher.objects.filter(first_name__iexact=request.user.first_name.strip())
                    if qs.count() == 1:
                        teacher = qs.first(); teacher.user = request.user; teacher.save()
                except Exception: pass
            TeacherPlan.objects.create(
                teacher=teacher,
                subject=request.POST.get('subject',''),
                topic=request.POST.get('topic',''),
                goal=request.POST.get('goal',''),
                material=request.POST.get('material',''),
                activities=request.POST.get('activities',''),
                evaluation=request.POST.get('evaluation',''),
                class_name=request.POST.get('cls',''),
                date=request.POST.get('date', datetime.today().date()),
            )
            messages.success(request, '✅ پلان ذخیره شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
        return redirect('teacher_plans')
    return render(request, 'teacher/plans/add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_plan_delete(request, pk):
    obj = get_object_or_404(TeacherPlan, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ پلان حذف شد')
    return redirect('teacher_dashboard')



# ════════════════════════════════════════
# TEACHER: Timetable
# ════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_timetable_add(request):
    if request.method == 'POST':
        try:
            # ── چند روش برای پیدا کردن Teacher ──
            teacher = Teacher.objects.filter(user=request.user).first()
            if not teacher and request.user.email:
                try:
                    teacher = Teacher.objects.get(email=request.user.email)
                    teacher.user = request.user; teacher.save()
                except Exception: pass
            if not teacher and request.user.first_name:
                try:
                    qs = Teacher.objects.filter(first_name__iexact=request.user.first_name.strip())
                    if qs.count() == 1:
                        teacher = qs.first()
                        teacher.user = request.user; teacher.save()
                except Exception: pass
            day       = request.POST.get('day', '')
            time_slot = request.POST.get('time', '')
            subject   = request.POST.get('subject', '').strip()
            note      = request.POST.get('note', '').strip()
            if not subject:
                messages.error(request, '❌ نام درس را وارد کنید')
            else:
                # update_or_create handles UNIQUE constraint gracefully
                obj, created = TeacherTimetable.objects.update_or_create(
                    teacher=teacher,
                    day=day,
                    time_slot=time_slot,
                    defaults={'subject': subject, 'note': note}
                )
                if created:
                    messages.success(request, f'✅ درس "{subject}" اضافه شد')
                else:
                    messages.success(request, f'✅ درس "{subject}" بروزرسانی شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
        return redirect('teacher_timetable')
    return render(request, 'teacher/timetable/add.html', _teacher_page_context(request))


@login_required(login_url='login_chat')
def teacher_timetable_delete(request, pk):
    obj = get_object_or_404(TeacherTimetable, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ درس از جدول حذف شد')
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=timetable')


# ════════════════════════════════════════
# TEACHER: Profile
# ════════════════════════════════════════


@login_required(login_url='login_chat')
def teacher_plan_edit(request, pk):
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    obj = get_object_or_404(TeacherPlan, pk=pk)
    if request.method == 'POST':
        s = request.POST.get('subject', '').strip()
        if s: obj.subject = s
        obj.topic      = request.POST.get('topic', obj.topic or '')
        obj.class_name = request.POST.get('class_name', obj.class_name or '')
        d = request.POST.get('date', '')
        if d:
            for fmt in ('%Y-%m-%d','%m/%d/%Y','%d/%m/%Y'):
                try:
                    from datetime import datetime as _dt
                    obj.date = _dt.strptime(d, fmt).date(); break
                except: pass
        obj.save()
        messages.success(request, '✅ پلان بروزرسانی شد')
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=plans')


@login_required(login_url='login_chat')
def teacher_presence_edit(request, pk):
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    obj = get_object_or_404(TeacherPresence, pk=pk)
    if request.method == 'POST':
        d = request.POST.get('date', '')
        if d:
            for fmt in ('%Y-%m-%d','%m/%d/%Y','%d/%m/%Y'):
                try:
                    from datetime import datetime as _dt
                    obj.date = _dt.strptime(d, fmt).date(); break
                except: pass
        obj.status         = request.POST.get('status', obj.status)
        obj.check_in_time  = request.POST.get('check_in_time') or None
        obj.check_out_time = request.POST.get('check_out_time') or None
        obj.note           = request.POST.get('note', obj.note or '')
        obj.save()
        messages.success(request, '✅ حضور بروزرسانی شد')
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=tp')


@login_required(login_url='login_chat')
def teacher_timetable_edit(request, pk):
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    obj = get_object_or_404(TeacherTimetable, pk=pk)
    if request.method == 'POST':
        s = request.POST.get('subject', '').strip()
        if s: obj.subject = s
        obj.note = request.POST.get('note', obj.note or '')
        obj.save()
        messages.success(request, '✅ جدول وقت بروزرسانی شد')
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=timetable')


@login_required(login_url='login_chat')
def teacher_profile_update(request):
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        user = request.user
        if form_type == 'info':
            try:
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.email = request.POST.get('email', user.email)
                user.save()
                try:
                    from .models import UserProfile
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.phone = request.POST.get('phone', '')
                    profile.department = request.POST.get('department', '')
                    profile.bio = request.POST.get('bio', '')
                    profile.save()
                except Exception:
                    pass
                messages.success(request, '✅ معلومات ذخیره شد')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
        elif form_type == 'password':
            from django.contrib.auth import update_session_auth_hash
            current = request.POST.get('current_password','')
            new_pw = request.POST.get('new_password','')
            confirm = request.POST.get('confirm_password','')
            if not user.check_password(current):
                messages.error(request, '❌ پسورد فعلی اشتباه است')
            elif new_pw != confirm:
                messages.error(request, '❌ پسورد جدید مطابقت ندارد')
            elif len(new_pw) < 8:
                messages.error(request, '❌ پسورد باید حداقل 8 کاراکتر باشد')
            else:
                user.set_password(new_pw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, '✅ پسورد تغییر کرد')
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_profile_picture(request):
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, '✅ عکس پروفایل تغییر کرد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('teacher_dashboard')

#  
# سایر Dashboards
#  

@login_required(login_url='login_chat')
def student_dashboard(request, template_name='student/dashboard.html'):
    """داشبورد شاگرد - وصل کامل به دیتابیس مشترک"""

    def safe(fn, default=0):
        try: return fn()
        except Exception: return default

    def safe_qs(fn):
        try: return fn()
        except Exception: return []

    # ══════════════════════════════════════════════
    # پیدا کردن Student record - جستجوی چند مرحله‌ای
    # ══════════════════════════════════════════════
    student = None

    # روش 1: از طریق user FK (دقیق‌ترین)
    try:
        student = Student.objects.get(user=request.user)
    except Student.DoesNotExist:
        pass

    # روش 2: از طریق ایمیل
    if not student and request.user.email:
        try:
            student = Student.objects.get(email=request.user.email)
            # لینک کردن برای دفعه بعد
            student.user = request.user
            student.save()
        except (Student.DoesNotExist, Student.MultipleObjectsReturned):
            pass

    # روش 3: از طریق نام کاربر
    if not student:
        try:
            fn = request.user.first_name.strip()
            ln = request.user.last_name.strip()
            if fn and ln:
                student = Student.objects.get(first_name__iexact=fn, last_name__iexact=ln)
                student.user = request.user
                student.save()
            elif fn:
                qs = Student.objects.filter(first_name__iexact=fn)
                if qs.count() == 1:
                    student = qs.first()
                    student.user = request.user
                    student.save()
        except (Student.DoesNotExist, Student.MultipleObjectsReturned):
            pass

    # روش 4: از طریق username
    if not student:
        try:
            uname = request.user.username.strip()
            qs = Student.objects.filter(first_name__iexact=uname)
            if qs.count() == 1:
                student = qs.first()
                student.user = request.user
                student.save()
        except Exception:
            pass

    username = request.user.first_name or request.user.username

    # ══════════════════════════════════════════════
    # ✅ جستجوی هوشمند حضوری و صحی
    # روش 1: از طریق student_id_fk (دقیق‌ترین)
    # روش 2: از طریق نام (fallback)
    # ══════════════════════════════════════════════
    from django.db.models import Q

    # ساختن همه نام‌های ممکن
    search_names = set()
    if student:
        if student.first_name:
            search_names.add(student.first_name.strip())
        if student.last_name:
            search_names.add(student.last_name.strip())
        full = f"{student.first_name} {student.last_name}".strip()
        if full:
            search_names.add(full)
    u = request.user
    if u.first_name:
        search_names.add(u.first_name.strip())
        full2 = f"{u.first_name} {u.last_name}".strip()
        if full2:
            search_names.add(full2)
    search_names.discard('')
    search_names.discard(' ')

    # ساختن name filter
    # Attendance and health records currently store a name rather than a student FK.
    # Exact matching prevents records belonging to another student with the same first name leaking here.
    name_filter = Q(pk__in=[])
    if student:
        full_name = f'{student.first_name} {student.last_name}'.strip()
        if full_name:
            name_filter = Q(student_name__iexact=full_name)

    def get_presence():
        qs = None
        # روش 1: FK مستقیم
        if student:
            try:
                qs = StudentPresence.objects.filter(student_id_fk=student.id)
                if qs.exists():
                    return qs.order_by('-date')
            except Exception:
                pass
        # روش 2: جستجو بر اساس نام
        if name_filter:
            try:
                qs = StudentPresence.objects.filter(name_filter)
                return qs.order_by('-date')
            except Exception:
                pass
        return StudentPresence.objects.none()

    def get_health():
        # روش 1: FK مستقیم
        if student:
            try:
                qs = StudentHealthReport.objects.filter(student_id_fk=student.id)
                if qs.exists():
                    return qs.order_by('-date')
            except Exception:
                pass
        # روش 2: نام
        if name_filter:
            try:
                return StudentHealthReport.objects.filter(name_filter).order_by('-date')
            except Exception:
                pass
        return StudentHealthReport.objects.none()

    try:
        sp_qs = get_presence()
        present_count = sp_qs.filter(status='present').count()
        absent_count  = sp_qs.filter(status='absent').count()
        leave_count   = sp_qs.filter(status='leave').count()
        my_presence   = sp_qs
    except Exception:
        present_count = absent_count = leave_count = 0
        my_presence = []

    total_presence = present_count + absent_count + leave_count
    presence_rate  = round(present_count / total_presence * 100) if total_presence else 0

    try:
        my_health = get_health()
    except Exception:
        my_health = []

    # ══════════════════════════════════════════════
    # فیس - از StudentPayment (FK به Student)
    # ══════════════════════════════════════════════
    if student:
        paid_fees    = safe(lambda: StudentPayment.objects.filter(student=student, status='completed').count())
        pending_fees = safe(lambda: StudentPayment.objects.filter(student=student, status='pending').count())
        overdue_fees = safe(lambda: StudentPayment.objects.filter(student=student, status='overdue').count())
        my_payments  = safe_qs(lambda: StudentPayment.objects.filter(student=student).order_by('-year','-month'))
    else:
        paid_fees = pending_fees = overdue_fees = 0
        my_payments = []

    # ══════════════════════════════════════════════
    # جدول وقت - از کلاس شاگرد
    # ══════════════════════════════════════════════
    class_record = Class.objects.filter(class_name=student.class_field, is_active=True).select_related('teacher').first() if student else None
    timetable = safe_qs(
        lambda: TeacherTimetable.objects.filter(teacher=class_record.teacher).order_by('day', 'time_slot')
        if class_record and class_record.teacher else TeacherTimetable.objects.none()
    )

    # ══════════════════════════════════════════════
    # پروفایل
    # ══════════════════════════════════════════════
    try:
        from .models import UserProfile
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_phone   = profile_obj.phone or ''
        profile_picture = profile_obj.profile_picture.url if profile_obj.profile_picture else None
    except Exception:
        profile_phone   = ''
        profile_picture = None

    context = {
        'username':       username,
        'student':        student,
        'today':          str(datetime.today().date()),
        'present_count':  present_count,
        'absent_count':   absent_count,
        'leave_count':    leave_count,
        'presence_rate':  presence_rate,
        # aliased for template compatibility
        'sp_present':     present_count,
        'sp_absent':      absent_count,
        'sp_leave':       leave_count,
        'total_students':  safe(lambda: Student.objects.filter(is_active=True).count()),
        'active_students': safe(lambda: Student.objects.filter(is_active=True).count()),
        'present_today':   present_count,
        'absent_today':    absent_count,
        'total_plans':     safe(lambda: TeacherPlan.objects.count()),
        'h_excellent':     safe(lambda: StudentHealthReport.objects.filter(health_status='excellent').count()),
        'h_good':          safe(lambda: StudentHealthReport.objects.filter(health_status='good').count()),
        'h_care':          safe(lambda: StudentHealthReport.objects.filter(health_status='needs_care').count()),
        # general stats
        'total_students':  safe(lambda: Student.objects.filter(is_active=True).count()),
        'active_students': safe(lambda: Student.objects.filter(is_active=True).count()),
        'present_today':   present_count,
        'absent_today':    absent_count,
        'total_plans':     safe(lambda: TeacherPlan.objects.count()),
        'h_excellent':     safe(lambda: StudentHealthReport.objects.filter(health_status='excellent').count()),
        'h_good':          safe(lambda: StudentHealthReport.objects.filter(health_status='good').count()),
        'h_care':          safe(lambda: StudentHealthReport.objects.filter(health_status='needs_care').count()),
        'paid_fees':      paid_fees,
        'pending_fees':   pending_fees,
        'overdue_fees':   overdue_fees,
        'my_presence':    my_presence,
        'my_payments':    my_payments,
        'my_health':      my_health,
        'timetable':      timetable,
        'time_slots':     ['7:30 - 8:15','8:15 - 9:00','9:15 - 10:00','10:00 - 10:45','11:00 - 11:45','11:45 - 12:30'],
        'days_list':      ['شنبه','یکشنبه','دوشنبه','سه‌شنبه','چهارشنبه'],
        'profile_phone':  profile_phone,
        'profile_picture':profile_picture,
    }
    return render(request, template_name, context)


@login_required(login_url='login_chat')
def student_info(request):
    return student_dashboard(request, 'student/info.html')


@login_required(login_url='login_chat')
def student_attendance(request):
    return student_dashboard(request, 'student/attendance.html')


@login_required(login_url='login_chat')
def student_fees(request):
    return student_dashboard(request, 'student/fees.html')


@login_required(login_url='login_chat')
def student_timetable(request):
    return student_dashboard(request, 'student/timetable.html')


@login_required(login_url='login_chat')
def student_health(request):
    return student_dashboard(request, 'student/health.html')


@login_required(login_url='login_chat')
def student_profile(request):
    return student_dashboard(request, 'student/profile.html')


@login_required(login_url='login_chat')
def student_profile_update(request):
    """آپدیت پروفایل شاگرد"""
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        user = request.user
        if form_type == 'info':
            try:
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name  = request.POST.get('last_name', user.last_name)
                user.email      = request.POST.get('email', user.email)
                user.save()
                try:
                    from .models import UserProfile
                    profile, _ = UserProfile.objects.get_or_create(user=user)
                    profile.phone = request.POST.get('phone', '')
                    profile.save()
                except Exception:
                    pass
                messages.success(request, '✅ معلومات ذخیره شد')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
        elif form_type == 'password':
            from django.contrib.auth import update_session_auth_hash
            cur = request.POST.get('current_password','')
            nw  = request.POST.get('new_password','')
            cf  = request.POST.get('confirm_password','')
            if not user.check_password(cur):
                messages.error(request, '❌ پسورد فعلی اشتباه است')
            elif nw != cf:
                messages.error(request, '❌ پسورد جدید مطابقت ندارد')
            elif len(nw) < 8:
                messages.error(request, '❌ پسورد باید حداقل 8 کاراکتر باشد')
            else:
                user.set_password(nw)
                user.save()
                update_session_auth_hash(request, user)
                messages.success(request, '✅ پسورد تغییر کرد')
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return redirect('student_profile')


@login_required(login_url='login_chat')
def student_profile_picture(request):
    """آپلود عکس پروفایل شاگرد"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            from .models import UserProfile
            profile, _ = UserProfile.objects.get_or_create(user=request.user)
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, '✅ عکس پروفایل تغییر کرد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return redirect('student_profile')

#  
# doctor DASHBOARD -داشبورد داکتر
# 
#  

@login_required(login_url='login_chat')
@login_required(login_url='login_chat')
def doctor_dashboard(request, template_name='doctor/dashboard.html', record=None):
    """داشبورد دکتر - کامل"""
    from django.db.models import Count
    from datetime import date
    from django.http import HttpResponseRedirect
    from django.urls import reverse

    if request.method == 'POST':
        action = request.POST.get('action', '')

        # ── تابع تبدیل تاریخ
        def parse_date(d):
            """تاریخ را از هر فرمتی به date تبدیل می‌کند"""
            if not d:
                return date.today()
            from datetime import datetime
            for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d'):
                try:
                    return datetime.strptime(d.strip(), fmt).date()
                except:
                    pass
            return date.today()

        # ── Add Health Report
        if action == 'add_report':
            try:
                student_id = request.POST.get('student')
                if not student_id:
                    messages.error(request, '❌ لطفاً یک شاگرد انتخاب کنید')
                    return redirect('doctor_health_add')
                student = Student.objects.get(id=student_id)
                r, _ = Medical.objects.get_or_create(student=student)
                r.checkup_date    = parse_date(request.POST.get('checkup_date'))
                r.height          = request.POST.get('height') or None
                r.weight          = request.POST.get('weight') or None
                r.blood_pressure  = request.POST.get('blood_pressure', '')
                r.temperature     = request.POST.get('temperature') or None
                r.health_status   = request.POST.get('health_status', 'normal')
                r.diagnosis       = request.POST.get('diagnosis', '')
                r.recommendations = request.POST.get('recommendations', '')
                r.save()
                messages.success(request, '✅ گزارش صحی با موفقیت ذخیره شد')
                return redirect('doctor_health_list')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
                return redirect('doctor_health_add')

        # ── Edit Health Report
        elif action == 'edit_report':
            try:
                record_id = request.POST.get('record_id')
                r = Medical.objects.get(id=record_id)
                r.student         = Student.objects.get(id=request.POST.get('student'))
                r.checkup_date    = parse_date(request.POST.get('checkup_date'))
                r.height          = request.POST.get('height') or None
                r.weight          = request.POST.get('weight') or None
                r.blood_pressure  = request.POST.get('blood_pressure', '')
                r.temperature     = request.POST.get('temperature') or None
                r.health_status   = request.POST.get('health_status', 'normal')
                r.diagnosis       = request.POST.get('diagnosis', '')
                r.recommendations = request.POST.get('recommendations', '')
                r.save()
                messages.success(request, '✅ گزارش با موفقیت بروزرسانی شد')
                return redirect('doctor_health_list')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
                return redirect('doctor_health_add')

        # ── Add Presence
        elif action == 'add_presence':
            try:
                pdate  = request.POST.get('date') or str(date.today())
                status = request.POST.get('status', 'present')
                note   = request.POST.get('note', '')
                DoctorPresence.objects.create(
                    doctor=request.user,
                    date=pdate,
                    status=status,
                    note=note
                )
                messages.success(request, '✅ حضور با موفقیت ثبت شد')
            except Exception as e:
                messages.error(request, f'❌ خطا ثبت حضور: {str(e)}')
            return redirect('doctor_attendance')

        return HttpResponseRedirect(reverse('doctor_dashboard'))

    # ── GET
    all_records    = Medical.objects.select_related('student').order_by('-checkup_date')
    recent_records = all_records[:10]

    presence_list = []
    try:
        presence_list = list(DoctorPresence.objects.filter(doctor=request.user).order_by('-date'))
    except Exception:
        presence_list = []

    today = date.today()
    context = {
        'all_records':    all_records,
        'recent_records': recent_records,
        'presence_list':  presence_list,
        'students':       Student.objects.all().order_by('first_name'),
        'total_students': Student.objects.count(),
        'total_examined': Medical.objects.count(),
        'needs_care':     Medical.objects.filter(health_status='needs_care').count(),
        'total_records':  Medical.objects.filter(checkup_date=today).count(),
        'present_days':   len([p for p in presence_list if p.status == 'present']),
        'absent_days':    len([p for p in presence_list if p.status == 'absent']),
    }
    context.update(_get_profile_context(request.user))
    if record:
        context['record'] = record
    return render(request, template_name, context)


@login_required(login_url='login_chat')
def doctor_health_list(request):
    return doctor_dashboard(request, 'doctor/health/list.html')


@login_required(login_url='login_chat')
def doctor_health_add(request):
    return doctor_dashboard(request, 'doctor/health/form.html')


@login_required(login_url='login_chat')
def doctor_health_edit(request, pk):
    return doctor_dashboard(request, 'doctor/health/form.html', get_object_or_404(Medical, pk=pk))


@login_required(login_url='login_chat')
def doctor_attendance(request):
    return doctor_dashboard(request, 'doctor/attendance/list.html')


@login_required(login_url='login_chat')
def doctor_attendance_add(request):
    return doctor_dashboard(request, 'doctor/attendance/add.html')


@login_required(login_url='login_chat')
def doctor_profile(request):
    return doctor_dashboard(request, 'doctor/profile.html')


@login_required(login_url='login_chat')
def doctor_record_delete(request, pk):
    """حذف رکورد صحی"""
    try:
        Medical.objects.filter(id=pk).delete()
        messages.success(request, '✅ رکورد حذف شد')
    except Exception as e:
        messages.error(request, f'❌ {str(e)}')
    return redirect('doctor_health_list')

@login_required(login_url='login_chat')
def doctor_presence_delete(request, pk):
    """حذف رکورد حضور داکتر"""
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    try:
        presence = DoctorPresence.objects.get(pk=pk, doctor=request.user)
        presence.delete()
        messages.success(request, '✅ رکورد حضور حذف شد')
    except DoctorPresence.DoesNotExist:
        messages.error(request, '❌ رکورد یافت نشد')
    except Exception as e:
        messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('doctor_attendance')


@login_required(login_url='login_chat')
def doctor_profile_update(request):
    """بروزرسانی پروفایل داکتر"""
    if request.method == 'POST':
        u = request.user
        if request.POST.get('change_password'):
            np = request.POST.get('new_password')
            cp = request.POST.get('confirm_password')
            if np and np == cp:
                u.set_password(np)
                u.save()
                messages.success(request, '✅ رمز عبور تغییر یافت')
            else:
                messages.error(request, '❌ رمزهای عبور مطابقت ندارند')
        else:
            u.first_name = request.POST.get('first_name', u.first_name)
            u.last_name  = request.POST.get('last_name', u.last_name)
            u.email      = request.POST.get('email', u.email)
            u.save()
            profile_obj, _ = UserProfile.objects.get_or_create(user=u)
            profile_obj.phone = request.POST.get('phone', '')
            profile_obj.bio   = request.POST.get('bio', '')
            profile_obj.save()
            messages.success(request, '✅ پروفایل بروزرسانی شد')
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return redirect('doctor_profile')


@login_required(login_url='login_chat')
def doctor_profile_picture(request):
    """آپلود عکس پروفایل داکتر"""
    if request.method == 'POST' and request.FILES.get('picture'):
        profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
        profile_obj.profile_picture = request.FILES['picture']
        profile_obj.save()
        messages.success(request, '✅ عکس پروفایل بروزرسانی شد')
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return redirect('doctor_profile')

#  
# 💰 FINANCE DASHBOARD - داشبورد مالی
# 
#  

def _finance_page_context(request):
    """Shared data for every page in the split finance dashboard."""
    total_income  = Transaction.objects.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = Transaction.objects.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance   = total_income - total_expense

    # ترانسکشن‌ها
    all_transactions   = Transaction.objects.all().order_by('-transaction_date')
    recent_transactions = all_transactions[:8]
    total_transactions = all_transactions.count()

    # فیس شاگردان
    all_payments  = StudentPayment.objects.all().order_by('-year', '-month')
    paid_count    = StudentPayment.objects.filter(status='completed').count()
    pending_count = StudentPayment.objects.filter(status='pending').count()
    overdue_count = StudentPayment.objects.filter(status='overdue').count()

    # آمار کلی سیستم (از همان دیتابیس مشترک)
    total_students  = Student.objects.count()
    total_teachers  = Teacher.objects.count()
    total_employees = Employee.objects.count()
    try:
        from .models import Class
        total_classes = Class.objects.count()
    except Exception:
        total_classes = 0

    # لیست شاگردان برای فرم‌ها
    all_students = Student.objects.all().order_by('first_name')

    context = {
        'total_income':        total_income,
        'total_expense':       total_expense,
        'net_balance':         net_balance,
        'all_transactions':    all_transactions,
        'recent_transactions': recent_transactions,
        'total_transactions':  total_transactions,
        'all_payments':        all_payments,
        'paid_count':          paid_count,
        'pending_count':       pending_count,
        'overdue_count':       overdue_count,
        'total_students':      total_students,
        'total_teachers':      total_teachers,
        'total_employees':     total_employees,
        'total_classes':       total_classes,
        'all_students':        all_students,
    }
    context.update(_get_profile_context(request.user))
    context['username'] = context.get('username') or request.user.first_name or request.user.username
    return context


@login_required(login_url='login_chat')
def finance_dashboard(request):
    return render(request, 'finance/dashboard.html', _finance_page_context(request))


@login_required(login_url='login_chat')
def finance_transactions(request):
    return render(request, 'finance/transactions/list.html', _finance_page_context(request))


@login_required(login_url='login_chat')
def finance_payments(request):
    return render(request, 'finance/payments/list.html', _finance_page_context(request))


@login_required(login_url='login_chat')
def finance_reports(request):
    return render(request, 'finance/reports/index.html', _finance_report_context(request))


def _finance_report_context(request):
    """Return one calendar-month financial report and its filter choices."""
    today = timezone.localdate()
    try:
        month = int(request.GET.get('month', today.month))
        year = int(request.GET.get('year', today.year))
    except (TypeError, ValueError):
        month, year = today.month, today.year
    if month not in range(1, 13) or year < 2000 or year > today.year + 1:
        month, year = today.month, today.year

    transactions = Transaction.objects.filter(
        transaction_date__year=year,
        transaction_date__month=month,
    ).select_related('student').order_by('-transaction_date', '-id')
    completed = transactions.filter(status='completed')
    total_income = completed.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = completed.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0

    context = _finance_page_context(request)
    context.update({
        'all_transactions': transactions,
        'recent_transactions': transactions[:8],
        'total_transactions': transactions.count(),
        'total_income': total_income,
        'total_expense': total_expense,
        'net_balance': total_income - total_expense,
        'selected_month': month,
        'selected_year': year,
        'report_month_name': _REPORT_MONTHS_FA[month - 1],
        'report_months': list(enumerate(_REPORT_MONTHS_FA, 1)),
        'report_years': list(range(today.year + 1, max(2019, today.year - 5), -1)),
    })
    return context


def _pdf_escape(value):
    return str(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _finance_pdf_document(context):
    """Build a clean, portable PDF without requiring a server-side binary."""
    transactions = list(context['all_transactions'])
    rows_per_page = 24
    row_sets = [transactions[index:index + rows_per_page] for index in range(0, len(transactions), rows_per_page)] or [[]]
    page_objects = []
    content_objects = []

    for page_number, rows in enumerate(row_sets, 1):
        commands = [
            '0.05 0.12 0.25 rg 0 780 595 62 re f',
            'BT /F2 21 Tf 42 815 Td (GAAM KINDERGARTEN) Tj ET',
            'BT /F1 11 Tf 42 796 Td (Monthly Financial Report) Tj ET',
            '0.10 0.25 0.48 rg 42 750 511 1 re f',
            f'BT /F2 12 Tf 42 731 Td (Period: {_pdf_escape(context["report_month_name"])} {context["selected_year"]}) Tj ET',
            f'BT /F1 10 Tf 320 731 Td (Generated: {timezone.localdate().isoformat()}) Tj ET',
            f'BT /F2 11 Tf 42 704 Td (Income: AFN {context["total_income"]}) Tj ET',
            f'BT /F2 11 Tf 215 704 Td (Expense: AFN {context["total_expense"]}) Tj ET',
            f'BT /F2 11 Tf 397 704 Td (Net: AFN {context["net_balance"]}) Tj ET',
            '0.10 0.25 0.48 rg 42 675 511 20 re f',
            '1 1 1 rg BT /F2 9 Tf 48 682 Td (DATE) Tj 110 0 Td (TYPE) Tj 95 0 Td (CATEGORY) Tj 150 0 Td (STATUS) Tj 92 0 Td (AMOUNT) Tj ET',
        ]
        y = 657
        for index, item in enumerate(rows):
            if index % 2 == 0:
                commands.append(f'0.96 0.97 0.99 rg 42 {y - 5} 511 18 re f')
            amount = f'AFN {item.amount}'
            category = _pdf_escape((item.category or '-')[:25])
            commands.append(f'0.10 0.12 0.17 rg BT /F1 8 Tf 48 {y} Td ({item.transaction_date}) Tj 110 0 Td ({item.transaction_type.upper()}) Tj 95 0 Td ({category}) Tj 150 0 Td ({item.status.upper()}) Tj 92 0 Td ({amount}) Tj ET')
            y -= 21
        commands.extend([
            '0.85 0.88 0.93 rg 42 55 511 1 re f',
            f'0.25 0.30 0.38 rg BT /F1 8 Tf 42 38 Td (GAAM Finance | Confidential) Tj 400 0 Td (Page {page_number} of {len(row_sets)}) Tj ET',
        ])
        content = '\n'.join(commands).encode('latin-1', 'replace')
        content_objects.append(f'<< /Length {len(content)} >>\nstream\n'.encode() + content + b'\nendstream')

    object_count = 4 + len(row_sets) * 2
    page_ids = [5 + index * 2 for index in range(len(row_sets))]
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        ('<< /Type /Pages /Kids [' + ' '.join(f'{item} 0 R' for item in page_ids) + f'] /Count {len(page_ids)} >>').encode(),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>',
    ]
    for index, content in enumerate(content_objects):
        page_id = page_ids[index]
        content_id = page_id + 1
        objects.append((f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {content_id} 0 R >>').encode())
        objects.append(content)

    output = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f'{number} 0 obj\n'.encode())
        output.extend(obj)
        output.extend(b'\nendobj\n')
    xref = len(output)
    output.extend(f'xref\n0 {object_count + 1}\n0000000000 65535 f \n'.encode())
    output.extend(b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:]))
    output.extend(f'trailer\n<< /Size {object_count + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode())
    return bytes(output)


@login_required(login_url='login_chat')
def finance_report_pdf(request):
    context = _finance_report_context(request)
    filename = f"gaam-finance-{context['selected_year']}-{context['selected_month']:02d}.pdf"
    response = HttpResponse(_finance_pdf_document(context), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required(login_url='login_chat')
def finance_stats(request):
    return render(request, 'finance/reports/stats.html', _finance_page_context(request))


@login_required(login_url='login_chat')
def finance_profile(request):
    return render(request, 'finance/profile.html', _finance_page_context(request))


#  
# 💰 PAYMENT ADD - ثبت فیس جدید
#  

@login_required(login_url='login_chat')
def _legacy_finance_payment_add(request):
    """ثبت فیس جدید برای شاگرد"""
    if request.method == 'POST':
        try:
            student_id   = request.POST.get('student_id')
            total_amount = request.POST.get('total_amount')
            paid_amount  = request.POST.get('paid_amount') or '0'
            payment_type = request.POST.get('payment_type')
            month        = request.POST.get('month')
            year         = request.POST.get('year')
            status       = request.POST.get('status', 'pending')

            student = Student.objects.get(pk=student_id)
            payment = StudentPayment.objects.create(
                student=student,
                total_amount=total_amount,
                paid_amount=paid_amount,
                payment_type=payment_type,
                month=int(month),
                year=int(year),
                status=status,
            )
            messages.success(request, f'✅ فیس {student.first_name} {student.last_name} برای ماه {month}/{year} ثبت شد')
        except StudentPayment.UniqueConstraint:
            messages.error(request, '❌ فیس این ماه برای این شاگرد قبلاً ثبت شده')
        except Exception as e:
            messages.error(request, f'❌ خطا در ثبت فیس: {str(e)}')
    return redirect('finance_dashboard')


#  
# 💰 PAYMENT MARK PAID - علامت‌گذاری پرداخت شده
#  

@login_required(login_url='login_chat')
def _legacy_finance_payment_mark(request, pk):
    """علامت‌گذاری فیس به عنوان پرداخت شده"""
    if request.method == 'POST':
        try:
            payment = StudentPayment.objects.get(pk=pk)
            payment.status = 'completed'
            payment.paid_amount = payment.total_amount
            payment.save()
            messages.success(request, f'✅ فیس {payment.student.first_name} {payment.student.last_name} به عنوان پرداخت شده ثبت شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('finance_dashboard')




#  
# 💰 PAYMENT EDIT - ویرایش فیس
#  

@login_required(login_url='login_chat')
def _legacy_finance_payment_edit(request, pk):
    """ویرایش فیس شاگرد"""
    if request.method == 'POST':
        try:
            payment = get_object_or_404(StudentPayment, pk=pk)
            total_amount = request.POST.get('total_amount', payment.total_amount)
            paid_amount  = request.POST.get('paid_amount') or 0
            payment_type = request.POST.get('payment_type', payment.payment_type)
            month        = request.POST.get('month', payment.month)
            year         = request.POST.get('year', payment.year)
            status       = request.POST.get('status', payment.status)

            payment.total_amount = total_amount
            payment.paid_amount  = paid_amount
            payment.payment_type = payment_type
            payment.month        = int(month)
            payment.year         = int(year)
            payment.status       = status
            payment.save()

            messages.success(request, f'✅ فیس {payment.student.first_name} {payment.student.last_name} بروزرسانی شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('finance_dashboard')

#  
# 💰 PAYMENT DELETE - حذف فیس
#  

@login_required(login_url='login_chat')
def _legacy_finance_payment_delete(request, pk):
    """حذف فیس شاگرد"""
    if request.method == 'POST':
        try:
            payment = get_object_or_404(StudentPayment, pk=pk)
            name = f"{payment.student.first_name} {payment.student.last_name}"
            payment.delete()
            messages.success(request, f'✅ فیس {name} حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('finance_dashboard')


#  
# 💰 FINANCE PROFILE UPDATE - ویرایش پروفایل مسئول مالی
#  

@login_required(login_url='login_chat')
def finance_payment_add(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment = StudentPayment.objects.create(**_payment_payload(request))
                _sync_payment_transaction(payment)
            messages.success(request, 'فیس شاگرد با موفقیت ثبت شد و با سیستم مالی همگام‌سازی شد.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
        except Exception as error:
            messages.error(request, f'خطا: {error}')
        return redirect('finance_payments')
    return render(request, 'finance/payments/add.html', _finance_page_context(request))


@login_required(login_url='login_chat')
def finance_payment_edit(request, pk):
    payment = get_object_or_404(StudentPayment, pk=pk)
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for field, value in _payment_payload(request, payment).items():
                    setattr(payment, field, value)
                payment.save()
                _sync_payment_transaction(payment)
            messages.success(request, 'فیس شاگرد با موفقیت به‌روزرسانی شد.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
    return redirect('finance_payments')


@login_required(login_url='login_chat')
def finance_payment_mark(request, pk):
    payment = get_object_or_404(StudentPayment, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            payment.status = 'completed'
            payment.paid_amount = payment.total_amount
            payment.save(update_fields=['status', 'paid_amount'])
            _sync_payment_transaction(payment)
        messages.success(request, 'فیس شاگردبه  پرداخت‌شده  شد.')
    return redirect('finance_payments')


@login_required(login_url='login_chat')
def finance_payment_delete(request, pk):
    payment = get_object_or_404(StudentPayment, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            if payment.transaction_id:
                payment.transaction.delete()
            payment.delete()
        messages.success(request, 'فیس شاگرد با موفقیت حذف شد.')
    return redirect('finance_payments')


@login_required(login_url='login_chat')
def admin_student_payments(request):
    payments = StudentPayment.objects.select_related('student', 'transaction').order_by('-year', '-month', '-id')
    context = {
        'payments': payments,
        'students': Student.objects.filter(is_active=True).order_by('first_name', 'last_name'),
        'paid_count': payments.filter(status='completed').count(),
        'pending_count': payments.filter(status='pending').count(),
        'overdue_count': payments.filter(status='overdue').count(),
        'current_year': timezone.localdate().year,
        'now': timezone.localdate(),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/student_payments.html', context)


@login_required(login_url='login_chat')
def admin_student_payment_add(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                payment = StudentPayment.objects.create(**_payment_payload(request))
                _sync_payment_transaction(payment)
            messages.success(request, 'فیس شاگرد با موفقیت ثبت شد و با سیستم مالی همگام‌سازی شد.')
        except ValidationError as error:
            messages.error(request, error.messages[0])
        except Exception as error:
            messages.error(request, f'خطا: {error}')
    return redirect('admin_student_payments')


@login_required(login_url='login_chat')
def admin_student_payment_mark(request, pk):
    payment = get_object_or_404(StudentPayment, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            payment.status = 'completed'
            payment.paid_amount = payment.total_amount
            payment.save(update_fields=['status', 'paid_amount'])
            _sync_payment_transaction(payment)
        messages.success(request, 'فیس شاگرد به عنوان پرداخت‌شده علامت‌گذاری شد و با سیستم مالی همگام‌سازی شد.')
    return redirect('admin_student_payments')


@login_required(login_url='login_chat')
def admin_student_payment_delete(request, pk):
    payment = get_object_or_404(StudentPayment, pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            if payment.transaction_id:
                payment.transaction.delete()
            payment.delete()
        messages.success(request, 'فیس شاگرد و معامله مربوط به آن حذف شد.')
    return redirect('admin_student_payments')


@login_required(login_url='login_chat')
def finance_profile_update(request):
    """ویرایش اطلاعات پروفایل مسئول مالی"""
    if request.method == 'POST':
        if request.POST.get('change_password'):
            # تغییر پسورد
            old_password     = request.POST.get('old_password')
            new_password     = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if not request.user.check_password(old_password):
                messages.error(request, '❌ پسورد فعلی اشتباه است')
            elif new_password != confirm_password:
                messages.error(request, '❌ پسورد جدید و تکرار آن یکی نیستند')
            elif len(new_password) < 8:
                messages.error(request, '❌ پسورد باید حداقل ۸ کاراکتر باشد')
            else:
                request.user.set_password(new_password)
                request.user.save()
                messages.success(request, '✅ پسورد با موفقیت تغییر کرد — دوباره وارد شوید')
                from django.contrib.auth import logout
                logout(request)
                return redirect('login_chat')
        else:
            # ویرایش اطلاعات
            request.user.first_name = request.POST.get('first_name', '')
            request.user.last_name  = request.POST.get('last_name', '')
            request.user.email      = request.POST.get('email', '')
            request.user.save()
            messages.success(request, '✅ اطلاعات پروفایل بروزرسانی شد')
    return redirect('finance_profile')


#  
# 💰 FINANCE PROFILE PICTURE - تغییر عکس پروفایل
#  

@login_required(login_url='login_chat')
def finance_profile_picture(request):
    """آپلود عکس پروفایل مسئول مالی"""
    if request.method == 'POST' and request.FILES.get('profile_picture'):
        try:
            from .models import UserProfile
            profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
            profile_obj.profile_picture = request.FILES['profile_picture']
            profile_obj.save()
            messages.success(request, '✅ عکس پروفایل بروزرسانی شد')
        except Exception as e:
            messages.error(request, f'❌ خطا در آپلود عکس: {str(e)}')
    return redirect('finance_profile')
