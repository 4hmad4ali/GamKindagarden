# Deploy GAAM Kindergarten to Railway

## 1. Push the project to GitHub

Do not commit `.env`, `media/`, `staticfiles/`, `venv/`, or `.venv/`.

## 2. Create the Railway project

1. Create a new Railway project.
2. Add a **MySQL** database service.
3. Add a service from this GitHub repository.
4. In the Django web service, create references to the MySQL service variables:

   - `MYSQLDATABASE=${{MySQL.MYSQLDATABASE}}`
   - `MYSQLUSER=${{MySQL.MYSQLUSER}}`
   - `MYSQLPASSWORD=${{MySQL.MYSQLPASSWORD}}`
   - `MYSQLHOST=${{MySQL.MYSQLHOST}}`
   - `MYSQLPORT=${{MySQL.MYSQLPORT}}`

   Use the actual database service name if it is not `MySQL`.

## 3. Add the Django environment variables

Generate a new secret key with:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

In Railway Variables, set:

```text
SECRET_KEY=<new random value>
DEBUG=False
DJANGO_ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}}
CSRF_TRUSTED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}}
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
INITIAL_ADMIN_USERNAME=<your-admin-username>
INITIAL_ADMIN_PASSWORD=<long-unique-password>
INITIAL_ADMIN_EMAIL=<admin-email>
```

After generating a Railway domain, redeploy so the host and CSRF variables resolve correctly. For a custom domain, append it to both variables:

```text
DJANGO_ALLOWED_HOSTS=${{RAILWAY_PUBLIC_DOMAIN}},app.example.com
CSRF_TRUSTED_ORIGINS=https://${{RAILWAY_PUBLIC_DOMAIN}},https://app.example.com
```

## 4. Deploy

`railway.toml` automatically performs these steps:

1. Collects static files during build.
2. Runs Django migrations before deploying.
3. Creates the first superuser from the protected `INITIAL_ADMIN_*` variables,
   only when no superuser already exists.
4. Starts Gunicorn and exposes `/healthz/` for Railway health checks.

The project pins Railway's Python runtime to 3.11 in `.python-version` so the
deployment does not silently move to a newer Python version that older project
dependencies may not support.

The bootstrap command never changes the password of an existing administrator.
After the first deployment, use that administrator to create other users from
the application or Django admin.

## Important: uploaded profile images

Railway's application filesystem is ephemeral unless you attach a Volume. This project stores profile images under `media/`; do not rely on a free or temporary filesystem for production student data. Before a real launch, use a Railway Volume or object storage such as Cloudflare R2, Amazon S3, or Cloudinary, and implement automated database backups.
