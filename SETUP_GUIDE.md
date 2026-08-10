# 🎓 GAAM Kindergarten - راهنمای نصب

## معلومات کودکستان

- **نام:** GAAM Kindergarten
- **آدرس:** مکروریان سوم، کابل
- **تماس:** 0788919112

## مراحل نصب

### 1. MySQL نصب کنید

```sql
CREATE DATABASE gaam_kindergarten_db CHARACTER SET utf8mb4;
CREATE USER 'root'@'localhost' IDENTIFIED BY 'password123';
GRANT ALL PRIVILEGES ON gaam_kindergarten_db.* TO 'root'@'localhost';
```

### 2. Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. نصب وابستگی‌ها

```bash
pip install -r requirements.txt
```

### 4. Database Setup

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Super User

```bash
python manage.py createsuperuser
```

### 6. اجرا

```bash
python manage.py runserver
```

## دسترسی

- Signup: http://localhost:8000/signup/
- Login: http://localhost:8000/login/
- Admin: http://localhost:8000/admin/

---

**Version:** 1.0
