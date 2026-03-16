import requests
from typing import Optional

class OllamaClient:
    def __init__(self, api_endpoint: str, model_name: str):
        self.api_endpoint = api_endpoint
        self.model_name = model_name

    def send_request(self, prompt: str) -> tuple[Optional[str], dict]:
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

            # 🌟 ここを 60 から 180 (3分) に延長したわよ！必要なら 300 にしてもOK！
            response = requests.post(url, headers=headers, json=data, timeout=180)
            response.raise_for_status()
            
            response_json = response.json()
            text = response_json.get('response')
            usage = response_json.get('usage', {})
            
            return text, usage

        except requests.RequestException as e:
            print(f"Error sending request to Ollama: {e}")
            return None, {}

    def generate_text(self, prompt: str) -> tuple[Optional[str], dict]:
        text, usage = self.send_request(prompt)
        if text is not None:
            return text.strip(), usage
        return None, usage