"""
فقط این یک فایل را اجرا کنید:
python create_doctor_presence.py

این جدول core_doctorpresence را می‌سازد
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
import pymysql

db = settings.DATABASES['default']
conn = pymysql.connect(
    host=db.get('HOST', 'localhost'),
    port=int(db.get('PORT', 3306)),
    user=db['USER'],
    password=db['PASSWORD'],
    database=db['NAME'],
    charset='utf8mb4',
    autocommit=True,
)
cur = conn.cursor()
print("✅ اتصال به MySQL برقرار شد")

# ── بررسی جدول
cur.execute("SHOW TABLES LIKE 'core_doctorpresence'")
if cur.fetchone():
    print("✅ جدول core_doctorpresence موجود است")
    cur.execute("SELECT COUNT(*) FROM core_doctorpresence")
    count = cur.fetchone()[0]
    print(f"   تعداد رکوردها: {count}")
else:
    print("⚠️  جدول core_doctorpresence موجود نیست - در حال ساختن...")
    try:
        cur.execute("""
            CREATE TABLE core_doctorpresence (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                doctor_id INT NOT NULL,
                date DATE NOT NULL,
                status VARCHAR(20) NOT NULL DEFAULT 'present',
                note TEXT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (doctor_id) REFERENCES auth_user(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        print("✅ جدول core_doctorpresence ساخته شد!")
    except Exception as e:
        print(f"❌ خطا: {e}")

# ── ثبت migration
cur.execute("SELECT COUNT(*) FROM django_migrations WHERE app='core' AND name='0005_doctorpresence'")
if not cur.fetchone()[0]:
    cur.execute("INSERT INTO django_migrations (app,name,applied) VALUES ('core','0005_doctorpresence',NOW())")
    print("✅ migration 0005_doctorpresence ثبت شد")
else:
    print("✅ migration قبلاً ثبت شده")

# ── تست insert
print("\n── تست ثبت یک رکورد آزمایشی ──")
try:
    cur.execute("SELECT id FROM auth_user LIMIT 1")
    user = cur.fetchone()
    if user:
        cur.execute("""
            INSERT INTO core_doctorpresence (doctor_id, date, status, note)
            VALUES (%s, CURDATE(), 'present', 'تست آزمایشی')
        """, (user[0],))
        cur.execute("SELECT COUNT(*) FROM core_doctorpresence")
        print(f"✅ تست موفق! تعداد رکوردها: {cur.fetchone()[0]}")
        # حذف رکورد تستی
        cur.execute("DELETE FROM core_doctorpresence WHERE note='تست آزمایشی'")
        print("✅ رکورد تستی حذف شد")
    else:
        print("⚠️  هیچ کاربری در دیتابیس نیست")
except Exception as e:
    print(f"❌ تست ناموفق: {e}")

cur.close()
conn.close()

print("\n" + "="*40)
print("✅ تمام! حالا سرور را اجرا کنید:")
print("   python manage.py runserver")
print("="*40)
