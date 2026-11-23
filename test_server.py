import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

import server


class SharedOrdersTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        server.DATABASE = str(Path(self.tmp.name) / "orders.sqlite3")
        with server.connect() as db:
            for name in ("Alice", "Bob"):
                salt = "01" * 16
                db.execute("INSERT INTO users VALUES (?,?,?)", (name, salt, server.password_hash("test password 123", salt)))
        self.httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()
        self.tmp.cleanup()

    def request(self, method, path, body=None, cookie=None, header=True):
        conn = http.client.HTTPConnection("127.0.0.1", self.httpd.server_port)
        headers = {}
        if body is not None:
            headers["Content-Type"] = "application/json"
            if header:
                headers["X-WPFC-Request"] = "1"
            body = json.dumps(body)
        if cookie:
            headers["Cookie"] = cookie
        conn.request(method, path, body, headers)
        response = conn.getresponse()
        data = json.loads(response.read())
        result = response.status, data, response.getheader("Set-Cookie")
        conn.close()
        return result

    def login(self, name):
        status, _, cookie = self.request("POST", "/api/login", {"name": name, "password": "test password 123"})
        self.assertEqual(status, 200)
        return cookie.split(";")[0]

    def test_shared_history_conflicts_and_deletion(self):
        alice, bob = self.login("Alice"), self.login("Bob")
        order = {
            "id": "ORD-1", "submittedAt": "2026-01-01", "coachName": "Coach",
            "teamName": "U11", "totalItems": 1, "grandTotal": 10, "status": "pending",
            "items": [{"sku": "A", "name": "Shirt", "sizeLabel": "M", "quantity": 1,
                       "unitPrice": 10, "lineTotal": 10, "personalisations": []}]
        }
        self.assertEqual(self.request("PUT", "/api/orders", {"revision": 0, "orders": [order]}, alice)[0], 200)
        status, shared, _ = self.request("GET", "/api/orders", cookie=bob)
        self.assertEqual(status, 200)
        self.assertEqual(shared["orders"], [order])
        order["status"] = "approved"
        self.assertEqual(self.request("PUT", "/api/orders", {"revision": 0, "orders": [order]}, bob)[0], 409)
        self.assertEqual(self.request("PUT", "/api/orders", {"revision": shared["revision"], "orders": [order]}, bob)[0], 200)
        self.assertEqual(self.request("PUT", "/api/orders", {"revision": 2, "orders": []}, alice)[0], 200)
        _, history, _ = self.request("GET", "/api/orders", cookie=bob)
        self.assertEqual(history["orders"], [])
        self.assertEqual([(e["actor"], e["action"]) for e in history["audit"]],
                         [("Alice", "deleted"), ("Bob", "updated"), ("Alice", "created")])
        self.assertEqual(json.loads(history["audit"][0]["data"])["status"], "approved")

    def test_authentication_and_request_validation(self):
        self.assertEqual(self.request("GET", "/api/orders")[0], 401)
        self.assertEqual(self.request("POST", "/api/login", {"name": "Alice", "password": "wrong"})[0], 401)
        self.assertEqual(self.request("POST", "/api/login", {"name": "Alice", "password": "test password 123"}, header=False)[0], 403)
        alice = self.login("Alice")
        self.assertEqual(self.request("PUT", "/api/orders", {"revision": 0, "orders": [{"id": "'bad"}]}, alice)[0], 400)
        self.assertEqual(self.request("POST", "/api/logout", {}, alice)[0], 200)
        self.assertEqual(self.request("GET", "/api/orders", cookie=alice)[0], 401)


if __name__ == "__main__":
    unittest.main()
