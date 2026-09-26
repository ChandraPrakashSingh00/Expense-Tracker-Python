
## Description

Create a single dummy user in the database.

## Allowed Tools

- Read
- Bash(`python3:*`)

---

## Instructions

Read `database/db.py` to understand the `users` table schema and the `get_db()` helper.

Then write and run a Python script using Bash that:

### 1. Generates a realistic random Indian user

Use your own knowledge of common Indian names across regions.

- **Name:** A realistic Indian first + last name.
- **Email:** Derived from the name with a random 2–3 digit number suffix.
  - Example: `rahul.sharma91@gmail.com`
- **Password:** `"password123"` hashed with the Werkzeug `generate_password_hash`.
- **created_at:** Current datetime.

### 2. Checks email uniqueness

Check if the generated email already exists in the `users` table.

If it does, regenerate the email until a unique email is found.

### 3. Inserts the user

Insert the generated user into the database using the same `get_db()` pattern found in `db.py`.

### 4. Prints confirmation

Print a confirmation containing:

- `id`
- `name`
- `email`

