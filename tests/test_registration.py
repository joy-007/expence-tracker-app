import pytest
from werkzeug.security import check_password_hash

import database.db as db_module

VALID = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "password": "password123",
}
DUPLICATE_MSG = "An account with that email already exists."


def _users():
    conn = db_module.get_db()
    try:
        return conn.execute("SELECT * FROM users ORDER BY id").fetchall()
    finally:
        conn.close()


def _post(client, **overrides):
    return client.post("/register", data={**VALID, **overrides})


# ------------------------------------------------------------------ #
# GET and startup                                                     #
# ------------------------------------------------------------------ #

def test_get_register_renders_form_without_error(client):
    resp = client.get("/register")
    assert resp.status_code == 200
    assert b"<form" in resp.data
    assert b"auth-error" not in resp.data


def test_seeded_demo_user_exists(client):
    assert [u["email"] for u in _users()] == ["demo@spendly.com"]


def test_put_not_allowed(client):
    assert client.put("/register").status_code == 405


# ------------------------------------------------------------------ #
# Success path                                                        #
# ------------------------------------------------------------------ #

def test_valid_post_redirects_to_login(client):
    resp = _post(client)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/login")


def test_valid_post_creates_row(client):
    _post(client)
    users = _users()
    assert len(users) == 2
    assert users[-1]["name"] == "Jane Doe"
    assert users[-1]["email"] == "jane@example.com"


def test_name_stripped_and_email_stripped_and_lowercased(client):
    resp = _post(client, name="  Jane  ", email="  New@Example.COM ")
    assert resp.status_code == 302
    row = _users()[-1]
    assert row["name"] == "Jane"
    assert row["email"] == "new@example.com"


def test_password_is_hashed(client):
    _post(client)
    stored = _users()[-1]["password_hash"]
    assert stored != VALID["password"]
    assert VALID["password"] not in stored
    assert check_password_hash(stored, VALID["password"])
    assert not check_password_hash(stored, "wrong-password")


# ------------------------------------------------------------------ #
# Duplicate email                                                     #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "email", ["demo@spendly.com", "DEMO@Spendly.COM", "  demo@spendly.com "]
)
def test_duplicate_email_rejected(client, email):
    resp = _post(client, email=email)
    assert resp.status_code == 400
    assert DUPLICATE_MSG.encode() in resp.data
    assert len(_users()) == 1


# ------------------------------------------------------------------ #
# Validation                                                          #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_rejected(client, name):
    resp = _post(client, name=name)
    assert resp.status_code == 400
    assert b"Name is required." in resp.data
    assert len(_users()) == 1


@pytest.mark.parametrize(
    "email",
    [
        "notanemail",
        "@x.com",
        "a@",
        "a@b",
        "a b@x.com",
        "a@@x.com",
        "a@x.",
        "a@.com",
        "",
    ],
)
def test_invalid_email_rejected(client, email):
    resp = _post(client, email=email)
    assert resp.status_code == 400
    assert b"valid email" in resp.data
    assert len(_users()) == 1


def test_password_minimum_length(client):
    assert _post(client, password="a" * 7).status_code == 400
    assert len(_users()) == 1
    assert _post(client, password="a" * 8).status_code == 302
    assert len(_users()) == 2


def test_length_caps(client):
    assert _post(client, name="a" * 101).status_code == 400
    assert _post(client, email="a" * 250 + "@x.com").status_code == 400
    assert _post(client, password="p" * 129).status_code == 400
    assert len(_users()) == 1
    assert _post(client, name="a" * 100).status_code == 302
    assert len(_users()) == 2


# ------------------------------------------------------------------ #
# Re-rendered form                                                    #
# ------------------------------------------------------------------ #

def test_failed_post_keeps_name_and_email_but_not_password(client):
    secret = "Zq9!unique-secret"
    resp = _post(client, name="Jane", email="bad@", password=secret)
    assert resp.status_code == 400
    assert b'value="Jane"' in resp.data
    assert b'value="bad@"' in resp.data
    assert secret.encode() not in resp.data


def test_echoed_values_are_escaped(client):
    payload = "<script>alert(1)</script>"
    resp = _post(client, name=payload, email="bad@")
    assert resp.status_code == 400
    assert payload.encode() not in resp.data
    assert b"&lt;script&gt;" in resp.data
