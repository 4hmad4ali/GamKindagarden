# 📊 MySQL نصب و تنظیم

## ✅ MySQL نصب کنید

### Windows:
1. دانلود: https://dev.mysql.com/downloads/mysql/
2. نسخه: MySQL 8.0 Community Server
3. نصب کنید (استاندارد)
4. رمز: password123

### Linux (Ubuntu/Debian):
```bash
sudo apt-get update
sudo apt-get install mysql-server mysql-client
sudo mysql_secure_installation
```

### Mac:
```bash
brew install mysql
mysql.server start
```

## 📝 Database ایجاد کنید

```bash
mysql -u root -p
```

رمز: `password123`

سپس:

```sql
CREATE DATABASE gaam_kindergarten_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE USER 'root'@'localhost' IDENTIFIED BY 'password123';

GRANT ALL PRIVILEGES ON gaam_kindergarten_db.* TO 'root'@'localhost';

FLUSH PRIVILEGES;

EXIT;
```

## ✔️ تائید موفقیت

```bash
mysql -u root -p -e "SHOW DATABASES;"
```

باید `gaam_kindergarten_db` را ببینید.

## 🐍 Django تنظیمات

فایل `config/settings.py` میں:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'gaam_kindergarten_db',
        'USER': 'root',
        'PASSWORD': 'password123',
        'HOST': 'localhost',
        'PORT': '3306',
    }
}
```

## ▶️ اجرا

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

---

✅ تمام!
