#from django.shortcuts import render, redirect
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from datetime import datetime
from django.db.models import Sum, Count, Q
from django.db import transaction
from django.contrib.auth.models import User
from accounts.roles import assign_role
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
    context = {'teachers': teachers}
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/teachers.html', context)


@login_required(login_url='login_chat')
def teacher_add(request):
    """
    افزودن معلم جدید
    - ایجاد User و Teacher
    """
    if request.method == 'POST':
        try:
            # ایجاد User جدید
            username = request.POST.get('email').split('@')[0]
            user = User.objects.create_user(
                username=username,
                email=request.POST.get('email'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                password='defaultpass123'
            )
            
            # ایجاد Teacher
            teacher = Teacher.objects.create(
                user=user,
                email=request.POST.get('email'),
                phone=request.POST.get('phone'),
                subject=request.POST.get('subject'),
                employee_id=request.POST.get('employee_id'),
                hire_date=request.POST.get('hire_date')
            )
            assign_role(user, 'teacher')
            
            messages.success(request, f'✅ معلم {user.first_name} با موفقیت اضافه شد')
            return redirect('teachers_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return render(request, 'admin/teacher_form.html')


@login_required(login_url='login_chat')
def teacher_edit(request, pk):
    """
    ویرایش معلم
    """
    teacher = get_object_or_404(Teacher, pk=pk)
    
    if request.method == 'POST':
        try:
            teacher.user.first_name = request.POST.get('first_name')
            teacher.user.last_name = request.POST.get('last_name')
            teacher.user.email = request.POST.get('email')
            teacher.user.save()
            
            teacher.email = request.POST.get('email')
            teacher.phone = request.POST.get('phone')
            teacher.subject = request.POST.get('subject')
            teacher.employee_id = request.POST.get('employee_id')
            teacher.hire_date = request.POST.get('hire_date')
            teacher.save()
            
            messages.success(request, '✅ معلم با موفقیت بروزرسانی شد')
            return redirect('teachers_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
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
            teacher_name = teacher.user.first_name
            user = teacher.user
            teacher.delete()
            user.delete()
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
    students = Student.objects.all().order_by('-id')
    context = {'students': students}
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/students.html', context)


@login_required(login_url='login_chat')
def student_add(request):
    """
    افزودن شاگرد جدید + ساختن User account اتوماتیک
    """
    if request.method == 'POST':
        try:
            fname = request.POST.get('first_name','').strip()
            lname = request.POST.get('last_name','').strip()
            email = request.POST.get('email','').strip()
            
            # ══════════════════════════════════════════
            # ✅ ساختن User account برای شاگرد
            # ══════════════════════════════════════════
            username = request.POST.get('username','').strip()
            password = request.POST.get('password','').strip()
            
            # اگر username خالی بود، اتوماتیک بساز
            if not username:
                base = fname.lower().replace(' ','') or 'student'
                username = base
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base}{counter}"
                    counter += 1
            
            # اگر password خالی بود، password پیش‌فرض
            if not password:
                password = '12345678'
            
            # User را بساز یا موجود را پیدا کن
            if User.objects.filter(username=username).exists():
                user = User.objects.get(username=username)
                user.first_name = fname
                user.last_name = lname
                if email: user.email = email
                user.save()
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    first_name=fname,
                    last_name=lname,
                    email=email or f"{username}@gaam.edu"
                )
            
            # ══════════════════════════════════════════
            # ✅ ساختن Student record و وصل به User
            # ══════════════════════════════════════════
            student = Student.objects.create(
                user=user,
                first_name=fname,
                last_name=lname,
                father_name=request.POST.get('father_name',''),
                email=email or user.email,
                phone=request.POST.get('phone',''),
                address=request.POST.get('address',''),
                student_id=request.POST.get('student_id', f'S{user.id}'),
                class_field=request.POST.get('class_field',''),
                enrollment_date=request.POST.get('enrollment_date') or datetime.today().date(),
            )
            assign_role(user, 'student')
            
            messages.success(request, f'✅ شاگرد {student.first_name} اضافه شد | نام کاربری: {username} | پسورد: {password}')
            return redirect('students_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    return render(request, 'admin/student_form.html')

@login_required(login_url='login_chat')
def student_edit(request, pk):
    """
    ویرایش شاگرد
    """
    student = get_object_or_404(Student, pk=pk)
    
    if request.method == 'POST':
        try:
            fname = request.POST.get('first_name','').strip()
            lname = request.POST.get('last_name','').strip()
            
            student.first_name = fname
            student.last_name = lname
            student.father_name = request.POST.get('father_name','')
            student.email = request.POST.get('email','')
            student.phone = request.POST.get('phone','')
            student.address = request.POST.get('address','')
            student.student_id = request.POST.get('student_id', student.student_id)
            student.class_field = request.POST.get('class_field','')
            student.enrollment_date = request.POST.get('enrollment_date') or student.enrollment_date
            
            # ✅ آپدیت User هم اگر وصل باشد
            try:
                if student.user:
                    student.user.first_name = fname
                    student.user.last_name = lname
                    if request.POST.get('email'):
                        student.user.email = request.POST.get('email')
                    # تغییر پسورد اگر وارد شده
                    new_pass = request.POST.get('new_password','').strip()
                    if new_pass and len(new_pass) >= 6:
                        student.user.set_password(new_pass)
                    student.user.save()
                else:
                    # ✅ اگر user نداشت، الان بساز
                    username = fname.lower().replace(' ','') or f'student{student.id}'
                    base = username
                    counter = 1
                    while User.objects.filter(username=username).exclude(id=0).exists():
                        username = f"{base}{counter}"
                        counter += 1
                    user = User.objects.create_user(
                        username=username,
                        password='12345678',
                        first_name=fname,
                        last_name=lname,
                        email=student.email or f"{username}@gaam.edu"
                    )
                    student.user = user
                    messages.info(request, f'✅ User جدید ساخته شد: {username} / 12345678')
            except Exception as ue:
                pass  # user linking optional
            
            student.save()
            messages.success(request, '✅ شاگرد بروزرسانی شد')
            return redirect('students_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    context = {'student': student, 'edit_mode': True}
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
    transactions = Transaction.objects.all().order_by('-transaction_date')
    
    # محاسبه آمار
    total_income = Transaction.objects.filter(
        transaction_type='income'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    total_expense = Transaction.objects.filter(
        transaction_type='expense'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    net_income = total_income - total_expense
    total_payments = transactions.filter(student__isnull=False).aggregate(Sum('amount'))['amount__sum'] or 0
    
    context = {
        'transactions': transactions,
        'total_income': total_income,
        'total_expense': total_expense,
        'net_income': net_income,
        'total_payments': total_payments,
    }
    context.update(_get_profile_context(request.user))
    return render(request, 'admin/finance.html', context)


@login_required(login_url='login_chat')
def transaction_add(request):
    """
    افزودن تراکنش جدید - با auto-generate transaction_id
    """
    if request.method == 'POST':
        try:
            import uuid
            from datetime import date as _date

            # auto-generate unique transaction_id
            provided_id = request.POST.get('transaction_id', '').strip()
            if provided_id and not Transaction.objects.filter(transaction_id=provided_id).exists():
                trx_id = provided_id
            else:
                trx_id = f"TRX-{_date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

            student_id = request.POST.get('student') or None
            Transaction.objects.create(
                transaction_id=trx_id,
                transaction_type=request.POST.get('transaction_type'),
                amount=request.POST.get('amount'),
                transaction_date=request.POST.get('transaction_date'),
                description=request.POST.get('description', ''),
                category=request.POST.get('category', ''),
                status=request.POST.get('status', 'completed'),
                student_id=student_id if student_id else None
            )
            messages.success(request, '✅ تراکنش با موفقیت اضافه شد')
            # redirect back to correct dashboard
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')
            return redirect('finance_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')

    students = Student.objects.all()
    return render(request, 'admin/transaction_form.html', {'students': students})


@login_required(login_url='login_chat')
def transaction_edit(request, pk):
    """
    ویرایش تراکنش
    """
    transaction = get_object_or_404(Transaction, pk=pk)
    
    if request.method == 'POST':
        try:
            transaction.transaction_type = request.POST.get('transaction_type')
            transaction.amount = request.POST.get('amount')
            transaction.transaction_date = request.POST.get('transaction_date')
            transaction.description = request.POST.get('description', '')
            transaction.category = request.POST.get('category', '')
            transaction.status = request.POST.get('status', 'completed')
            
            student_id = request.POST.get('student') or None
            transaction.student_id = student_id if student_id else None
            
            transaction.save()
            
            messages.success(request, '✅ تراکنش با موفقیت بروزرسانی شد')
            referer = request.META.get('HTTP_REFERER', '')
            if 'finance' in referer and '/admin/' not in referer:
                return redirect('finance_dashboard')
            return redirect('finance_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    students = Student.objects.all()
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
    total_salary = employees.aggregate(Sum('salary'))['salary__sum'] or 0
    avg_salary = employees.aggregate(Sum('salary'))['salary__sum'] / total_employees if total_employees > 0 else 0
    
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
def employee_add(request):
    """
    افزودن کارمند جدید
    """
    if request.method == 'POST':
        try:
            employee = Employee.objects.create(
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                position=request.POST.get('position'),
                phone=request.POST.get('phone'),
                email=request.POST.get('email'),
                employee_id=request.POST.get('employee_id'),
                salary=request.POST.get('salary'),
                hire_date=request.POST.get('hire_date')
            )
            
            messages.success(request, f'✅ کارمند {employee.first_name} با موفقیت اضافه شد')
            return redirect('employees_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
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
            employee.first_name = request.POST.get('first_name')
            employee.last_name = request.POST.get('last_name')
            employee.position = request.POST.get('position')
            employee.phone = request.POST.get('phone')
            employee.email = request.POST.get('email')
            employee.employee_id = request.POST.get('employee_id')
            employee.salary = request.POST.get('salary')
            employee.hire_date = request.POST.get('hire_date')
            employee.save()
            
            messages.success(request, '✅ کارمند با موفقیت بروزرسانی شد')
            return redirect('employees_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
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
    medical_records = Medical.objects.all().order_by('-checkup_date')
    
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
def medical_add(request):
    """
    افزودن معاینه جدید
    """
    if request.method == 'POST':
        try:
            medical = Medical.objects.create(
                student_id=request.POST.get('student'),
                checkup_date=request.POST.get('checkup_date'),
                height=request.POST.get('height') or None,
                weight=request.POST.get('weight') or None,
                blood_pressure=request.POST.get('blood_pressure'),
                temperature=request.POST.get('temperature') or None,
                diagnosis=request.POST.get('diagnosis'),
                recommendations=request.POST.get('recommendations'),
                health_status=request.POST.get('health_status')
            )
            
            messages.success(request, '✅ معاینه با موفقیت اضافه شد')
            return redirect('medical_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    students = Student.objects.all()
    return render(request, 'admin/medical_form.html', {'students': students})


@login_required(login_url='login_chat')
def medical_edit(request, pk):
    """
    ویرایش معاینه
    """
    medical = get_object_or_404(Medical, pk=pk)
    
    if request.method == 'POST':
        try:
            medical.student_id = request.POST.get('student')
            medical.checkup_date = request.POST.get('checkup_date')
            medical.height = request.POST.get('height') or None
            medical.weight = request.POST.get('weight') or None
            medical.blood_pressure = request.POST.get('blood_pressure')
            medical.temperature = request.POST.get('temperature') or None
            medical.diagnosis = request.POST.get('diagnosis')
            medical.recommendations = request.POST.get('recommendations')
            medical.health_status = request.POST.get('health_status')
            medical.save()
            
            messages.success(request, '✅ معاینه با موفقیت بروزرسانی شد')
            return redirect('medical_list')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    
    students = Student.objects.all()
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
    try:
        total_income = float(Transaction.objects.filter(transaction_type='income').aggregate(s=Sum('amount'))['s'] or 0)
    except:
        total_income = 0
    try:
        total_expenses = float(Transaction.objects.filter(transaction_type='expense').aggregate(s=Sum('amount'))['s'] or 0)
    except:
        total_expenses = 0

    context = {
        # Students
        'total_students': Student.objects.count(),
        'active_students': Student.objects.filter(is_active=True).count(),
        'inactive_students': Student.objects.filter(is_active=False).count(),
        # Teachers
        'total_teachers': Teacher.objects.count(),
        'active_teachers': Teacher.objects.filter(is_active=True).count(),
        'inactive_teachers': Teacher.objects.filter(is_active=False).count(),
        # Employees
        'total_employees': Employee.objects.count(),
        'active_employees': Employee.objects.filter(is_active=True).count(),
        'total_salary': float(Employee.objects.filter(is_active=True).aggregate(s=Sum('salary'))['s'] or 0),
        # Attendance
        'total_attendance': Attendance.objects.count(),
        'present_count': Attendance.objects.filter(status='present').count(),
        'absent_count': Attendance.objects.filter(status='absent').count(),
        'leave_count': Attendance.objects.filter(status='leave').count(),
        # Finance
        'total_income': total_income,
        'total_expenses': total_expenses,
        'net_balance': total_income - total_expenses,
        'total_income_count': Transaction.objects.filter(transaction_type='income').count(),
        'total_expense_count': Transaction.objects.filter(transaction_type='expense').count(),
        # Medical
        'total_medical': Medical.objects.count(),
        'excellent_health': Medical.objects.filter(health_status='excellent').count(),
        'needs_care': Medical.objects.filter(health_status='needs_care').count(),
        # Classes
        'total_classes': Class.objects.count(),
        'active_classes': Class.objects.filter(is_active=True).count(),
        'total_capacity': int(Class.objects.aggregate(s=Sum('capacity'))['s'] or 0),
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
                user.first_name = request.POST.get('first_name', user.first_name)
                user.last_name = request.POST.get('last_name', user.last_name)
                user.email = request.POST.get('email', user.email)
                user.save()

                profile = _get_or_create_profile(user)
                if profile:
                    profile.phone = request.POST.get('phone', '')
                    profile.department = request.POST.get('department', '')
                    profile.bio = request.POST.get('bio', '')
                    profile.save()

                messages.success(request, '✅ معلومات شخصی با موفقیت ذخیره شد')
            except Exception as e:
                messages.error(request, f'❌ خطا: {str(e)}')

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
            from django.conf import settings
            import os
            # اطمینان از وجود MEDIA_ROOT
            media_root = getattr(settings, 'MEDIA_ROOT', None)
            if not media_root:
                messages.error(request, '❌ MEDIA_ROOT در settings.py تنظیم نشده است')
                return redirect('profile')
            profiles_dir = os.path.join(media_root, 'profiles')
            os.makedirs(profiles_dir, exist_ok=True)

            profile = _get_or_create_profile(request.user)
            if profile:
                profile.profile_picture = request.FILES['profile_picture']
                profile.save()
                messages.success(request, '✅ عکس پروفایل با موفقیت تغییر کرد')
            else:
                messages.error(request, '❌ پروفایل کاربر پیدا نشد')
        except Exception as e:
            messages.error(request, f'❌ خطا در آپلود: {str(e)}')
    return redirect('profile')


# ════════════════════════════════════════════════════════════════
# teacher_dashboard
# ════════════════════════════════════════════════════════════════

@login_required(login_url='login_chat')
def teacher_dashboard(request):
    """داشبورد معلم - کامل با همه داده‌ها"""
    # ── پیدا کردن Teacher با چند روش ──
    teacher = None

    # روش 1: از طریق user FK
    try:
        teacher = Teacher.objects.get(user=request.user)
    except Teacher.DoesNotExist:
        pass
    except Exception:
        pass

    # روش 2: از طریق email
    if not teacher and request.user.email:
        try:
            t = Teacher.objects.get(email=request.user.email)
            t.user = request.user
            t.save()
            teacher = t
        except Exception:
            pass

    # روش 3: از طریق نام
    if not teacher and request.user.first_name:
        try:
            fn = request.user.first_name.strip()
            qs = Teacher.objects.filter(first_name__iexact=fn)
            if qs.count() == 1:
                teacher = qs.first()
                teacher.user = request.user
                teacher.save()
        except Exception:
            pass

    today = datetime.today().date()

    def safe(fn):
        try: return fn()
        except Exception: return 0

    def safe_qs(fn):
        try: return fn()
        except Exception: return []

    # Stats
    total_students   = safe(lambda: Student.objects.count())
    active_students  = safe(lambda: Student.objects.filter(is_active=True).count())
    inactive_students= safe(lambda: Student.objects.filter(is_active=False).count())
    present_today    = safe(lambda: StudentPresence.objects.filter(date=today, status='present').count())
    absent_today     = safe(lambda: StudentPresence.objects.filter(date=today, status='absent').count())
    total_plans      = safe(lambda: TeacherPlan.objects.filter(teacher=teacher).count() if teacher else TeacherPlan.objects.filter(teacher__isnull=True).count())
    sp_present       = safe(lambda: StudentPresence.objects.filter(status='present').count())
    sp_absent        = safe(lambda: StudentPresence.objects.filter(status='absent').count())
    sp_leave         = safe(lambda: StudentPresence.objects.filter(status='leave').count())
    tp_present       = safe(lambda: TeacherPresence.objects.filter(teacher=teacher, status='present').count() if teacher else TeacherPresence.objects.filter(teacher__isnull=True, status='present').count())
    tp_absent        = safe(lambda: TeacherPresence.objects.filter(teacher=teacher, status='absent').count() if teacher else TeacherPresence.objects.filter(teacher__isnull=True, status='absent').count())
    tp_total         = tp_present + tp_absent
    tp_rate          = round(tp_present / tp_total * 100) if tp_total else 0
    h_excellent      = safe(lambda: StudentHealthReport.objects.filter(health_status='excellent').count())
    h_good           = safe(lambda: StudentHealthReport.objects.filter(health_status='good').count())
    h_care           = safe(lambda: StudentHealthReport.objects.filter(health_status='needs_care').count())

    # Querysets
    all_students     = safe_qs(lambda: Student.objects.all().order_by('-created_at'))
    student_presence = safe_qs(lambda: StudentPresence.objects.all().order_by('-date'))
    teacher_presence = safe_qs(lambda: TeacherPresence.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPresence.objects.filter(teacher__isnull=True).order_by('-date'))
    health_reports   = safe_qs(lambda: StudentHealthReport.objects.all().order_by('-date'))
    plans            = safe_qs(lambda: TeacherPlan.objects.filter(teacher=teacher).order_by('-date') if teacher else TeacherPlan.objects.filter(teacher__isnull=True).order_by('-date'))
    timetable        = safe_qs(lambda: TeacherTimetable.objects.filter(teacher=teacher).order_by('day','time_slot') if teacher else TeacherTimetable.objects.filter(teacher__isnull=True).order_by('day','time_slot'))
    all_classes      = safe_qs(lambda: Class.objects.filter(is_active=True))

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
    students = Student.objects.all().order_by('-created_at')
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
            from django.utils import timezone
            Student.objects.create(
                first_name=request.POST.get('fname',''),
                last_name=request.POST.get('lname',''),
                father_name=request.POST.get('father',''),
                phone=request.POST.get('phone',''),
                email=request.POST.get('email', f"s{timezone.now().timestamp()}@gaam.edu"),
                address=request.POST.get('address',''),
                student_id=f"S{int(datetime.now().timestamp())}",
                class_field=request.POST.get('cls',''),
                enrollment_date=datetime.today().date(),
                is_active=request.POST.get('status','active')=='active',
            )
            messages.success(request, '✅ شاگرد اضافه شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        try:
            student.first_name = request.POST.get('fname', student.first_name)
            student.last_name = request.POST.get('lname', student.last_name)
            student.father_name = request.POST.get('father', student.father_name)
            student.phone = request.POST.get('phone', student.phone)
            student.class_field = request.POST.get('cls', student.class_field)
            student.is_active = request.POST.get('status', 'active') == 'active'
            student.save()
            messages.success(request, '✅ شاگرد ویرایش شد')
        except Exception as e:
            messages.error(request, f'❌ خطا: {str(e)}')
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
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
            # ✅ student_id از form می‌آید - نام هم ذخیره می‌شود برای نمایش
            student_id = request.POST.get('student_id','')
            student_name = request.POST.get('name','')
            
            # اگر student_id داشت، نام را از دیتابیس بگیر
            if student_id:
                try:
                    st = Student.objects.get(id=student_id)
                    student_name = f"{st.first_name} {st.last_name}".strip()
                except Student.DoesNotExist:
                    pass
            
            StudentPresence.objects.create(
                student_name=student_name,
                student_id_fk=int(student_id) if student_id else None,
                date=request.POST.get('date', datetime.today().date()),
                status=request.POST.get('status','present'),
                note=request.POST.get('note',''),
            )
            messages.success(request, '✅ حضوری ثبت شد')
        except Exception as e:
            # Fallback: save without FK if column doesn't exist yet
            try:
                student_name = request.POST.get('name','')
                student_id = request.POST.get('student_id','')
                if student_id:
                    try:
                        st = Student.objects.get(id=student_id)
                        student_name = f"{st.first_name} {st.last_name}".strip()
                    except: pass
                StudentPresence.objects.create(
                    student_name=student_name,
                    date=request.POST.get('date', datetime.today().date()),
                    status=request.POST.get('status','present'),
                    note=request.POST.get('note',''),
                )
                messages.success(request, '✅ حضوری ثبت شد')
            except Exception as e2:
                messages.error(request, f'❌ خطا: {str(e2)}')
    return redirect('teacher_dashboard')


@login_required(login_url='login_chat')
def teacher_student_presence_delete(request, pk):
    obj = get_object_or_404(StudentPresence, pk=pk)
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
