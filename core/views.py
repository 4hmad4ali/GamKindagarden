#from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from datetime import datetime
from django.db.models import Sum, Count, Q, Avg
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from accounts.roles import assign_role, ROLE_GROUPS
from django.utils import timezone
from .models import StudentPresence, DoctorPresence
from .models import Teacher, Student, Employee, Medical, Class, Transaction, StudentPayment, Attendance, TeacherPlan, TeacherPresence, StudentPresence, StudentHealthReport, TeacherTimetable, UserProfile

# ════════════════════════════════════════════════════════════════
# 🔧 PROFILE CONTEXT HELPER
# ════════════════════════════════════════════════════════════════
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


# ════════════════════════════════════════════════════════════════
# 🏠 HOMEPAGE
# ════════════════════════════════════════════════════════════════

def homepage(request):
    """صفحه اصلی"""
    context = {
        'kindergarten': 'GAAM Kindergarten',
        'phone': '0788919112',
        'address': 'Microrayan 3rd, Kabul'
    }
    return render(request, 'homepage.html', context)

# ════════════════════════════════════════════════════════════════
# 1️⃣ ADMIN DASHBOARD
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 2️⃣ ATTENDANCE
# ════════════════════════════════════════════════════════════════

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
                
                messages.success(request, '✅ حضوری روزانه با موفقیت ثبت شد')
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

# ════════════════════════════════════════════════════════════════
# 3️⃣ TEACHERS
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 4️⃣ STUDENTS
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 5️⃣ FINANCE
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_list(request):
    """
    لیست تمام تراکنش‌های مالی
    - نمایش درآمد، هزینه، درآمد خالص
    - جدول تمام تراکنش‌ها
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
    fields = ('transaction_type', 'amount', 'transaction_date', 'description', 'category', 'status')
    payload = {field: request.POST.get(field, '').strip() for field in fields}

    if any(not payload[field] for field in fields):
        raise ValidationError('لطفاً تمام فیلدهای الزامی تراکنش را تکمیل کنید.')
    if payload['transaction_type'] not in {'income', 'expense'}:
        raise ValidationError({'transaction_type': 'نوع تراکنش معتبر نیست.'})
    if payload['status'] not in {'completed', 'pending'}:
        raise ValidationError({'status': 'وضعیت تراکنش معتبر نیست.'})

    student_id = request.POST.get('student', '').strip()
    if student_id:
        student = Student.objects.filter(pk=student_id, is_active=True).first()
        if not student:
            raise ValidationError({'student': 'شاگرد انتخاب‌شده معتبر یا فعال نیست.'})
        payload['student_id'] = student.pk
    else:
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
    return {field: getattr(candidate, field) for field in (*fields, 'student_id')}


@login_required(login_url='login_chat')
def transaction_add(request):
    """
    افزودن تراکنش جدید - با auto-generate transaction_id
    """
    if request.method == 'POST':
        try:
            import uuid
            from datetime import date as _date

            with transaction.atomic():
                # Use a generated immutable ID, avoiding user-supplied collisions.
                trx_id = f"TRX-{_date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
                Transaction.objects.create(transaction_id=trx_id, **_transaction_payload(request))
            messages.success(request, '✅ تراکنش با موفقیت اضافه شد')
            # redirect back to correct dashboard
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')
            return redirect('finance_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')

    students = Student.objects.filter(is_active=True).order_by('first_name', 'last_name')
    return render(request, 'admin/transaction_form.html', {'students': students})


@login_required(login_url='login_chat')
def transaction_edit(request, pk):
    """
    ویرایش تراکنش
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        try:
            for field, value in _transaction_payload(request, transaction).items():
                setattr(transaction, field, value)
            transaction.save()
            
            messages.success(request, '✅ تراکنش با موفقیت بروزرسانی شد')
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')
            return redirect('finance_list')
        except ValidationError as error:
            messages.error(request, f'خطا: {error.messages[0]}')
    
    students = Student.objects.filter(is_active=True).order_by('first_name', 'last_name')
    return render(request, 'admin/transaction_form.html', {
        'transaction': transaction,
        'students': students,
        'edit_mode': True
    })


