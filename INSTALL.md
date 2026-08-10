# 🚀 نصب سریع

## 1️⃣ استخراج

```bash
unzip gaam_kindergarten.zip
cd gaam_kindergarten
```

## 2️⃣ MySQL

```bash
mysql -u root -p
CREATE DATABASE gaam_kindergarten_db CHARACTER SET utf8mb4;
EXIT;
```

## 3️⃣ نصب

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 4️⃣ Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

## 5️⃣ اجرا

```bash
python manage.py runserver
```

## 6️⃣ دسترسی

- http://localhost:8000/signup/
- http://localhost:8000/login/

---

✅ تمام!
