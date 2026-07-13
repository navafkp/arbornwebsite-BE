# Arborn Backend

Django + Django REST Framework API for the Arborn Next.js frontend.

## Apps

- **accounts** — custom `User` model (email-based), Google Sign-In verification, email OTP login, JWT issue/refresh, profile + addresses
- **catalog** — categories, products, colors, images, sizes, reviews
- **orders** — orders and order items (profile order grid + detail modal)
- **content** — Home hero and Select Size copy/images (singleton rows, editable from Django Admin)

## Setup

```bash
cd arborn-be
source venv/bin/activate        # venv already created
cp .env.example .env            # fill in DB creds, GOOGLE_CLIENT_ID, etc.
```

Create the Postgres database and user referenced in `.env` (adjust names/password to match):

```bash
sudo -u postgres psql -c "CREATE DATABASE arborn;"
sudo -u postgres psql -c "CREATE USER arborn WITH PASSWORD 'yourpassword';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE arborn TO arborn;"
```

**Migrations have deliberately not been run yet** — review the models in each
app's `models.py` first, adjust anything you want changed, then run:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Admin panel: `http://localhost:8000/admin/`
API root: `http://localhost:8000/api/`

## Endpoints

| Method | Path | Auth |
|---|---|---|
| POST | `/api/auth/google/` | — |
| POST | `/api/auth/otp/request/` | — |
| POST | `/api/auth/otp/verify/` | — |
| POST | `/api/auth/refresh/` | — |
| GET/PATCH | `/api/profile/` | JWT |
| GET | `/api/categories/` | — |
| GET | `/api/products/` | — |
| GET | `/api/products/{slug}/` | — |
| GET | `/api/orders/` | JWT |
| GET | `/api/orders/{id}/` | JWT |
| GET | `/api/content/home/` | — |
| GET | `/api/content/select-size/` | — |

Send the JWT as `Authorization: Bearer <access>`.

## Notes

- `GOOGLE_CLIENT_ID` in `.env` should match the frontend's
  `NEXT_PUBLIC_GOOGLE_CLIENT_ID` — the backend verifies incoming Google ID
  tokens were issued for that same app.
- Product/category/content images use `ImageField` (uploaded via Django
  Admin) — set `MEDIA_URL`/`MEDIA_ROOT` storage (e.g. S3) before production.
- CORS is restricted to `CORS_ALLOWED_ORIGINS` in `.env` — add your real
  frontend domain when it changes (e.g. moving off GitHub Pages to EC2).
