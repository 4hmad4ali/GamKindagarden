# 🎓 GAAM Kindergarten Management System

## 📍 معلومات کودکستان

**نام:** GAAM Kindergarten  
**آدرس:** Microrayan 3rd District (مکروریان سوم)  
**شماره تماس:** 0788919112  
**ملک:** Afghanistan  

---

## 🎯 درباره سیستم

یک سیستم جامع مدیریت کودکستان با:
- ✅ 5 داشبورد مختلف
- ✅ سیستم Chat یکپارچه
- ✅ مدیریت شاگردان، معلمان، کارمندان
- ✅ مدیریت مالی و حضوری
- ✅ گزارش‌های تفصیلی

---

## 🚀 نصب سریع

```bash
# 1. استخراج ZIP
unzip gaam_kindergarten.zip
cd gaam_kindergarten

# 2. Virtual Environment
python -m venv venv
venv\Scripts\activate  # Windows

# 3. نصب وابستگی‌ها
pip install -r requirements.txt

# 4. Database
python manage.py makemigrations
python manage.py migrate

# 5. Super User
python manage.py createsuperuser

# 6. اجرا
python manage.py runserver
```

---

## 🔗 دسترسی

- **URL:** http://localhost:8000/
- **ثبت نام:** /signup/
- **ورود:** /login/
- **Admin:** /admin/

---

## 📋 داشبوردها

1. **Admin** - مدیریت کل سیستم
2. **Teacher** - مدیریت کلاس و شاگردان
3. **Student** - اطلاعات و حضوری
4. **Doctor** - مدیریت سلامت
5. **Finance** - مدیریت مالی

---

**Version:** 1.0  
**Status:** ✅ Production Ready