@login_required(login_url='login_chat')
def transaction_delete(request, pk):
    """
    حذف تراکنش
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        try:
            transaction.delete()
            messages.success(request, '✅ تراکنش با موفقیت حذف شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return redirect('finance_list')

# ════════════════════════════════════════════════════════════════
# 6️⃣ EMPLOYEES
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 7️⃣ MEDICAL (DOCTOR)
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 8️⃣ REPORTS
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def reports(request):
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
    attendance_summary = Attendance.objects.aggregate(
        total=Count('id'), present=Count('id', filter=Q(status='present')),
        absent=Count('id', filter=Q(status='absent')), leave=Count('id', filter=Q(status='leave')),
    )
    finance_summary = Transaction.objects.filter(status='completed').aggregate(
        income=Sum('amount', filter=Q(transaction_type='income')),
        expenses=Sum('amount', filter=Q(transaction_type='expense')),
        income_count=Count('id', filter=Q(transaction_type='income')),
        expense_count=Count('id', filter=Q(transaction_type='expense')),
    )
    medical_summary = Medical.objects.aggregate(
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
        'report_date': timezone.localdate(),
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/reports.html', context)

# ════════════════════════════════════════════════════════════════
# 9️⃣ CLASSES
# ════════════════════════════════════════════════════════════════

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

# ════════════════════════════════════════════════════════════════
# 🔟 PROFILE
# ════════════════════════════════════════════════════════════════

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


# ════════════════════════════════════════════════════════════════
# teacher_dashboard
# ════════════════════════════════════════════════════════════════

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
    _, students = _teacher_students_queryset(request.user)
    students = students.order_by('-created_at')
    context = {
        'students': students,
        'total': students.count(),
        'active': students.filter(is_active=True).count(),
        'inactive': students.filter(is_active=False).count(),
    }
    return render(request, 'teacher/dashboard.html', context)


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
    return redirect('teacher_dashboard')


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
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_student_delete(request, pk):
    _, students = _teacher_students_queryset(request.user)
    student = get_object_or_404(students, pk=pk)
    if request.method == 'POST':
        student.delete()
        messages.success(request, '✅ شاگرد حذف شد')
    return redirect('teacher_dashboard')


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
    return redirect('teacher_dashboard')


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
            
            student_id = request.POST.get('student_id','')
            student_name = request.POST.get('name','')
            if student_id:
                try:
                    st = Student.objects.get(id=student_id)
                    student_name = f"{st.first_name} {st.last_name}".strip()
                except Student.DoesNotExist:
                    pass
            
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
    return redirect('teacher_dashboard')


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
            TeacherPresence.objects.create(
                teacher=teacher,
                date=request.POST.get('date', datetime.today().date()),
                status=request.POST.get('status','present'),
                check_in_time=request.POST.get('in_time') or None,
                check_out_time=request.POST.get('out_time') or None,
                note=request.POST.get('note',''),
            )
            messages.success(request, '✅ حضوری ثبت شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_presence_delete(request, pk):
    obj = get_object_or_404(TeacherPresence, pk=pk)
    if request.method == 'POST':
        obj.delete()
        messages.success(request, '✅ حذف شد')
    return redirect('teacher_dashboard')


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
    return redirect('teacher_dashboard')


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
    from django.http import HttpResponseRedirect
    from django.urls import reverse
    return HttpResponseRedirect(reverse('teacher_dashboard') + '?page=timetable')


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

# ════════════════════════════════════════════════════════════════
# سایر Dashboards
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def student_dashboard(request):
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
    name_filter = Q()
    for n in search_names:
        if n.strip():
            name_filter |= Q(student_name__icontains=n.strip())

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
    timetable = safe_qs(lambda: TeacherTimetable.objects.all().order_by('day', 'time_slot'))

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
    return render(request, 'student/dashboard.html', context)


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
    return HttpResponseRedirect(reverse('student_dashboard') + '?page=profile')


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
    return HttpResponseRedirect(reverse('student_dashboard') + '?page=profile')

# ════════════════════════════════════════════════════════════════
# doctor DASHBOARD -داشبورد داکتر
# 
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
@login_required(login_url='login_chat')
def doctor_dashboard(request):
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
                    return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=add_report')
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
                return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=health_list')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
                return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=add_report')

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
                return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=health_list')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')
                return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=add_report')

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
            return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=presence')

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
    return render(request, 'doctor_dashboard.html', context)


@login_required(login_url='login_chat')
def doctor_record_delete(request, pk):
    """حذف رکورد صحی"""
    try:
        Medical.objects.filter(id=pk).delete()
        messages.success(request, '✅ رکورد حذف شد')
    except Exception as e:
        messages.error(request, f'❌ {str(e)}')
    return redirect('doctor_dashboard')

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
    return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=presence')


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
    return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=profile')


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
    return HttpResponseRedirect(reverse('doctor_dashboard') + '?section=profile')

# ════════════════════════════════════════════════════════════════
# 💰 FINANCE DASHBOARD - داشبورد مالی
# 
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_dashboard(request):
    """داشبورد مالی کامل"""
    from django.db.models import Sum

    # آمار مالی
    total_income  = Transaction.objects.filter(transaction_type='income').aggregate(Sum('amount'))['amount__sum'] or 0
    total_expense = Transaction.objects.filter(transaction_type='expense').aggregate(Sum('amount'))['amount__sum'] or 0
    net_balance   = total_income - total_expense

    # تراکنش‌ها
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
    return render(request, 'finance_dashboard.html', context)


# ════════════════════════════════════════════════════════════════
# 💰 PAYMENT ADD - ثبت فیس جدید
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_payment_add(request):
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


# ════════════════════════════════════════════════════════════════
# 💰 PAYMENT MARK PAID - علامت‌گذاری پرداخت شده
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_payment_mark(request, pk):
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




# ════════════════════════════════════════════════════════════════
# 💰 PAYMENT EDIT - ویرایش فیس
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_payment_edit(request, pk):
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

# ════════════════════════════════════════════════════════════════
# 💰 PAYMENT DELETE - حذف فیس
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def finance_payment_delete(request, pk):
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


# ════════════════════════════════════════════════════════════════
# 💰 FINANCE PROFILE UPDATE - ویرایش پروفایل مسئول مالی
# ════════════════════════════════════════════════════════════════

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
    return redirect('finance_dashboard')


# ════════════════════════════════════════════════════════════════
# 💰 FINANCE PROFILE PICTURE - تغییر عکس پروفایل
# ════════════════════════════════════════════════════════════════

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
    return redirect('finance_dashboard')
