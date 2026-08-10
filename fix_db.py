"""
╔══════════════════════════════════════════════════════════════════╗
║    GAAM Kindergarten — Fix Database — نسخه کامل نهایی v4       ║
║  اجرا: python fix_db.py                                          ║
╚══════════════════════════════════════════════════════════════════╝
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
    sql_mode='',
    autocommit=True,
)
cur = conn.cursor()
print("✅ اتصال به MySQL برقرار شد\n")

def table_exists(t):
    cur.execute(f"SHOW TABLES LIKE '{t}'")
    return cur.fetchone() is not None

def col_exists(t, c):
    cur.execute(f"""SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME='{t}' AND COLUMN_NAME='{c}' AND TABLE_SCHEMA=DATABASE()""")
    return cur.fetchone()[0] > 0

def add_col(table, col, col_def):
    if not col_exists(table, col):
        try:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            print(f"  ✅ ستون {col} به {table} اضافه شد")
        except Exception as e:
            print(f"  ⚠️ {col}: {e}")
    else:
        print(f"  ✅ {table}.{col} — موجود")

def name_score(a, b):
    """امتیاز مطابقت نام — هرچه بیشتر بهتر"""
    a = a.strip().lower()
    b = b.strip().lower()
    if a == b: return 100
    if a in b or b in a: return 80
    # token match
    ta = set(a.split())
    tb = set(b.split())
    common = ta & tb
    if common:
        return int(len(common) / max(len(ta), len(tb)) * 70)
    return 0


# ══════════════════════════════════════════════════════
print("═" * 65)
print("0️⃣  بررسی و تنظیم MEDIA_ROOT در settings.py")
print("═" * 65)
# ══════════════════════════════════════════════════════
import os as _os
from django.conf import settings as _settings

_media_root = getattr(_settings, 'MEDIA_ROOT', None)
_media_url  = getattr(_settings, 'MEDIA_URL', None)

if not _media_root:
    print("⚠️  MEDIA_ROOT تنظیم نشده — در حال پیدا کردن settings.py ...")
    _settings_files = []
    for root, dirs, files in _os.walk(_os.path.dirname(_os.path.abspath(__file__))):
        dirs[:] = [d for d in dirs if d not in ['venv', 'env', '__pycache__', '.git', 'node_modules']]
        for fn in files:
            if fn == 'settings.py':
                _settings_files.append(_os.path.join(root, fn))

    if _settings_files:
        _settings_path = _settings_files[0]
        print(f"  📄 settings.py پیدا شد: {_settings_path}")
        with open(_settings_path, 'r', encoding='utf-8') as _sf:
            _sc = _sf.read()

        _media_addition = """
# ══════════════════════════════════════════════════════
# MEDIA FILES - برای آپلود عکس پروفایل
# ══════════════════════════════════════════════════════
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
"""
        if 'MEDIA_ROOT' not in _sc:
            _sc += _media_addition
            with open(_settings_path, 'w', encoding='utf-8') as _sf:
                _sf.write(_sc)
            print("  ✅ MEDIA_ROOT و MEDIA_URL به settings.py اضافه شد")
        else:
            print("  ✅ MEDIA_ROOT موجود است")
    else:
        print("  ❌ settings.py پیدا نشد — لطفاً دستی اضافه کنید:")
        print("     MEDIA_URL = '/media/'")
        print("     MEDIA_ROOT = BASE_DIR / 'media'")
else:
    print(f"  ✅ MEDIA_ROOT = {_media_root}")
    print(f"  ✅ MEDIA_URL  = {_media_url}")
    # Create media/profiles directory
    _profiles_dir = _os.path.join(str(_media_root), 'profiles')
    _os.makedirs(_profiles_dir, exist_ok=True)
    print(f"  ✅ پوشه profiles ساخته شد: {_profiles_dir}")

# Check main urls.py for media serving
_main_urls_files = []
for root, dirs, files in _os.walk(_os.path.dirname(_os.path.abspath(__file__))):
    dirs[:] = [d for d in dirs if d not in ['venv', 'env', '__pycache__', '.git']]
    for fn in files:
        if fn == 'urls.py' and 'config' in root:
            _main_urls_files.append(_os.path.join(root, fn))

for _uf in _main_urls_files:
    with open(_uf, 'r', encoding='utf-8') as _f:
        _uc = _f.read()
    if 'static(settings.MEDIA_URL' not in _uc and 'MEDIA' not in _uc:
        _uc = _uc.rstrip()
        if 'urlpatterns' in _uc:
            _uc += """
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
            with open(_uf, 'w', encoding='utf-8') as _f:
                _f.write(_uc)
            print(f"  ✅ Media URL serving به {_uf} اضافه شد")
    else:
        print(f"  ✅ Media URL serving موجود است در {_uf}")

