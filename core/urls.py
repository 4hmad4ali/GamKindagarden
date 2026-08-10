from django.urls import path
from . import views

urlpatterns = [
    # ════════════════════════════════════════════════════════════
    # صفحه اصلی
    # ════════════════════════════════════════════════════════════
    
    path('', views.homepage, name='homepage'),
    
    # ════════════════════════════════════════════════════════════
    # Admin Dashboard - صفحه اول
    # ════════════════════════════════════════════════════════════
    
    path('admin/', views.admin_dashboard, name='admin_dashboard'),
    
    # ════════════════════════════════════════════════════════════
    # Attendance - حضوری
    # ════════════════════════════════════════════════════════════
    
    path('admin/attendance/', views.attendance_list, name='attendance_list'),
    path('admin/attendance/add/', views.attendance_add, name='attendance_add'),
    path('admin/attendance/<int:pk>/edit/', views.attendance_edit, name='attendance_edit'),
    path('admin/attendance/<int:pk>/delete/', views.attendance_delete, name='attendance_delete'),    
        
    # ════════════════════════════════════════════════════════════
    # Teachers - معلمان
    # ════════════════════════════════════════════════════════════
    
    path('admin/teachers/', views.teachers_list, name='teachers_list'),
    path('admin/teachers/add/', views.teacher_add, name='teacher_add'),
    path('admin/teachers/<int:pk>/edit/', views.teacher_edit, name='teacher_edit'),
    path('admin/teachers/<int:pk>/delete/', views.teacher_delete, name='teacher_delete'),
    
    # ════════════════════════════════════════════════════════════
    # Students - شاگردان
    # ════════════════════════════════════════════════════════════
    
    path('admin/students/', views.students_list, name='students_list'),
    path('admin/students/add/', views.student_add, name='student_add'),
    path('admin/students/<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('admin/students/<int:pk>/delete/', views.student_delete, name='student_delete'),
    
    # ════════════════════════════════════════════════════════════
    # Finance - مالیات
    # ════════════════════════════════════════════════════════════
    
    path('admin/finance/', views.finance_list, name='finance_list'),
    path('admin/finance/add/', views.transaction_add, name='transaction_add'),
    path('admin/finance/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('admin/finance/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
     
    # ════════════════════════════════════════════════════════════
    # Employees - کارمندان
    # ════════════════════════════════════════════════════════════
    
    path('admin/employees/', views.employees_list, name='employees_list'),
    path('admin/employees/add/', views.employee_add, name='employee_add'),
    path('admin/employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('admin/employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
     
    # ════════════════════════════════════════════════════════════
    # Doctor - دکتر
    # ════════════════════════════════════════════════════════════
    
    path('admin/medical/', views.medical_list, name='medical_list'),
    path('admin/medical/add/', views.medical_add, name='medical_add'),
    path('admin/medical/<int:pk>/edit/', views.medical_edit, name='medical_edit'),
    path('admin/medical/<int:pk>/delete/', views.medical_delete, name='medical_delete'),
     
    # ════════════════════════════════════════════════════════════
    # Reports - گزارشات
    # ════════════════════════════════════════════════════════════
    
    path('admin/reports/', views.reports, name='reports'),
    
    # ════════════════════════════════════════════════════════════
    # Classes - کلاس‌ها
    # ════════════════════════════════════════════════════════════
    
    path('admin/classes/', views.classes_list, name='classes_list'),
    path('admin/classes/add/', views.class_add, name='class_add'),
    path('admin/classes/<int:pk>/edit/', views.class_edit, name='class_edit'),
    path('admin/classes/<int:pk>/delete/', views.class_delete, name='class_delete'),

    
    # ════════════════════════════════════════════════════════════
    # Profile - پروفایل
    # ════════════════════════════════════════════════════════════
    
    path('admin/profile/', views.profile, name='profile'),
    path('admin/profile/update/', views.profile_update, name='profile_update'),
    path('admin/profile/picture/', views.profile_upload_picture, name='profile_upload_picture'),

    # ════════════════════════════════════════════════════════════
    # Teacher Dashboard  ✅ NEW
    # ════════════════════════════════════════════════════════════
    path('teacher/', views.teacher_dashboard, name='teacher_dashboard'),

    # Students (teacher)
    path('teacher/students/add/', views.teacher_student_add, name='teacher_student_add'),
    path('teacher/students/<int:pk>/edit/', views.teacher_student_edit, name='teacher_student_edit'),
    path('teacher/students/<int:pk>/delete/', views.teacher_student_delete, name='teacher_student_delete'),

    # Student Presence
    path('teacher/student-presence/add/', views.teacher_student_presence_add, name='teacher_student_presence_add'),
    path('teacher/student-presence/<int:pk>/delete/', views.teacher_student_presence_delete, name='teacher_student_presence_delete'),

    # Student Health
    path('teacher/health/add/', views.teacher_health_add, name='teacher_health_add'),
    path('teacher/health/<int:pk>/delete/', views.teacher_health_delete, name='teacher_health_delete'),

    # Teacher Presence
    path('teacher/presence/add/', views.teacher_presence_add, name='teacher_presence_add'),
    path('teacher/presence/<int:pk>/delete/', views.teacher_presence_delete, name='teacher_presence_delete'),

    # Plans
    path('teacher/plan/add/', views.teacher_plan_add, name='teacher_plan_add'),
    path('teacher/plan/<int:pk>/edit/', views.teacher_plan_edit, name='teacher_plan_edit'),
    path('teacher/plan/<int:pk>/delete/', views.teacher_plan_delete, name='teacher_plan_delete'),
    
    # Teacher Presence Edit
    path('teacher/presence/<int:pk>/edit/', views.teacher_presence_edit, name='teacher_presence_edit'),

    # Timetable Edit
    path('teacher/timetable/<int:pk>/edit/', views.teacher_timetable_edit, name='teacher_timetable_edit'),

    # Timetable
    path('teacher/timetable/add/', views.teacher_timetable_add, name='teacher_timetable_add'),
    path('teacher/timetable/<int:pk>/delete/', views.teacher_timetable_delete, name='teacher_timetable_delete'),

    # Teacher Profile
    path('teacher/profile/update/', views.teacher_profile_update, name='teacher_profile_update'),
    path('teacher/profile/picture/', views.teacher_profile_picture, name='teacher_profile_picture'),


    # ════════════════════════════════════════════════════════════
    # Dashboards شاگرد 
    # ════════════════════════════════════════════════════════════
    
    path('student/', views.student_dashboard, name='student_dashboard'),
    path('student/profile/update/', views.student_profile_update, name='student_profile_update'),
    path('student/profile/picture/', views.student_profile_picture, name='student_profile_picture'),

    # ════════════════════════════════════════════════════════════════
    # Doctor Dashboard - داشبورد داکتر
    # ════════════════════════════════════════════════════════════════
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/record/<int:pk>/delete/', views.doctor_record_delete, name='doctor_record_delete'),
    path('doctor/presence/<int:pk>/delete/', views.doctor_presence_delete,  name='doctor_presence_delete'),
    path('doctor/profile/update/',        views.doctor_profile_update,  name='doctor_profile_update'),
    path('doctor/profile/picture/',       views.doctor_profile_picture,  name='doctor_profile_picture'),  
    

    # ════════════════════════════════════════════════════════════════
    # Finance Dashboard - داشبورد مالی
    # ════════════════════════════════════════════════════════════════
    path('finance/', views.finance_dashboard, name='finance_dashboard'),
    path('finance/payment/add/', views.finance_payment_add, name='finance_payment_add'),
    path('finance/payment/<int:pk>/edit/', views.finance_payment_edit, name='finance_payment_edit'),
    path('finance/payment/<int:pk>/mark/', views.finance_payment_mark, name='finance_payment_mark'),
    path('finance/payment/<int:pk>/delete/', views.finance_payment_delete, name='finance_payment_delete'),
    path('finance/profile/update/', views.finance_profile_update, name='finance_profile_update'),
    path('finance/profile/picture/', views.finance_profile_picture, name='finance_profile_picture'),
]
