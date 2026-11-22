import pytest
from flask import session

import database.db as db_module

DEMO = {"email": "demo@spendly.com", "password": "demo123"}
INVALID_MSG = b"Invalid email or password."
REQUIRED_MSG = b"Email and password are required."


def _login(client, **overrides):
    return client.post("/login", data={**DEMO, **overrides})


# ------------------------------------------------------------------ #
# GET /login                                                          #
# ------------------------------------------------------------------ #

def test_get_login_renders_form_without_error(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"<form" in resp.data
    assert b'action="/login"' in resp.data
    assert b"auth-error" not in resp.data


# ------------------------------------------------------------------ #
# Successful login                                                    #
# ------------------------------------------------------------------ #

def test_demo_login_redirects_and_sets_only_user_id(client):
    with client:
        resp = _login(client)
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")
        assert dict(session) == {"user_id": 1}
    assert "session=" in resp.headers.get("Set-Cookie", "")


def test_navbar_shows_user_after_login(client):
    resp = _login(client)
    page = client.get("/")
    assert page.status_code == 200
    assert b"Demo User" in page.data
    assert b"Sign out" in page.data
    assert b"Sign in" not in page.data
    assert b"Get started" not in page.data
    assert resp.status_code == 302


@pytest.mark.parametrize(
    "email", ["  DEMO@Spendly.com ", "DEMO@SPENDLY.COM", "demo@spendly.com\t"]
)
def test_email_is_case_and_whitespace_insensitive(client, email):
    with client:
        resp = _login(client, email=email)
        assert resp.status_code == 302
        assert session.get("user_id") == 1


def test_registered_user_can_log_in(client):
    reg = client.post(
        "/register",
        data={"name": "Jane", "email": "jane@example.com", "password": "pass12345"},
    )
    assert reg.status_code == 302
    with client:
        resp = _login(client, email="jane@example.com", password="pass12345")
        assert resp.status_code == 302
        assert session.get("user_id") == 2
    assert b"Jane" in client.get("/").data


def test_login_clears_pre_existing_session_data(client):
    with client.session_transaction() as sess:
        sess["junk"] = "stale"
    with client:
        _login(client)
        assert dict(session) == {"user_id": 1}


# ------------------------------------------------------------------ #
# Failed login                                                        #
# ------------------------------------------------------------------ #

def test_wrong_password_rejected(client):
    with client:
        resp = _login(client, password="wrong-password")
        assert resp.status_code == 400
        assert INVALID_MSG in resp.data
        assert "user_id" not in session


def test_unknown_email_gets_same_message(client):
    with client:
        resp = _login(client, email="nobody@example.com")
        assert resp.status_code == 400
        assert INVALID_MSG in resp.data
        assert "user_id" not in session


@pytest.mark.parametrize(
    "email,password",
    [("", "demo123"), ("demo@spendly.com", ""), ("", ""), ("   ", "demo123")],
)
def test_missing_fields_rejected(client, email, password):
    with client:
        resp = _login(client, email=email, password=password)
        assert resp.status_code == 400
        assert REQUIRED_MSG in resp.data
        assert "user_id" not in session


def test_failed_login_keeps_email_but_not_password(client):
    secret = "Zq9!unique-secret"
    resp = _login(client, email="demo@spendly.com", password=secret)
    assert resp.status_code == 400
    assert b'value="demo@spendly.com"' in resp.data
    assert secret.encode() not in resp.data


def test_echoed_email_is_escaped(client):
    payload = "<script>alert(1)</script>"
    resp = _login(client, email=payload)
    assert resp.status_code == 400
    assert payload.encode() not in resp.data
    assert b"&lt;script&gt;" in resp.data


def test_password_is_not_stripped(client):
    resp = _login(client, password=" demo123 ")
    assert resp.status_code == 400
    assert INVALID_MSG in resp.data


# ------------------------------------------------------------------ #
# Logout                                                              #
# ------------------------------------------------------------------ #

def test_logout_clears_session_and_restores_navbar(client):
    _login(client)
    with client:
        resp = client.get("/logout")
        assert resp.status_code == 302
        assert resp.headers["Location"].endswith("/")
        assert dict(session) == {}
    page = client.get("/")
    assert b"Sign in" in page.data
    assert b"Get started" in page.data
    assert b"Sign out" not in page.data


def test_logout_when_anonymous_redirects(client):
    resp = client.get("/logout")
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


# ------------------------------------------------------------------ #
# Logged-in redirects                                                 #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize(
    "method,path",
    [("get", "/login"), ("post", "/login"), ("get", "/register"), ("post", "/register")],
)
def test_logged_in_user_redirected_from_auth_pages(client, method, path):
    _login(client)
    resp = getattr(client, method)(path)
    assert resp.status_code == 302
    assert resp.headers["Location"].endswith("/")


# ------------------------------------------------------------------ #
# Stale session                                                       #
# ------------------------------------------------------------------ #

@pytest.mark.parametrize("path", ["/", "/terms", "/privacy"])
def test_stale_user_id_treated_as_logged_out(client, path):
    with client.session_transaction() as sess:
        sess["user_id"] = 9999
    with client:
        resp = client.get(path)
        assert resp.status_code == 200
        assert b"Sign in" in resp.data
        assert "user_id" not in session


# ------------------------------------------------------------------ #
# Footer and DB helpers                                               #
# ------------------------------------------------------------------ #

def test_footer_links_render(client):
    resp = client.get("/")
    assert b'href="/terms"' in resp.data
    assert b'href="/privacy"' in resp.data
    assert client.get("/terms").status_code == 200
    assert client.get("/privacy").status_code == 200


def test_get_user_by_email_is_injection_safe(app):
    assert db_module.get_user_by_email("' OR 1=1 --") is None
    assert db_module.get_user_by_email("DEMO@spendly.com")["id"] == 1


def test_get_user_by_id_excludes_password_hash(app):
    user = db_module.get_user_by_id(1)
    assert user["name"] == "Demo User"
    assert "password_hash" not in user.keys()
    assert db_module.get_user_by_id(None) is None
    assert db_module.get_user_by_id(9999) is None


def test_verify_user(app):
    assert db_module.verify_user("demo@spendly.com", "demo123")["id"] == 1
    assert db_module.verify_user("demo@spendly.com", "nope") is None
    assert db_module.verify_user("ghost@example.com", "demo123") is None
