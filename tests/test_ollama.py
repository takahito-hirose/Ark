import unittest
from src.core.ollama_client import OllamaClient

class TestOllamaClient(unittest.TestCase):
    def setUp(self):
        self.api_endpoint = "http://localhost:11434"  # Replace with your LLM API endpoint
        self.model_name = "gemma3:4b"  # Replace with your model name
        self.ollama_client = OllamaClient(self.api_endpoint, self.model_name)

    def test_generate_text(self):
        prompt = "Hello, how are you?"
        response = self.ollama_client.generate_text(prompt)
        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        print(f"Response from LLM: {response}")

if __name__ == "__main__":
    unittest.main()