"""Testes de integração locais do MVP, sem dependências externas."""
import http.cookiejar
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

import app


class VoLancharIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        app.DB_PATH = Path(cls.temp.name) / "test.db"
        app.init_db()
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.AppHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def setUp(self):
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def request(self, path, method="GET", data=None, expected=200):
        raw = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(self.base + path, data=raw, method=method,
                                     headers={"Content-Type": "application/json"})
        content_type = ""
        try:
            with self.opener.open(req, timeout=4) as response:
                status, body = response.status, response.read()
                content_type = response.headers.get("Content-Type", "")
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
            content_type = error.headers.get("Content-Type", "")
        self.assertEqual(status, expected, body.decode(errors="replace"))
        if body and "application/json" in content_type:
            return json.loads(body)
        return body

    def register(self, email, name="Teste"):
        return self.request("/api/register", "POST", {"name": name, "email": email, "password": "senha-segura-123"})["user"]

    def test_core_buyer_seller_journey_and_visibility(self):
        user = self.register("seller@example.com", "Vendedor")
        self.assertEqual(user["mode"], "buyer")
        points = self.request("/api/points")["points"]
        self.assertGreaterEqual(len(points), 1)
        point_id = points[0]["id"]

        self.request("/api/mode", "POST", {"mode": "seller"})
        self.request("/api/presence", "POST", {"point_id": point_id, "selling": True, "whatsapp": "5511999999999"})
        self.request("/api/products", "POST", {"name": "Suco", "description": "Natural", "price_cents": 650}, expected=201)

        sellers = self.request(f"/api/sellers?point={point_id}")["sellers"]
        self.assertEqual(len(sellers), 1)
        seller_id = sellers[0]["id"]
        product = sellers[0]["products"][0]
        self.assertEqual(product["price_cents"], 650)

        self.request(f"/api/products/{product['id']}", "PATCH", {"available": False})
        live_seller = self.request(f"/api/seller/{seller_id}")["seller"]
        self.assertEqual(live_seller["whatsapp"], "5511999999999")
        self.assertEqual(live_seller["products"], [])
        self.assertEqual(self.request(f"/api/sellers?point={point_id}")["sellers"][0]["products"], [])

        self.request("/api/presence", "POST", {"point_id": point_id, "selling": False, "whatsapp": "5511999999999"})
        self.assertEqual(self.request(f"/api/sellers?point={point_id}")["sellers"], [])

        # A mesma conta alterna de volta sem logout.
        self.request("/api/mode", "POST", {"mode": "buyer"})
        self.assertEqual(self.request("/api/me")["user"]["mode"], "buyer")

    def test_password_login_and_duplicate_registration(self):
        self.register("login@example.com")
        self.request("/api/register", "POST", {"name": "Outro", "email": "login@example.com", "password": "senha-segura-123"}, expected=409)
        self.request("/api/logout", "POST", {})
        self.request("/api/me", expected=401)
        data = self.request("/api/login", "POST", {"email": "login@example.com", "password": "senha-segura-123"})
        self.assertEqual(data["user"]["email"], "login@example.com")
        self.request("/api/login", "POST", {"email": "login@example.com", "password": "errada"}, expected=401)

    def test_main_page_and_bad_password_validation(self):
        page = self.request("/")
        self.assertIn(b"V\xc3\xb4Lanchar", page)
        self.request("/api/register", "POST", {"name": "A", "email": "a@example.com", "password": "curta"}, expected=400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
