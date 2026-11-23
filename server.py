#!/usr/bin/env python3
"""Single-instance order portal server. Keep the SQLite database on persistent storage."""

import argparse
from contextlib import contextmanager
import getpass
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATABASE = os.environ.get("WPFC_DATABASE", str(Path.home() / ".wpfc-orders.sqlite3"))
MAX_BODY = 2 * 1024 * 1024
ITERATIONS = 310000


@contextmanager
def connect():
    db = sqlite3.connect(DATABASE, timeout=30)
    try:
        os.chmod(DATABASE, 0o600)
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (name TEXT PRIMARY KEY, salt TEXT NOT NULL, password TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, name TEXT NOT NULL, expires INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                actor TEXT NOT NULL, action TEXT NOT NULL, order_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS metadata (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL);
            INSERT OR IGNORE INTO metadata VALUES (1, 0);
        """)
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()


def valid_order(order):
    if not isinstance(order, dict):
        return False
    if not isinstance(order.get("id"), str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", order["id"]):
        return False
    if order.get("status") not in ("pending", "approved", "sent"):
        return False
    if not all(isinstance(order.get(k), str) and len(order[k]) <= 1000 for k in ("coachName", "teamName", "submittedAt")):
        return False
    if not all(isinstance(order.get(k), (int, float)) and not isinstance(order[k], bool) and 0 <= order[k] <= 10000000 for k in ("totalItems", "grandTotal")):
        return False
    items = order.get("items")
    return isinstance(items, list) and len(items) <= 1000 and all(
        isinstance(item, dict)
        and all(isinstance(item.get(k), str) and len(item[k]) <= 1000 for k in ("sku", "name", "sizeLabel"))
        and all(isinstance(item.get(k), (int, float)) and not isinstance(item[k], bool) and 0 <= item[k] <= 10000000 for k in ("quantity", "unitPrice", "lineTotal"))
        and isinstance(item.get("personalisations", []), list)
        and all(isinstance(p, str) and len(p) <= 1000 for p in item.get("personalisations", []))
        for item in items
    )


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, data, headers=()):
        body = json.dumps(data, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for name, value in headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            raise ValueError("JSON required")
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_BODY:
            raise ValueError("Invalid request size")
        return json.loads(self.rfile.read(length), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))

    def user(self, db):
        try:
            cookie = cookies.SimpleCookie(self.headers.get("Cookie", ""))
            token = cookie["wpfc_session"].value
        except (KeyError, cookies.CookieError):
            return None
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        row = db.execute("SELECT name FROM sessions WHERE token=? AND expires>?", (token_hash, int(time.time()))).fetchone()
        return row["name"] if row else None

    def do_GET(self):
        if self.path in ("/", "/index.html", "/IMG_4899.png"):
            path = ROOT / ("index.html" if self.path == "/" else self.path[1:])
            body = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "image/png" if path.suffix == ".png" else "text/html; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)
            return
        with connect() as db:
            user = self.user(db)
            if not user:
                self.respond(401, {"error": "Sign in required"})
            elif self.path == "/api/session":
                self.respond(200, {"name": user})
            elif self.path == "/api/orders":
                db.execute("BEGIN")
                orders = [json.loads(row["data"]) for row in db.execute("SELECT data FROM orders ORDER BY rowid DESC")]
                revision = db.execute("SELECT revision FROM metadata WHERE id=1").fetchone()[0]
                audit = [dict(row) for row in db.execute("SELECT at, actor, action, order_id, data FROM audit ORDER BY id DESC")]
                self.respond(200, {"orders": orders, "revision": revision, "audit": audit})
            else:
                self.respond(404, {"error": "Not found"})

    def do_POST(self):
        self.mutate()

    def do_PUT(self):
        self.mutate()

    def mutate(self):
        # A non-simple header and JSON content type prevent cross-origin form requests.
        if self.headers.get("X-WPFC-Request") != "1":
            self.respond(403, {"error": "Invalid request"})
            return
        try:
            data = self.read_json()
            if not isinstance(data, dict):
                raise ValueError("Object required")
            with connect() as db:
                if self.path == "/api/login" and self.command == "POST":
                    name, password = data.get("name"), data.get("password")
                    if not isinstance(name, str) or not isinstance(password, str) or len(password) > 1024:
                        raise ValueError("Invalid credentials")
                    row = db.execute("SELECT * FROM users WHERE name=?", (name,)).fetchone()
                    computed = password_hash(password, row["salt"] if row else "00" * 16)
                    if not row or not hmac.compare_digest(computed, row["password"]):
                        self.respond(401, {"error": "Invalid name or password"})
                        return
                    token = secrets.token_urlsafe(32)
                    db.execute("DELETE FROM sessions WHERE expires<=?", (int(time.time()),))
                    db.execute("INSERT INTO sessions VALUES (?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), name, int(time.time()) + 43200))
                    db.commit()
                    secure = "; Secure" if os.environ.get("WPFC_SECURE_COOKIE") == "1" else ""
                    self.respond(200, {"name": name}, [("Set-Cookie", f"wpfc_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200{secure}")])
                    return
                user = self.user(db)
                if not user:
                    self.respond(401, {"error": "Sign in required"})
                    return
                if self.path == "/api/logout" and self.command == "POST":
                    cookie = cookies.SimpleCookie(self.headers.get("Cookie", ""))
                    db.execute("DELETE FROM sessions WHERE token=?", (hashlib.sha256(cookie["wpfc_session"].value.encode()).hexdigest(),))
                    db.commit()
                    self.respond(200, {}, [("Set-Cookie", "wpfc_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")])
                    return
                if self.path != "/api/orders" or self.command != "PUT":
                    self.respond(404, {"error": "Not found"})
                    return
                orders, revision = data.get("orders"), data.get("revision")
                if not isinstance(orders, list) or len(orders) > 10000 or not all(valid_order(o) for o in orders) or len({o["id"] for o in orders}) != len(orders) or type(revision) is not int:
                    raise ValueError("Invalid orders")
                db.execute("BEGIN IMMEDIATE")
                current = db.execute("SELECT revision FROM metadata WHERE id=1").fetchone()[0]
                if revision != current:
                    self.respond(409, {"error": "Orders changed on another device"})
                    return
                old = {row["id"]: json.loads(row["data"]) for row in db.execute("SELECT id, data FROM orders")}
                new = {o["id"]: o for o in orders}
                for order_id in old.keys() | new.keys():
                    before, after = old.get(order_id), new.get(order_id)
                    if before == after:
                        continue
                    action = "created" if before is None else "deleted" if after is None else "updated"
                    snapshot = json.dumps(after if after is not None else before, allow_nan=False)
                    db.execute("INSERT INTO audit (actor,action,order_id,data) VALUES (?,?,?,?)", (user, action, order_id, snapshot))
                    if after is None:
                        db.execute("DELETE FROM orders WHERE id=?", (order_id,))
                    else:
                        db.execute("INSERT INTO orders VALUES (?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data", (order_id, snapshot))
                db.execute("UPDATE metadata SET revision=revision+1 WHERE id=1")
                db.commit()
                self.respond(200, {"revision": current + 1})
        except (ValueError, TypeError, json.JSONDecodeError, OverflowError):
            self.respond(400, {"error": "Invalid request or order data"})


def main():
    parser = argparse.ArgumentParser(description="WPFC shared order portal")
    parser.add_argument("--add-user", metavar="NAME", help="create or reset an official account")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if args.add_user:
        name = args.add_user.strip()
        if not name or len(name) > 100:
            parser.error("Name must be 1–100 characters")
        password = getpass.getpass("Password (at least 12 characters): ")
        if len(password) < 12 or password != getpass.getpass("Confirm password: "):
            parser.error("Passwords must match and be at least 12 characters")
        salt = secrets.token_hex(16)
        with connect() as db:
            db.execute("INSERT OR REPLACE INTO users VALUES (?,?,?)", (name, salt, password_hash(password, salt)))
            db.execute("DELETE FROM sessions WHERE name=?", (name,))
        print("Official account saved.")
    else:
        with connect():
            pass
        ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
