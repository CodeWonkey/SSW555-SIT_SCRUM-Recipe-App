import unittest

from app import create_app
from app.services.recipes import RecipeService
from app.services.users import UserService


class LoginWebTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()
        self.users.register(name="John Doe", email="john@example.com", password="johnnydoe-123")
        self.client = create_app(RecipeService(), self.users).test_client()

    def test_login_page_renders_form(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'name="email"', response.data)
        self.assertIn(b'name="password"', response.data)

    def test_valid_login_signs_the_user_in(self):
        response = self.client.post(
            "/login",
            data={"email": "john@example.com", "password": "johnnydoe-123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"John Doe", response.data)
        self.assertIn(b"Log out", response.data)

    def test_invalid_login_is_rejected(self):
        response = self.client.post("/login", data={"email": "john@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)

    def test_logout_clears_the_session(self):
        self.client.post("/login", data={"email": "john@example.com", "password": "johnnydoe-123"})
        response = self.client.post("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Log out", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)


if __name__ == "__main__":
    unittest.main()
