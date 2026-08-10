"""
این script برای شاگردان قدیمی که User ندارند، User می‌سازد
python link_students.py
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth.models import User
from core.models import Student

students_no_user = Student.objects.filter(user__isnull=True)
print(f"📋 {students_no_user.count()} شاگرد بدون User\n")

for s in students_no_user:
    # ساختن username از نام
    base = s.first_name.lower().replace(' ','') if s.first_name else f'student{s.id}'
    username = base
    i = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}{i}"
        i += 1
    
    # ساختن User
    user = User.objects.create_user(
        username=username,
        password='12345678',
        first_name=s.first_name or '',
        last_name=s.last_name or '',
        email=s.email or f"{username}@gaam.edu"
    )
    
    # وصل به Student
    s.user = user
    s.save()
    
    print(f"✅ {s.first_name} {s.last_name}")
    print(f"   نام کاربری: {username}")
    print(f"   پسورد: 12345678")
    print()

print("🎉 تمام! شاگردان می‌توانند با این اطلاعات وارد شوند")
print("آدرس ورود: /login/")
