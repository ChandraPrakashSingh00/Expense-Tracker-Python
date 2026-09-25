# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Windows / PowerShell, using the local `venv`:

```powershell
.\venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
python app.py                        # dev server with debug reload at http://localhost:5001 (not 5000)
pytest                               # run all tests
pytest path/to/test_file.py::test_name   # run a single test
```

There are no tests yet. `pytest-flask` is installed and expects an `app` fixture in a `conftest.py`. That fixture can return the module-level `app` from `app.py`.

## Architecture

**Spendly** is the product name used in the UI for this repo. It's an expense tracker for Indian users, with amounts in ₹. It is a server-rendered Flask app with no frontend build step.

- **Single module, no app factory or blueprints.** `app.py` defines a global `app` and every route. Templates link with `url_for('<view function name>')`, so renaming a view function breaks the nav, footer and auth links.
- **Scaffold that gets built in numbered steps.** The placeholder routes in `app.py` return strings like "coming in Step 7". Their step numbers show the planned order: DB setup (Step 1), logout (3), profile (4), add/edit/delete expense (7–9). When you implement a step, replace the placeholder in place and keep the URL.
- **Database layer is only specified so far.** `database/db.py` holds nothing but comments describing the contract: `get_db()` returns a SQLite connection with `row_factory` set and foreign keys enabled; `init_db()` uses `CREATE TABLE IF NOT EXISTS`; `seed_db()` inserts dev sample data. The DB file is expected to be `expense_tracker.db` in the repo root (already in `.gitignore`). Nothing in `app.py` imports the database yet.
- **The auth templates are ahead of the routes.** `login.html` and `register.html` POST to `/login` and `/register` and render an `{{ error }}` variable, but those routes only accept GET today. Wiring them up needs `methods=["GET", "POST"]` and must pass `error=` on failure. No `secret_key` is set, and Flask sessions need one before login and logout can work. `werkzeug.security` is available for password hashing.
- **Templates.** Every page extends `templates/base.html`, which provides the `title`, `head`, `content` and `scripts` blocks. The navbar always shows Sign in / Get started because it doesn't check whether anyone is logged in yet. Page-specific JS goes inline in `{% block scripts %}`, as in the video modal in `landing.html`. `static/js/main.js` loads on every page and is currently empty.
- **Styling.** All CSS lives in `static/css/style.css`, split into sections by comment banners (Navbar, Hero, Buttons, Auth pages, Legal pages, Footer, Responsive, …). Design tokens are CSS variables on `:root` (`--ink*`, `--paper*`, `--accent`, `--accent-2`, `--danger`, `--radius-*`, `--font-display`/`--font-body`). Reuse those tokens rather than hardcoding colors. Add new styles under the matching section, and add responsive overrides in the media-query blocks at the end of the file.
