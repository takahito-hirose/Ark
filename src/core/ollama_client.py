import requests
from typing import Optional

class OllamaClient:
    def __init__(self, api_endpoint: str, model_name: str):
        self.api_endpoint = api_endpoint
        self.model_name = model_name

    def send_request(self, prompt: str) -> Optional[str]:
        try:
            url = f"{self.api_endpoint}/api/generate"
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }

            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            return response.json().get('response')
        except requests.RequestException as e:
            print(f"Error sending request to Ollama: {e}")
            return None

    def generate_text(self, prompt: str) -> Optional[str]:
        text = self.send_request(prompt)
        if text is not None:
            return text.strip()
        return None