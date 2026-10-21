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
        user = self.users.get_by_email("john@example.com")
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], user.id)
            self.assertEqual(session["user_name"], user.name)

    def test_login_accepts_email_case_and_surrounding_whitespace(self):
        response = self.client.post(
            "/login",
            data={"email": "  JOHN@EXAMPLE.COM  ", "password": "johnnydoe-123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        with self.client.session_transaction() as session:
            self.assertEqual(
                session["user_id"], self.users.get_by_email("john@example.com").id
            )

    def test_unknown_account_is_rejected_without_creating_session(self):
        response = self.client.post(
            "/login",
            data={"email": "unknown@example.com", "password": "johnnydoe-123"},
        )
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)
            self.assertNotIn("user_name", session)

    def test_login_switches_session_to_the_authenticated_account(self):
        self.client.post(
            "/login",
            data={"email": "john@example.com", "password": "johnnydoe-123"},
        )
        second_user = self.users.register(
            name="Alex Smith", email="alex@example.com", password="alex-password-123"
        )
        response = self.client.post(
            "/login",
            data={"email": "alex@example.com", "password": "alex-password-123"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Alex Smith", response.data)
        with self.client.session_transaction() as session:
            self.assertEqual(session["user_id"], second_user.id)
            self.assertEqual(session["user_name"], second_user.name)

    def test_invalid_login_is_rejected(self):
        response = self.client.post("/login", data={"email": "john@example.com", "password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)
            self.assertNotIn("user_name", session)

    def test_logout_clears_the_session(self):
        self.client.post("/login", data={"email": "john@example.com", "password": "johnnydoe-123"})
        response = self.client.post("/logout", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"Log out", response.data)
        with self.client.session_transaction() as session:
            self.assertNotIn("user_id", session)


if __name__ == "__main__":
    unittest.main()
