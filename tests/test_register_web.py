import unittest

from app import create_app
from app.services.recipes import RecipeService
from app.services.users import UserService


def form_data(**overrides):
    data = {
        "name": "John Doe",
        "email": "john@example.com",
        "password": "johnnydoe-123",
        "password_confirm": "johnnydoe-123",
    }
    data.update(overrides)
    return data


class RegisterWebTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()
        self.app = create_app(RecipeService(), self.users)
        self.client = self.app.test_client()

    def test_register_page_renders_form(self):
        response = self.client.get("/register")
        self.assertEqual(response.status_code, 200)
        for field in (b'name="name"', b'name="email"', b'name="password"', b'name="password_confirm"'):
            self.assertIn(field, response.data)
        self.assertIn(b"Create account", response.data)

    def test_valid_registration_creates_account_and_opens_the_app(self):
        response = self.client.post("/register", data=form_data(), follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"John Doe", response.data)
        self.assertIn(b"Recipes worth keeping", response.data)

        user = self.users.get_by_email("john@example.com")
        self.assertIsNotNone(user)
        self.assertNotIn("johnnydoe-123", user.password_hash)
        with self.client.session_transaction() as session_data:
            self.assertEqual(session_data["user_id"], user.id)

    def test_duplicate_email_is_rejected(self):
        self.client.post("/register", data=form_data())
        response = self.client.post("/register", data=form_data(name="Someone Else"))
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already exists", response.data)
        self.assertEqual(self.users.get_by_email("john@example.com").name, "John Doe")

    def test_invalid_input_is_not_saved(self):
        cases = [
            form_data(name="  "),
            form_data(email="not-an-email"),
            form_data(password="short", password_confirm="short"),
            form_data(password_confirm="different-password"),
        ]
        for data in cases:
            with self.subTest(data=data):
                response = self.client.post("/register", data=data)
                self.assertEqual(response.status_code, 400)
                self.assertIsNone(self.users.get_by_email(data["email"]))


if __name__ == "__main__":
    unittest.main()
