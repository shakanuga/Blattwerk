"""Anmeldung über Pocket ID. Startet den echten Server in einem Thread."""
import http.client
import os
import sys
import threading
import urllib.parse
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "app"))
sys.path.insert(0, str(Path(__file__).parent))
from fake_pocketid import FakePocketID  # noqa: E402


@pytest.fixture()
def srv(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import importlib
    import server
    importlib.reload(server)
    server.init_db()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield server, httpd.server_address[1]
    httpd.shutdown()


def req(port, path, method="GET", headers=None, body=None):
    c = http.client.HTTPConnection("127.0.0.1", port)
    c.request(method, path, body=body, headers=headers or {})
    r = c.getresponse()
    r.read()
    return r


def cookies(res):
    out = {}
    for k, v in res.getheaders():
        if k.lower() == "set-cookie":
            name, _, rest = v.partition("=")
            out[name] = rest.split(";")[0]
    return out


def test_without_oidc_everything_is_open(srv):
    server, port = srv
    assert req(port, "/api/plants").status == 200


def test_login_flow(srv):
    server, port = srv
    fake = FakePocketID()
    server.OIDC = server.pocketid.PocketID(fake.env(), opener=fake)
    assert req(port, "/api/plants").status == 401
    r = req(port, "/pflanze/3")
    assert r.status == 302 and r.getheader("Location") == "/auth/pocketid?next=/pflanze/3"
    assert req(port, "/manifest.webmanifest").status == 200
    r = req(port, "/auth/pocketid?next=/pflanze/3", headers={"X-Forwarded-Proto": "https", "Host": "pflanzen.test"})
    pending = cookies(r)["oidc_pending"]
    redirect, params = fake.login(r.getheader("Location"))
    assert redirect == "https://pflanzen.test/auth/pocketid/zurueck"
    r = req(port, "/auth/pocketid/zurueck?" + urllib.parse.urlencode(params),
            headers={"Cookie": f"oidc_pending={pending}", "X-Forwarded-Proto": "https", "Host": "pflanzen.test"})
    assert r.status == 302 and r.getheader("Location") == "/pflanze/3"
    session = cookies(r)["blattwerk_session"]
    assert "Secure" in r.getheader("Set-Cookie")
    ok = {"Cookie": f"blattwerk_session={session}", "Host": "pflanzen.test"}
    assert req(port, "/api/plants", headers=ok).status == 200
    bad = {**ok, "Origin": "https://boese.test", "Content-Type": "application/json"}
    assert req(port, "/api/plants", "POST", bad, b"{}").status == 403
    assert req(port, "/api/plants", headers={"Cookie": "blattwerk_session=" + session + "x"}).status == 401


def test_wrong_state_and_group(srv):
    server, port = srv
    fake = FakePocketID()
    server.OIDC = server.pocketid.PocketID(fake.env(OIDC_ALLOWED_GROUPS="admins"), opener=fake)
    r = req(port, "/auth/pocketid")
    pending = cookies(r)["oidc_pending"]
    _, params = fake.login(r.getheader("Location"))
    r = req(port, "/auth/pocketid/zurueck?" + urllib.parse.urlencode(params), headers={"Cookie": f"oidc_pending={pending}"})
    assert r.status == 403 and "blattwerk_session" not in cookies(r)
