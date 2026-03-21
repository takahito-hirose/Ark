"""
ARK — WebTelescope Tool (Brave Edition) 🔭
=======================================
Brave Search API を使用して、外界の知識を「無課金・高精度」で抽出する。
お財布防衛リミッターとモックモードを搭載した安全設計よ💋
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

log = logging.getLogger("ARK.Tools.Telescope")

class WebTelescope:
    """Brave APIを使用してWeb検索とスクレイピングを行うクラス。"""

    def __init__(self, timeout: int = 10, mock_mode: bool = False):
        self.api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.timeout = timeout
        
        # 🌟 Orchestrator からのテレパシー（環境変数）を受信！
        # もし ARK_MOCK_MODE が "1" なら無条件でモックにするわ！
        env_mock = os.getenv("ARK_MOCK_MODE")
        if env_mock is not None:
            self.use_mock = (env_mock == "1")
        else:
            self.use_mock = mock_mode
            
        self.call_count = 0
        self.MAX_CALLS_PER_RUN = 3
        
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key or "",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        self.call_count += 1
        
        if self.use_mock:
            log.info(f"ℹ️ [MOCK MODE] Intercepting search request for: {query}")
            mock_content = self._get_mock_data(query)
            return [{
                "title": f"Search Results for {query} (Mock)",
                "url": "http://localhost/mock",
                "snippet": mock_content
            }]

        if self.call_count > self.MAX_CALLS_PER_RUN:
            log.warning("💸 [Telescope] API Call limit reached!")
            return [{
                "title": "API Limit Reached", 
                "url": "http://localhost", 
                "snippet": "検索上限に達しました。今持っている知識だけでコードを実装してください！💋"
            }]

        if not self.api_key:
            log.error("❌ BRAVE_SEARCH_API_KEY が設定されていません。")
            return []

        results = []
        params = {"q": query, "count": min(max_results, 20)}

        try:
            log.info(f"🔭 Brave Searching (Call {self.call_count}/{self.MAX_CALLS_PER_RUN}) for: {query}")
            response = requests.get(
                self.base_url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                log.error(f"Brave API Error Content: {response.text}")

            response.raise_for_status()
            data = response.json()

            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"][:max_results]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")
                    })
        except Exception as e:
            log.error(f"Brave Search failed: {e}")
        return results

    def _get_mock_data(self, query: str) -> str:
        q = query.lower()
        if "ascii-magic" in q:
            return """
# ascii-magic チュートリアル (Mock Data)
`ascii-magic` は画像をアスキーアートに変換するライブラリです。

【完璧な使い方の例】
```python
import ascii_magic
import os

def main():
    image_path = "pikachu.png"
    if not os.path.exists(image_path):
        print(f"Error: 画像 {image_path} が見つかりません。")
        return
    try:
        my_art = ascii_magic.from_image(image_path)
        my_art.to_terminal()
    except Exception as e:
        print(f"変換エラー: {e}")
        
if __name__ == "__main__":
    main()
```
【絶対の掟】
- `input()` で入力を待たずに自動終了させること。
- 必要な依存ライブラリ: `ascii-magic`
            """
        return f"[MOCK RESULT] 検索クエリ '{query}' に対する結果です。現在はAPI節約モードです。"

    def read_page(self, url: str, max_chars: int = 5000) -> str:
        if self.use_mock or url == "http://localhost/mock" or url == "http://localhost":
            return "Mock content mode active. Use snippet information provided in search."

        try:
            log.info(f"📖 Reading: {url}")
            sc_headers = {"User-Agent": self.headers["User-Agent"]}
            resp = requests.get(url, headers=sc_headers, timeout=self.timeout)
            resp.raise_for_status()
            
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
            
            text = soup.get_text(separator="\n")
            clean_text = "\n".join(l.strip() for l in text.splitlines() if l.strip())
            return clean_text[:max_chars]
        except Exception as e:
            log.error(f"Read failed {url}: {e}")
            return f"Error reading page content: {e}"

    def research(self, query: str) -> str:
        results = self.search(query, max_results=2)
        if not results:
            return "Braveでの検索結果が見つかりませんでした。🔑を確認して！"
        
        report_sections = []
        for res in results:
            if self.use_mock:
                content = res['snippet']
            else:
                content = self.read_page(res['url'])
                if "Error" in content:
                    content = f"【本文取得失敗】要約: {res['snippet']}"

            section = f"### Source: {res['title']}\nURL: {res['url']}\nContent:\n{content}\n"
            report_sections.append(section)
            
        return "\n" + "="*40 + "\n" + "\n".join(report_sections)