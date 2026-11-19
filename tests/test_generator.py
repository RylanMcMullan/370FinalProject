import string
import unittest

from password_manager.generator import generate_password


class GeneratorTests(unittest.TestCase):
    def test_default_length(self):
        self.assertEqual(len(generate_password()), 6)

    def test_length_and_each_selected_group(self):
        password = generate_password(20)
        self.assertEqual(len(password), 20)
        self.assertTrue(any(char in string.ascii_lowercase for char in password))
        self.assertTrue(any(char in string.ascii_uppercase for char in password))
        self.assertTrue(any(char in string.digits for char in password))
        self.assertTrue(any(char in "!@#$%^&*()-_=+[]{}:,.?" for char in password))

    def test_selected_groups_and_invalid_settings(self):
        self.assertTrue(generate_password(4, uppercase=False, digits=False, symbols=False).islower())
        with self.assertRaises(ValueError):
            generate_password(3)
        with self.assertRaises(ValueError):
            generate_password(21)
        with self.assertRaises(ValueError):
            generate_password(12, lowercase=False, uppercase=False, digits=False, symbols=False)


if __name__ == "__main__":
    unittest.main()
