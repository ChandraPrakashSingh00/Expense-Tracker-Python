# Spec: Registration

## Overview

This step lets a visitor create a Spendly account from the existing `/register` page. `register.html` already posts `name`, `email` and `password` to `/register` and shows an `{{ error }}` block. However, the route only accepts GET today, so submitting the form fails with 405 Method Not Allowed. Step 1 created the `users` table and the `get_db()` connection helper, and registration is the first feature to write real data through them. It stores the new user with a hashed password, rejects invalid or duplicate sign-ups with a clear message, and sends the user to the sign-in page with a success message. The step also sets the app's `secret_key`. Flashed messages need it now, and Step 3 (login and logout) needs it for sessions.

## Depends on

- **Step 1 — Database Setup** (`.claude/specs/01-databse-setup.md`). Registration needs:
  - the `users` table with `email TEXT NOT NULL UNIQUE`
  - `get_db()`
  - `init_db()` running at app startup

Step 3 (login and logout) will depend on this step.

## Routes

No new routes. The existing `/register` route is extended:

- `GET /register`: render the empty registration form. Public.
- `POST /register`: validate the form and create the user.
  - On success, redirect to `/login` and flash a success message.
  - On failure, re-render `register.html` with `error=` set.
  - Public.

The URL and the view function name `register` must stay the same, because `base.html`, `login.html` and `landing.html` link to it with `url_for('register')`.

## Database changes

No database changes. The `users` table in `database/db.py` already has every column registration needs: `id`, `name`, `email` (UNIQUE), `password_hash`, and `created_at` (defaults to `datetime('now')`).

Two helper functions are added to `database/db.py`. They are code only and do not change the schema:

- `get_user_by_email(email)` returns the matching `sqlite3.Row` or `None`. The query is `SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?`. Step 3 will reuse it for login.
- `create_user(name, email, password)`:
  - Hashes the password with `generate_password_hash`, which is already imported in `db.py`.
  - Inserts the row, commits, and returns the new `id` (`cursor.lastrowid`).
  - Closes the connection in `finally`.
  - Lets `sqlite3.IntegrityError` propagate on a duplicate email.

## Templates

- **Create:** none.
- **Modify `templates/register.html`:** after a failed submission, keep what the user typed.
  - Add `value="{{ name or '' }}"` to the name input and `value="{{ email or '' }}"` to the email input.
  - Never fill the password back in.
- **Modify `templates/login.html`:** show the one-time success message after registration.
  - Place it inside `.auth-card`, above the existing `{% if error %}` block.
  - Render it with `{% with messages = get_flashed_messages(category_filter=["success"]) %}`, one `<div class="auth-success">` per message.

## Files to change

- `app.py`
  - Import `os`, plus `flash`, `redirect`, `request` and `url_for` from Flask.
  - Set `app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")` right after `app = Flask(__name__)`.
  - Change the `register` route to `methods=["GET", "POST"]` and add the POST handling.
- `database/db.py`: add `get_user_by_email()` and `create_user()`.
- `templates/register.html`: keep entered `name` and `email` on error.
- `templates/login.html`: show the flashed success message.
- `static/css/style.css`: add a `.auth-success` rule in the "Auth pages" section, directly below `.auth-error`.
  - Mirror `.auth-error`'s layout.
  - Use `var(--accent-light)` for the background, `var(--accent)` for the text, and `var(--radius-sm)` for the corners.

## Files to create

None.

## New dependencies

No new dependencies. The step uses the following, all already installed or in the standard library:

- `werkzeug.security`
- `sqlite3`
- `re`
- `os`

## Rules for implementation

- **No new structure.** Keep the single-module layout: no app factory, no blueprints, no ORM.
- **Parameterised SQL only.** Every query uses `?` placeholders. SQL strings never use f-strings, `%` or `.format()`.
- **Password storage.** Store only the result of `werkzeug.security.generate_password_hash`. Never store, log, print or flash the plaintext password.
- **Normalise input before validating or storing it.**
  - `name`: `.strip()`
  - `email`: `.strip().lower()`, so that `Demo@Spendly.com` and `demo@spendly.com` count as the same account.
  - `password`: leave it exactly as submitted, with no stripping.
- **Server-side validation.** Check these in this order and stop at the first failure. Browser `required` and `type="email"` checks are not enough on their own.

  | # | Check | Error message |
  |---|-------|---------------|
  | 1 | Any field is empty after normalising | "Please fill in all fields." |
  | 2 | Email doesn't fully match `^[^@\s]+@[^@\s]+\.[^@\s]+$` | "Please enter a valid email address." |
  | 3 | Password is shorter than 8 characters | "Password must be at least 8 characters." |
  | 4 | `get_user_by_email(email)` returns a row | "An account with this email already exists." |

- **Duplicate-email race.** Also catch `sqlite3.IntegrityError` from `create_user()` and show the same duplicate-email error. This covers two sign-ups with the same email arriving at the same time.
- **On failure:** `render_template("register.html", error=..., name=name, email=email)`.
- **On success:**
  - `flash("Account created. Please sign in.", "success")`, then `redirect(url_for("login"))` (Post/Redirect/Get).
  - Do **not** log the user in or write to `session`. That is Step 3.
- **Out of scope.** Do not touch `base.html`'s navbar, the `/login` route logic, or any placeholder route.
- **Styling.** Reuse the existing CSS tokens and never hardcode colours. The one exception is a border shade for `.auth-success`, which may mirror how `.auth-error` uses `#f5c6c2`.
- **Secret key.** The hardcoded fallback is for local development only. Don't commit a real key.

## Definition of done

Run `python app.py` and use http://localhost:5001.

- [ ] The app starts with no errors, and `/`, `/login`, `/terms-and-conditions` and `/privacy-policy` still render.
- [ ] `GET /register` shows the form exactly as before, with empty fields.
- [ ] A valid sign-up (for example, name `Test User`, email `Test.User@Example.com`, password `password123`) does all of the following:
  - redirects to `/login`
  - shows a green "Account created. Please sign in." banner there
  - creates a new `users` row with email `test.user@example.com`, where `password_hash` is not the plaintext password and `created_at` is set
- [ ] `check_password_hash(row["password_hash"], "password123")` returns `True` for the new row.
- [ ] Reloading `/login` after that redirect does not show the success banner again, and it does not resubmit the form.
- [ ] Signing up again with `DEMO@spendly.com`, which differs only in case from the seeded user, does all of the following:
  - shows "An account with this email already exists."
  - adds no row
  - keeps the name and email fields filled in, with the password field empty
- [ ] A 7-character password shows "Password must be at least 8 characters." and adds no row.
- [ ] Submitting a name of only spaces shows "Please fill in all fields." and adds no row.
- [ ] Sending `curl -X POST -d "name=A&email=not-an-email&password=password123" http://localhost:5001/register` returns the form with "Please enter a valid email address." and adds no row.
- [ ] The error and success banners use the existing auth-card styling, and they are readable on a phone-width screen.
- [ ] Searching `app.py` and `database/db.py` finds no f-strings, `%` or `.format()` inside SQL strings.
