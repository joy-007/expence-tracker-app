# Spec: Login and Logout

## Overview
Step 3 makes sign-in and sign-out work. Today `GET /login` renders a form that posts nowhere, and `/logout` is a stub that returns a raw string. This step adds a `POST /login` handler that looks the user up by email, verifies the password against the stored werkzeug hash, and stores the user's id in the Flask session. `/logout` clears the session and redirects to the landing page. The navbar becomes session-aware, showing "Sign in / Get started" to visitors and the user's name plus "Sign out" to logged-in users. Registration (Step 2) created users but nobody could sign in; this step is the prerequisite for the profile page (Step 4) and all expense routes (Steps 7–9), which need to know who is logged in.

## Depends on
- **Step 1 — Database setup:** `get_db()`, the `users` table, the seeded demo user (`demo@spendly.com` / `demo123`).
- **Step 2 — Registration:** `create_user()` and the `/register` flow, which redirects to `/login` on success.

## Routes
- `GET /login` — already implemented; renders the sign-in form. If the visitor is already logged in, redirect to `landing` — public
- `POST /login` — validates input, verifies credentials, starts the session and redirects to `landing` on success, or re-renders the form with an error and HTTP 400 on failure — public
- `GET /logout` — clears the session and redirects to `landing`. Replaces the Step 3 stub. Safe to call when not logged in (just redirects) — public (no-op if anonymous)
- `GET /register` — small change only: if the visitor is already logged in, redirect to `landing`. Registration logic is unchanged — public

No other routes change. `/profile` and the expense routes remain stubs.

## Database changes
No schema changes. The `users` table already has `id`, `name`, `email` (UNIQUE), `password_hash`. Verified against `database/db.py`.

Two new helpers are added to `database/db.py`:
- `get_user_by_email(email)` — strips and lowercases `email`, selects the matching row from `users` with a parameterised query, returns a `sqlite3.Row` or `None`.
- `get_user_by_id(user_id)` — selects `id`, `name`, `email` from `users` by id with a parameterised query, returns a `sqlite3.Row` or `None`. Used to resolve the session user for templates.

Password verification (`check_password_hash`) happens in a small helper or in the route layer using the row returned above; no password hashes are ever sent to templates.

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — change the form action from the hardcoded `/login` to `{{ url_for('login') }}`. Keep the entered email after a failed attempt (`value="{{ email or '' }}"`). Never repopulate the password field. Leave the existing `{% if error %}` block as it is.
  - `templates/base.html` — make the navbar session-aware. When `current_user` is set, show the user's name and a "Sign out" link (`url_for('logout')`); otherwise keep "Sign in" and "Get started". Also replace the hardcoded footer links `/terms` and `/privacy` with `url_for('terms')` and `url_for('privacy')`, per the CLAUDE.md rule against hardcoded URLs.

## Files to change
- `app.py`
  - Set `app.secret_key` from the `SECRET_KEY` environment variable, falling back to a clearly-named development default so the app still starts with zero setup.
  - Import `session`, `check_password_hash` (from `werkzeug.security`), `get_user_by_email`, `get_user_by_id`.
  - Add `POST` to `/login` and implement the handler.
  - Replace the `/logout` stub with the real implementation.
  - Add a `@app.context_processor` that exposes `current_user` (looked up via `get_user_by_id(session.get("user_id"))`, or `None`) to every template. If the session holds an id for a user that no longer exists, clear the session.
  - Redirect already-logged-in visitors away from `/login` and `/register`.
- `database/db.py` — add `get_user_by_email()` and `get_user_by_id()`.
- `templates/login.html` — see above.
- `templates/base.html` — see above.
- `static/css/style.css` — add styles for the logged-in navbar state (user name and sign-out link) using existing CSS variables.
- `CLAUDE.md` — update the "Implemented vs stub routes" table: `/login` handles GET and POST, `/logout` is implemented (Step 3).

## Files to create
- `tests/test_login_logout.py` — tests listed under Definition of done. Tests must point the app at a temporary database file, not `expense_tracker.db` (follow the approach used in `tests/test_registration.py` if it exists).

## New dependencies
No new dependencies. `session` is part of Flask and `check_password_hash` is in `werkzeug.security`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only (`?` placeholders). No f-strings or `%` formatting in SQL
- Passwords hashed with werkzeug. Verify with `check_password_hash`; never compare plaintext, never log or echo passwords
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Route functions stay thin: read the form, call the DB helper, verify, then render or redirect. DB logic lives in `database/db.py`
- Use `url_for()` for every internal link and redirect target
- Store only the integer `user_id` in the session — nothing else (no name, email or hash)
- Call `session.clear()` before setting `session["user_id"]` on login so a pre-login session is never reused
- Use one generic error for both an unknown email and a wrong password: "Invalid email or password." Do not reveal which one failed
- Normalise the email (strip, lowercase) before lookup, so `Demo@Spendly.com ` signs in as the demo user
- Input handling: missing or empty email or password re-renders the form with "Email and password are required." Do not apply the registration length/format rules to login, since existing users must always be able to sign in
- Failed login returns HTTP 400 with `login.html` re-rendered; successful login returns a 302 redirect. Do not return bare strings
- `/logout` clears the whole session with `session.clear()` and always redirects, whether or not a user was logged in
- Do not accept or follow a `next` redirect parameter in this step (avoids open-redirect risk)
- Do not implement the profile page or protect any other route in this step (Step 4 onward)
- Do not change the port (5001) or the seed data

## Definition of done
- [ ] `GET /login` renders the sign-in form with no error
- [ ] Logging in as `demo@spendly.com` / `demo123` returns a 302 redirect to `/` and sets a session cookie
- [ ] After login, the navbar shows the user's name ("Demo User") and a "Sign out" link, and no longer shows "Sign in" or "Get started"
- [ ] Email is case- and whitespace-insensitive: `  DEMO@Spendly.com ` with the correct password also signs in
- [ ] A user created via `/register` can sign in immediately with the password they chose
- [ ] A wrong password shows "Invalid email or password." with HTTP 400 and does not start a session
- [ ] An unknown email shows the same "Invalid email or password." message with HTTP 400
- [ ] Empty email or empty password shows "Email and password are required." with HTTP 400
- [ ] After a failed login, the email field keeps its value and the password field is empty
- [ ] `GET /logout` while logged in clears the session, redirects to `/`, and the navbar shows "Sign in" / "Get started" again
- [ ] `GET /logout` while logged out redirects to `/` without error
- [ ] Visiting `/login` or `/register` while logged in redirects to `/`
- [ ] A session cookie referencing a user id that does not exist is treated as logged out and does not crash any page
- [ ] The session contains only `user_id` (verify in tests by inspecting `session`)
- [ ] The footer Terms and Privacy links are generated with `url_for()` and still work
- [ ] The app still starts on port 5001 and `init_db()` / `seed_db()` still run on startup without errors
- [ ] All new SQL uses parameterised queries (verify by reading `get_user_by_email()` and `get_user_by_id()`)
- [ ] `pytest` passes, and the tests do not modify `expense_tracker.db`