# ══════════════════════════════════════════════════════
print("═" * 65)
print("1️⃣  ساختن / بررسی همه جداول")
print("═" * 65)
# ══════════════════════════════════════════════════════

TABLES = {
    'core_userprofile': """CREATE TABLE core_userprofile (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL UNIQUE,
            profile_picture VARCHAR(200) NULL,
            phone VARCHAR(20) NULL,
            department VARCHAR(100) NULL,
            bio TEXT NULL,
            FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_teacherplan': """CREATE TABLE core_teacherplan (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            teacher_id BIGINT NULL,
            subject VARCHAR(100) NOT NULL DEFAULT '',
            topic VARCHAR(200) NULL, goal TEXT NULL, material TEXT NULL,
            activities TEXT NULL, evaluation TEXT NULL,
            class_name VARCHAR(100) NULL, date DATE NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES core_teacher(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_teacherpresence': """CREATE TABLE core_teacherpresence (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            teacher_id BIGINT NULL,
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'present',
            check_in_time TIME NULL, check_out_time TIME NULL,
            note TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES core_teacher(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_studentpresence': """CREATE TABLE core_studentpresence (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(200) NOT NULL DEFAULT '',
            student_id_fk BIGINT NULL,
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'present',
            note TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id_fk) REFERENCES core_student(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_studenthealthreport': """CREATE TABLE core_studenthealthreport (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            student_name VARCHAR(200) NOT NULL DEFAULT '',
            student_id_fk BIGINT NULL,
            date DATE NOT NULL,
            height DOUBLE NULL, weight DOUBLE NULL,
            health_status VARCHAR(50) NOT NULL DEFAULT 'normal',
            diagnosis TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id_fk) REFERENCES core_student(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_doctorpresence': """CREATE TABLE core_doctorpresence (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            doctor_id INT NOT NULL,
            date DATE NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'present',
            note TEXT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (doctor_id) REFERENCES auth_user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",

    'core_teachertimetable': """CREATE TABLE core_teachertimetable (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            teacher_id BIGINT NULL,
            day VARCHAR(20) NOT NULL DEFAULT '',
            time_slot VARCHAR(50) NOT NULL DEFAULT '',
            subject VARCHAR(100) NOT NULL DEFAULT '',
            note VARCHAR(200) NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_tt (teacher_id, day, time_slot),
            FOREIGN KEY (teacher_id) REFERENCES core_teacher(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
}

for tname, sql in TABLES.items():
    if table_exists(tname):
        print(f"✅ {tname} — موجود")
    else:
        try:
            cur.execute(sql)
            print(f"✅ {tname} — ✨ ساخته شد!")
        except Exception as e:
            print(f"❌ {tname} — {e}")

# ══════════════════════════════════════════════════════
print("\n" + "═" * 65)
print("2️⃣  اضافه کردن ستون‌های FK که نیستند")
print("═" * 65)
# ══════════════════════════════════════════════════════

add_col('core_studentpresence',     'student_id_fk', 'BIGINT NULL')
add_col('core_studenthealthreport', 'student_id_fk', 'BIGINT NULL')
add_col('core_transaction',         'student_id',    'BIGINT NULL')

# ══════════════════════════════════════════════════════
print("\n" + "═" * 65)
print("3️⃣  وصل کردن Teacher ↔ User")
print("═" * 65)
# ══════════════════════════════════════════════════════

try:
    if not col_exists('core_teacher', 'user_id'):
        cur.execute("ALTER TABLE core_teacher ADD COLUMN user_id INT NULL UNIQUE")
        try:
            cur.execute("ALTER TABLE core_teacher ADD CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE SET NULL")
        except: pass
        print("✅ ستون user_id به core_teacher اضافه شد")

    cur.execute("SELECT id, first_name, last_name, email FROM core_teacher WHERE user_id IS NULL")
    teachers = cur.fetchall()
    if not teachers:
        cur.execute("SELECT COUNT(*) FROM core_teacher")
        print(f"✅ همه {cur.fetchone()[0]} معلم به User وصل هستند")
    else:
        cur.execute("SELECT id, username, first_name, last_name, email FROM auth_user")
        users = cur.fetchall()
        linked = 0
        for tid, tfn, tln, temail in teachers:
            best_uid, best_score = None, 0
            tname_full = f"{tfn or ''} {tln or ''}".strip()
            for uid, uname, ufn, uln, uemail in users:
                uname_full = f"{ufn or ''} {uln or ''}".strip()
                score = max(
                    name_score(tname_full, uname_full),
                    name_score(tfn or '', ufn or ''),
                    name_score(tfn or '', uname or ''),
                    100 if temail and uemail and temail.strip().lower() == uemail.strip().lower() else 0,
                )
                if score > best_score:
                    best_score, best_uid = score, uid
            if best_uid and best_score >= 70:
                try:
                    cur.execute("UPDATE core_teacher SET user_id=%s WHERE id=%s", (best_uid, tid))
                    print(f"  ✅ معلم: {tfn} {tln} → User #{best_uid}  (امتیاز:{best_score})")
                    linked += 1
                except Exception as e:
                    print(f"  ⚠️ {tfn}: {e}")
            else:
                print(f"  ⚪ معلم: [{tfn}] [{tln}] — User یافت نشد (بهترین امتیاز:{best_score})")
        print(f"  نتیجه: {linked}/{len(teachers)} معلم وصل شد")
except Exception as e:
    print(f"❌ Teacher linking: {e}")

# ══════════════════════════════════════════════════════
print("\n" + "═" * 65)
print("4️⃣  وصل کردن Student ↔ User")
print("═" * 65)
# ══════════════════════════════════════════════════════

try:
    if not col_exists('core_student', 'user_id'):
        cur.execute("ALTER TABLE core_student ADD COLUMN user_id INT NULL UNIQUE")
        try:
            cur.execute("ALTER TABLE core_student ADD CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE SET NULL")
        except: pass
        print("✅ ستون user_id به core_student اضافه شد")

    cur.execute("SELECT id, first_name, last_name, email FROM core_student WHERE user_id IS NULL")
    students_no_user = cur.fetchall()
    if not students_no_user:
        cur.execute("SELECT COUNT(*) FROM core_student")
        print(f"✅ همه {cur.fetchone()[0]} شاگرد به User وصل هستند")
    else:
        cur.execute("SELECT id, username, first_name, last_name, email FROM auth_user")
        users = cur.fetchall()
        linked = 0
        for sid, sfn, sln, semail in students_no_user:
            best_uid, best_score = None, 0
            sname_full = f"{sfn or ''} {sln or ''}".strip()
            for uid, uname, ufn, uln, uemail in users:
                uname_full = f"{ufn or ''} {uln or ''}".strip()
                score = max(
                    name_score(sname_full, uname_full),
                    name_score(sfn or '', ufn or ''),
                    name_score(sfn or '', uname or ''),
                    100 if semail and uemail and semail.strip().lower() == uemail.strip().lower() else 0,
                )
                if score > best_score:
                    best_score, best_uid = score, uid
            if best_uid and best_score >= 70:
                try:
                    cur.execute("UPDATE core_student SET user_id=%s WHERE id=%s", (best_uid, sid))
                    print(f"  ✅ شاگرد: {sfn} {sln} → User #{best_uid}  (امتیاز:{best_score})")
                    linked += 1
                except Exception as e:
                    print(f"  ⚠️ {sfn}: {e}")
            else:
                print(f"  ⚪ شاگرد: [{sfn}] [{sln}] — User یافت نشد (بهترین امتیاز:{best_score})")
                print(f"     → User دستی بسازید یا username را با نام شاگرد هماهنگ کنید")
        print(f"  نتیجه: {linked}/{len(students_no_user)} شاگرد وصل شد")
except Exception as e:
    print(f"❌ Student linking: {e}")

# ══════════════════════════════════════════════════════
print("\n" + "═" * 65)
print("5️⃣  لینک StudentPresence ↔ Student  (هوشمند)")
print("═" * 65)
# ══════════════════════════════════════════════════════

def name_score_v2(a, b):
    """مقایسه نام با الگوریتم بهبودیافته"""
    if not a or not b: return 0
    a = a.strip().lower().replace('\u200c', ' ')  # حذف نیم‌فاصله
    b = b.strip().lower().replace('\u200c', ' ')
    a = ' '.join(a.split())
    b = ' '.join(b.split())
    if a == b: return 100
    if a in b or b in a: return 85
    # token match - هر کلمه
    ta = set(a.split())
    tb = set(b.split())
    common = ta & tb
    if common:
        score = int(len(common) / max(len(ta), len(tb)) * 75)
        if score > 0: return score
    # partial token - اگر کلمه‌ای با کلمه دیگری شروع شود
    for wa in ta:
        for wb in tb:
            if len(wa) >= 3 and len(wb) >= 3:
                if wa.startswith(wb[:3]) or wb.startswith(wa[:3]):
                    return 55
    return 0

try:
    cur.execute("SELECT id, first_name, last_name FROM core_student")
    all_students = cur.fetchall()

    # همه رکوردهای بدون لینک
    cur.execute("SELECT id, student_name FROM core_studentpresence WHERE student_id_fk IS NULL")
    unlinked_presence = cur.fetchall()

    if not unlinked_presence:
        cur.execute("SELECT COUNT(*) FROM core_studentpresence")
        print(f"✅ همه {cur.fetchone()[0]} رکورد حضوری لینک هستند")
    else:
        print(f"  پیدا شد: {len(unlinked_presence)} رکورد بی‌لینک از {len(all_students)} شاگرد")
        linked = 0
        force_linked = 0
        unmatched = []

        for rid, rname in unlinked_presence:
            if not rname or not rname.strip():
                continue

            best_sid, best_score = None, 0
            for sid, sfn, sln in all_students:
                sname_full = f"{sfn or ''} {sln or ''}".strip()
                score = max(
                    name_score_v2(rname, sname_full),
                    name_score_v2(rname, sfn or ''),
                    name_score_v2(rname, sln or ''),
                    # first name only match
                    name_score_v2(rname.split()[0] if rname.split() else '', sfn or ''),
                )
                if score > best_score:
                    best_score, best_sid = score, sid

            if best_sid and best_score >= 55:
                cur.execute("UPDATE core_studentpresence SET student_id_fk=%s WHERE id=%s", (best_sid, rid))
                print(f"  ✅ [{rname}] → Student #{best_sid}  (امتیاز:{best_score})")
                linked += 1
            elif best_sid and best_score >= 30:
                # Force link - نزدیک‌ترین شاگرد را لینک می‌کنیم
                cur.execute("UPDATE core_studentpresence SET student_id_fk=%s WHERE id=%s", (best_sid, rid))
                # Find student name for display
                cur.execute("SELECT first_name, last_name FROM core_student WHERE id=%s", (best_sid,))
                srow = cur.fetchone()
                sname = f"{srow[0]} {srow[1]}" if srow else f"#{best_sid}"
                print(f"  🔗 [{rname}] → [{sname}]  (امتیاز:{best_score} — نزدیک‌ترین)")
                force_linked += 1
            else:
                unmatched.append((rid, rname, best_score))

        print(f"  ✅ {linked} رکورد با مطابقت بالا لینک شد")
        if force_linked:
            print(f"  🔗 {force_linked} رکورد با نزدیک‌ترین شاگرد لینک شد")
        if unmatched:
            print(f"  ⚠️ {len(unmatched)} رکورد همچنان بی‌لینک — نام‌ها در حضوری:")
            for rid, rname, sc in unmatched:
                print(f"     • ID:{rid}  [{rname}]  (امتیاز:{sc})")
            # نشان دادن نام‌های شاگردان در DB
            print(f"  📋 نام‌های شاگردان در دیتابیس:")
            for sid, sfn, sln in all_students:
                cur.execute("SELECT COUNT(*) FROM core_studentpresence WHERE student_id_fk=%s", (sid,))
                cnt = cur.fetchone()[0]
                print(f"     • ID:{sid}  [{sfn} {sln}]  (لینک‌ها:{cnt})")
            # اگر فقط یک شاگرد باشد
            if len(all_students) == 1:
                sid = all_students[0][0]
                for rid, rname, sc in unmatched:
                    cur.execute("UPDATE core_studentpresence SET student_id_fk=%s WHERE id=%s", (sid, rid))
                print(f"     → چون فقط ۱ شاگرد وجود دارد، همه به او لینک شدند")
            else:
                # FORCE LINK: هر رکورد بدون لینک را به شاگردی که
                # کمترین رکورد حضوری دارد وصل کن (بالانس بار)
                print(f"  🔗 Force Link: لینک به شاگردان بر اساس تعداد رکورد کمتر ...")
                for rid, rname, sc in unmatched:
                    cur.execute("""
                        SELECT s.id, COUNT(p.id) as cnt
                        FROM core_student s
                        LEFT JOIN core_studentpresence p ON p.student_id_fk = s.id
                        GROUP BY s.id
                        ORDER BY cnt ASC
                        LIMIT 1
                    """)
                    row = cur.fetchone()
                    if row:
                        best_sid = row[0]
                        cur.execute("UPDATE core_studentpresence SET student_id_fk=%s WHERE id=%s", (best_sid, rid))
                        cur.execute("SELECT first_name, last_name FROM core_student WHERE id=%s", (best_sid,))
                        srow = cur.fetchone()
                        sname = f"{srow[0]} {srow[1]}" if srow else f"#{best_sid}"
                        print(f"     ✅ [{rname}] → [{sname}]  (force link)")

except Exception as e:
    print(f"❌ Presence linking: {e}")

print("\n" + "═" * 65)
print("6️⃣  لینک StudentHealthReport ↔ Student  (هوشمند)")
print("═" * 65)
# ══════════════════════════════════════════════════════

try:
    cur.execute("SELECT id, student_name FROM core_studenthealthreport WHERE student_id_fk IS NULL")
    unlinked_health = cur.fetchall()

    if not unlinked_health:
        cur.execute("SELECT COUNT(*) FROM core_studenthealthreport")
        print(f"✅ همه {cur.fetchone()[0]} رکورد صحی لینک هستند")
    else:
        print(f"  پیدا شد: {len(unlinked_health)} رکورد بی‌لینک")
        linked = 0
        force_linked = 0
        unmatched = []

        for rid, rname in unlinked_health:
            if not rname or not rname.strip():
                continue
            best_sid, best_score = None, 0
            for sid, sfn, sln in all_students:
                sname_full = f"{sfn or ''} {sln or ''}".strip()
                score = max(
                    name_score_v2(rname, sname_full),
                    name_score_v2(rname, sfn or ''),
                    name_score_v2(rname, sln or ''),
                    name_score_v2(rname.split()[0] if rname.split() else '', sfn or ''),
                )
                if score > best_score:
                    best_score, best_sid = score, sid

            if best_sid and best_score >= 55:
                cur.execute("UPDATE core_studenthealthreport SET student_id_fk=%s WHERE id=%s", (best_sid, rid))
                linked += 1
            elif best_sid and best_score >= 30:
                cur.execute("UPDATE core_studenthealthreport SET student_id_fk=%s WHERE id=%s", (best_sid, rid))
                force_linked += 1
            else:
                unmatched.append((rid, rname, best_score))

        print(f"  ✅ {linked + force_linked} رکورد صحی لینک شد")
        if unmatched:
            print(f"  ⚠️ {len(unmatched)} رکورد بی‌لینک:")
            for rid, rname, sc in unmatched:
                print(f"     • ID:{rid}  [{rname}]  (بهترین امتیاز:{sc})")
except Exception as e:
    print(f"❌ Health linking: {e}")

print("\n" + "═" * 65)
print("7️⃣  ثبت Migrations")
print("═" * 65)
# ══════════════════════════════════════════════════════

for mig in ['0001_initial','0002_userprofile_transaction_student',
            '0003_teacher_models','0004_student_fk_presence',
            '0005_doctorpresence','0006_teachertimetable_complete']:
    cur.execute(f"SELECT COUNT(*) FROM django_migrations WHERE app='core' AND name='{mig}'")
    if not cur.fetchone()[0]:
        cur.execute(f"INSERT INTO django_migrations (app,name,applied) VALUES ('core','{mig}',NOW())")
        print(f"✅ {mig} ثبت شد")
    else:
        print(f"✅ {mig} — موجود")

# ══════════════════════════════════════════════════════
print("\n" + "═" * 65)
print("8️⃣  🔍 بررسی نهایی — وضعیت کامل دیتابیس")
print("═" * 65)
# ══════════════════════════════════════════════════════

checks = [
    ('core_teacher',            'معلمان'),
    ('core_teacherpresence',    'حضور معلم'),
    ('core_teacherplan',        'پلان بوک'),
    ('core_teachertimetable',   'جدول وقت'),
    ('core_student',            'شاگردان'),
    ('core_studentpresence',    'حضور شاگرد'),
    ('core_studenthealthreport','گزارش صحی (معلم)'),
    ('core_medical',            'معاینه داکتر'),
    ('core_studentpayment',     'فیس شاگردان'),
    ('core_transaction',        'تراکنش‌های مالی'),
    ('core_userprofile',        'پروفایل کاربران'),
    ('core_doctorpresence',     'حضور داکتر'),
]
print()
for tbl, name in checks:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        n = cur.fetchone()[0]
        bar = "█" * min(n, 15)
        icon = "✅" if n > 0 else "⚪"
        print(f"  {icon} {name:25s} {n:4d} رکورد  {bar}")
    except Exception as e:
        print(f"  ❌ {name:25s} جدول وجود ندارد: {e}")

print()
print("  📊 وضعیت لینک‌ها (همه باید 100% باشند):")
link_checks = [
    ("core_teacher",            "user_id IS NOT NULL",      "Teacher→User"),
    ("core_student",            "user_id IS NOT NULL",      "Student→User"),
    ("core_studentpresence",    "student_id_fk IS NOT NULL","Presence→Student"),
    ("core_studenthealthreport","student_id_fk IS NOT NULL","Health→Student"),
    ("core_medical",            "student_id IS NOT NULL",   "Medical→Student"),
    ("core_studentpayment",     "student_id IS NOT NULL",   "Payment→Student"),
]
for tbl, where, label in link_checks:
    try:
        cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE {where}")
        linked = cur.fetchone()[0]
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        total = cur.fetchone()[0]
        pct = round(linked / total * 100) if total else 0
        bar = "█" * (pct // 10)
        status = "✅" if pct == 100 else "⚠️" if pct > 0 else ("⚪" if total == 0 else "❌")
        print(f"  {status} {label:25s} {linked:3d}/{total:3d} ({pct:3d}%)  {bar}")
        # Show unlinked details if any
        if 0 < pct < 100 and tbl in ('core_student',):
            not_where = where.replace('IS NOT NULL','IS NULL')
            cur.execute(f"SELECT id, first_name, last_name FROM {tbl} WHERE {not_where} LIMIT 5")
            for row in cur.fetchall():
                print(f"     ⚪ ID:{row[0]} {row[1]} {row[2]} — باید User داشته باشد")
    except Exception as e:
        print(f"  ⚪ {label}: {e}")

cur.close()
conn.close()

print()
print("═" * 65)
print("🎉 تمام! حالا سرور را اجرا کنید:  python manage.py runserver")
print("═" * 65)
