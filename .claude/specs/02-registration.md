# Spec: Registration

## Overview
Step 2 turns the existing `/register` page into a working sign-up flow. Today `GET /register` renders the form, but submitting it does nothing. This step adds a `POST /register` handler that validates the name, email and password, stores a new user in the `users` table with a werkzeug password hash, and redirects to the login page on success. Duplicate emails and invalid input re-render the form with an error message. This is the first write path into the database, so it relies on the schema and helpers from Step 1 and is a prerequisite for login (Step 3) and everything that depends on a user (profile, expenses).

## Depends on
- **Step 1 — Database setup:** `get_db()`, `init_db()`, `seed_db()`, the `users` table with `UNIQUE` on `email`, and `PRAGMA foreign_keys = ON`.

## Routes
- `GET /register` — already implemented; renders the registration form (keep as-is, but pass through any `error` and previously entered values) — public
- `POST /register` — validates form input, creates the user, redirects to `/login` on success, or re-renders the form with an error on failure — public

## Database changes
No schema changes. The existing `users` table already has `name`, `email` (UNIQUE, NOT NULL), `password_hash` (NOT NULL) and `created_at`, which covers everything this step needs. Verified against `database/db.py`.

One new helper is added to `database/db.py`:
- `create_user(name, email, password)` — strips and lowercases `email`, hashes `password` with `generate_password_hash`, inserts a row into `users` using a parameterised query, commits, and returns the new user id. Lets `sqlite3.IntegrityError` propagate on a duplicate email so the route can handle it.

## Templates
- **Create:** none
- **Modify:**
  - `templates/register.html` — keep `name` and `email` values in the inputs after a failed submission (`value="{{ name or '' }}"`, `value="{{ email or '' }}"`). Do not repopulate the password field. Change the form action from the hardcoded `/register` to `{{ url_for('register') }}`. Leave the `{% if error %}` block as it is.

## Files to change
- `app.py` — change `/register` to accept `GET` and `POST`; add validation and the redirect; import `create_user`, `redirect`, `request`, `url_for`, and `sqlite3` (for `IntegrityError`).
- `database/db.py` — add `create_user()`.
- `templates/register.html` — preserve submitted values and show the error block (see above).

## Files to create
- `tests/test_registration.py` — tests for the success path, duplicate email, invalid input, and password hashing. Tests must point the app at a temporary database file, not `expense_tracker.db`.

## New dependencies
No new dependencies. `werkzeug.security` is already available through Flask.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders). No f-strings or `%` formatting in SQL
- Passwords hashed with werkzeug (`generate_password_hash`). Never store or log plaintext passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Route functions stay thin: read the form, validate, call `create_user()`, then render or redirect. DB logic lives in `database/db.py`
- Use `url_for()` for every internal link and redirect target (e.g. `redirect(url_for('login'))`)
- Validation failures re-render `register.html` with an `error` message and HTTP status 400. Do not return bare strings
- Validation rules:
  - `name`: required, stripped of surrounding whitespace, non-empty, maximum 100 characters
  - `email`: required, stripped and lowercased before storage, maximum 254 characters, no whitespace, exactly one `@` with text before it, and a dot inside the domain that is not its first or last character (so `a@b` is rejected)
  - `password`: required, minimum 8 and maximum 128 characters (not stripped)
- A duplicate email returns the form with the message "An account with that email already exists." and HTTP status 400
- Do not implement login, logout, or session handling in this step (Step 3)
- Do not change the port (5001) or the seed data

## Definition of done
- [ ] `GET /register` renders the registration form with no errors
- [ ] Submitting valid name, email and password redirects to `/login`
- [ ] After a successful registration, a new row exists in `users` with the submitted name and the lowercased email
- [ ] The stored `password_hash` is not the plaintext password and verifies with `check_password_hash`
- [ ] Submitting an email that already exists (including the demo user `demo@spendly.com`, in any letter case) shows "An account with that email already exists." and does not create a row
- [ ] Submitting an empty name shows a validation error and does not create a row
- [ ] Submitting an invalid email (e.g. `notanemail`, `a@b`, `a b@x.com`) shows a validation error and does not create a row
- [ ] Submitting a password shorter than 8 characters shows a validation error and does not create a row
- [ ] Submitting a name over 100 characters, an email over 254 characters, or a password over 128 characters shows a validation error and does not create a row
- [ ] After a failed submission, the name and email fields keep their entered values; the password field is empty
- [ ] Error responses return HTTP 400; a successful registration returns a 302 redirect
- [ ] The app still starts on port 5001 and `init_db()` / `seed_db()` still run on startup without errors
- [ ] All new SQL uses parameterised queries (verify by reading `create_user()`)
- [ ] `pytest` passes, and the tests do not modify `expense_tracker.db`
