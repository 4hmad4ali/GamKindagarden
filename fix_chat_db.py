"""
╔══════════════════════════════════════════════════════════╗
║  GAAM Chat — Database Setup                              ║
║  اجرا کنید: python fix_chat_db.py                        ║
╚══════════════════════════════════════════════════════════╝
"""
import os, sys, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.conf import settings
import pymysql

db   = settings.DATABASES['default']
conn = pymysql.connect(
    host     = db.get('HOST', 'localhost'),
    port     = int(db.get('PORT', 3306)),
    user     = db['USER'],
    password = db['PASSWORD'],
    database = db['NAME'],
    charset  = 'utf8mb4',
    autocommit = True,
)
cur = conn.cursor()
print("✅ Connected to MySQL\n")

# ──────────────────────────────────────────────
# 1. ChatUserProfile
# ──────────────────────────────────────────────
cur.execute("SHOW TABLES LIKE 'chat_chatuserprofile'")
if cur.fetchone():
    print("✅ chat_chatuserprofile  — already exists")
else:
    cur.execute("""
        CREATE TABLE chat_chatuserprofile (
            id              BIGINT AUTO_INCREMENT PRIMARY KEY,
            user_id         INT NOT NULL UNIQUE,
            profile_picture VARCHAR(200) NULL DEFAULT NULL,
            is_online       TINYINT(1) NOT NULL DEFAULT 0,
            last_seen       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                            ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES auth_user(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("✅ chat_chatuserprofile  — CREATED")

# ──────────────────────────────────────────────
# 2. DirectMessage
# ──────────────────────────────────────────────
cur.execute("SHOW TABLES LIKE 'chat_directmessage'")
if cur.fetchone():
    print("✅ chat_directmessage    — already exists")
else:
    cur.execute("""
        CREATE TABLE chat_directmessage (
            id          BIGINT AUTO_INCREMENT PRIMARY KEY,
            sender_id   INT NOT NULL,
            receiver_id INT NOT NULL,
            content     LONGTEXT NOT NULL,
            is_read     TINYINT(1) NOT NULL DEFAULT 0,
            created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (sender_id)   REFERENCES auth_user(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES auth_user(id) ON DELETE CASCADE,
            INDEX idx_sender   (sender_id),
            INDEX idx_receiver (receiver_id),
            INDEX idx_created  (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    print("✅ chat_directmessage    — CREATED")

# ──────────────────────────────────────────────
# 3. Register migrations
# ──────────────────────────────────────────────
for mig in ['0001_initial', '0002_chatuserprofile_directmessage']:
    cur.execute(
        "SELECT COUNT(*) FROM django_migrations WHERE app='chat' AND name=%s", (mig,)
    )
    if not cur.fetchone()[0]:
        cur.execute(
            "INSERT INTO django_migrations (app, name, applied) VALUES ('chat', %s, NOW())",
            (mig,)
        )
        print(f"✅ migration {mig} registered")

# ──────────────────────────────────────────────
# 4. Clear old tables if they exist (ChatRoom, ChatMessage)
# ──────────────────────────────────────────────
for old_table in ['chat_chatmessage', 'chat_chatroom_members', 'chat_chatroom']:
    cur.execute(f"SHOW TABLES LIKE '{old_table}'")
    if cur.fetchone():
        cur.execute(f"DROP TABLE IF EXISTS `{old_table}`")
        print(f"🗑️  Dropped old table: {old_table}")

# ──────────────────────────────────────────────
# 5. Status
# ──────────────────────────────────────────────
print("\n📊 Status:")
for tbl in ['chat_chatuserprofile', 'chat_directmessage']:
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{tbl}`")
        print(f"   {tbl}: {cur.fetchone()[0]} rows")
    except Exception:
        print(f"   {tbl}: ⚠️ not found")

cur.close()
conn.close()
print("\n✅ Done! Run: python manage.py runserver")
