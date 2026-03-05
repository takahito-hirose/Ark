import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main_output(self):
        """
        Checks if the 'main' function prints 'hello' to the console.
        
        This is a simple test case to ensure that our application's entry point
        behaves as expected.
        """
        with self.assertLogs(level='INFO') as caplog:
            main()
        self.assertIn('hello', caplog.output)

if __name__ == "__main__":
    unittest.main()