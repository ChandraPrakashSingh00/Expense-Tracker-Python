# Plan: Step 1 — Database Setup

## Context

`database/db.py` currently holds only comments, and `app.py` doesn't touch a database. Every later step (auth, profile, add/edit/delete expense) needs a data layer. This step turns the spec in `.claude/specs/01-databse-setup.md` into a working SQLite layer: `get_db()`, `init_db()` and `seed_db()`. It also wires them into `app.py` so the DB file, schema and demo data exist as soon as the app starts. No routes change.

## Decisions

- **DB file:** `expense_tracker.db` in the repo root. The spec allows this name or `spendly.db`. This one is already in `.gitignore` and matches CLAUDE.md, so no ignore change is needed.
- **Path resolution:** build the path from `__file__`, not the working directory, so running `python app.py`, `flask run` or `pytest` from anywhere uses the same file. Keep it in a module-level `DB_PATH` so tests can monkeypatch it later.
- **`CATEGORIES` constant:** a tuple in `db.py` holding the 7 fixed categories. The seed uses it now, and Steps 7–8 (add/edit forms) can import it later. No SQL `CHECK` constraint, because SQLite can't alter constraints later and the spec doesn't ask for one.
- **Startup hook:** call `init_db()` and `seed_db()` at module level in `app.py`, inside `with app.app_context():`. That way they run under `python app.py`, `flask run` and pytest's import of `app`. The debug reloader runs it twice, which is harmless because both functions are idempotent.

## Changes

### 1. `database/db.py`: replace the stub

- Imports: `os`, `sqlite3`, `datetime.date`, `werkzeug.security.generate_password_hash`.
- `DB_PATH = os.path.join(<repo root>, "expense_tracker.db")`, where repo root is `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`.
- `CATEGORIES = ("Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other")`.
- **`get_db()`**: `sqlite3.connect(DB_PATH)`, set `conn.row_factory = sqlite3.Row`, run `PRAGMA foreign_keys = ON`, return `conn`.
- **`init_db()`**: open a connection and run one static `executescript` with both `CREATE TABLE IF NOT EXISTS` statements, matching the spec exactly:
  - `users`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `name TEXT NOT NULL`, `email TEXT NOT NULL UNIQUE`, `password_hash TEXT NOT NULL`, `created_at TEXT DEFAULT (datetime('now'))`
  - `expenses`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `user_id INTEGER NOT NULL REFERENCES users(id)`, `amount REAL NOT NULL`, `category TEXT NOT NULL`, `date TEXT NOT NULL`, `description TEXT`, `created_at TEXT DEFAULT (datetime('now'))`
  - Close the connection in `finally`.
- **`seed_db()`**:
  - Return early if `SELECT 1 FROM users LIMIT 1` returns a row.
  - Insert the demo user with a parameterized `INSERT`: `("Demo User", "demo@spendly.com", generate_password_hash("demo123"))`. Take `cursor.lastrowid` as `user_id`.
  - Build 8 expenses dated in the current month as `date.today().replace(day=min(d, today.day)).isoformat()` (YYYY-MM-DD). The `min` keeps early-month runs from producing future dates. Every category appears at least once, and Food appears twice:

    | day | category | amount (₹) | description |
    |---|---|---|---|
    | 1 | Food | 450.00 | Groceries |
    | 3 | Transport | 120.00 | Metro card recharge |
    | 6 | Bills | 1850.00 | Electricity bill |
    | 9 | Health | 600.00 | Pharmacy |
    | 12 | Entertainment | 499.00 | Movie tickets |
    | 15 | Shopping | 2199.00 | New shoes |
    | 19 | Food | 320.50 | Dinner with friends |
    | 23 | Other | 250.00 | Gift |

  - Insert them with `executemany("INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)", rows)`.
  - Commit once so the user and expenses land atomically, then close in `finally`.
- All SQL uses `?` placeholders and no f-strings or `%` formatting. Errors such as `IntegrityError` are not swallowed, so they surface clearly.

### 2. `app.py`: add imports and the startup call

- Add `from database.db import get_db, init_db, seed_db` below the Flask import. The spec asks for `get_db` to be imported too, although nothing uses it yet.
- Right after `app = Flask(__name__)`:
  ```python
  with app.app_context():
      init_db()
      seed_db()
  ```
- Leave every route untouched.

## Verification

Run from the repo root with the venv activated (`.\venv\Scripts\Activate.ps1`):

1. **Fresh start:** delete any existing `expense_tracker.db`, then run `python app.py`. The server should start on :5001 with no errors, `expense_tracker.db` should appear in the repo root, and `/`, `/login` and `/register` should still render.
2. **Schema and seed check:** run a short `python -c` script that imports `database.db` and checks:
   - Both tables exist (`sqlite_master`), and `PRAGMA table_info` matches the spec.
   - There is 1 user with email `demo@spendly.com`, and `check_password_hash(row["password_hash"], "demo123")` is `True`.
   - There are 8 expenses, the distinct categories equal all 7 of `CATEGORIES`, and every date matches `YYYY-MM-DD` in the current month.
   - `row["email"]` works (proves `Row` access), and `PRAGMA foreign_keys` returns `1`.
3. **Idempotency:** call `init_db()` and `seed_db()` again, or restart the app. There should still be 1 user and 8 expenses, with no errors.
4. **Constraints:** inserting a second user with `demo@spendly.com` raises `sqlite3.IntegrityError` (UNIQUE), and inserting an expense with `user_id=9999` raises `sqlite3.IntegrityError` (FOREIGN KEY).
5. **Done-criteria sweep:** grep `database/db.py` for `f"`, `.format(` and `%` inside SQL strings. There should be none.
