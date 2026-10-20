import unittest

from app.services.users import UserService


class UserServiceTests(unittest.TestCase):
    def setUp(self):
        self.users = UserService()

    def test_register_creates_account_without_storing_password(self):
        user = self.users.register(name="John Doe", email="johnd@example.com", password="johnnydoe-123")
        stored = self.users.get(user.id)
        self.assertEqual(stored.name, "John Doe")
        self.assertEqual(stored.email, "johnd@example.com")
        self.assertNotIn("johnnydoe-123", stored.password_hash)
        self.assertTrue(self.users.password_matches(stored, "johnnydoe-123"))
        self.assertFalse(self.users.password_matches(stored, "wrong-password"))

    def test_register_rejects_duplicate_email_ignoring_case(self):
        self.users.register(name="John", email="john@example.com", password="johnny-123")
        with self.assertRaises(ValueError):
            self.users.register(name="Other John", email="John@Example.com", password="another-password")
        self.assertEqual(self.users.get_by_email("John@Example.com").name, "John")

    def test_register_rejects_invalid_fields(self):
        cases = [
            {"name": "  ", "email": "john@example.com", "password": "correct-horse"},
            {"name": "John", "email": "not-an-email", "password": "correct-horse"},
            {"name": "John", "email": "john@example.com", "password": ""},
            {"name": "John", "email": "john@example.com", "password": "short"},
        ]
        for fields in cases:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    self.users.register(**fields)
        self.assertIsNone(self.users.get_by_email("john@example.com"))

    def test_authenticate_accepts_correct_credentials_ignoring_email_case(self):
        user = self.users.register(name="John", email="john@example.com", password="johnny-123")
        self.assertIs(self.users.authenticate("John@Example.com", "johnny-123"), user)

    def test_authenticate_rejects_wrong_password_and_unknown_email(self):
        self.users.register(name="John", email="john@example.com", password="johnny-123")
        self.assertIsNone(self.users.authenticate("john@example.com", "wrong-password"))
        self.assertIsNone(self.users.authenticate("nobody@example.com", "johnny-123"))


if __name__ == "__main__":
    unittest.main()
