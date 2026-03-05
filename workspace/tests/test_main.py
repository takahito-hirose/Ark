import unittest
from main import main

class TestMain(unittest.TestCase):
    def test_main(self) -> None:
        with self.assertLogs(level='INFO') as captured_logs:
            main()
        output = ' '.join(captured_logs.output)
        self.assertIn('hello', output)

if __name__ == "__main__":
    unittest.main()