"""
ARK — WebTelescope Tool (Brave Edition)
=======================================
Brave Search API を使用して、外界の知識を「無課金・高精度」で抽出する。
"""

import os
import logging
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

log = logging.getLogger("ARK.Tools.Telescope")

class WebTelescope:
    """Brave APIを使用してWeb検索とスクレイピングを行うクラス。"""

    def __init__(self, timeout: int = 10):
        # 環境変数からBraveの鍵を取得
        self.api_key = os.getenv("BRAVE_SEARCH_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
        self.timeout = timeout
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }

    def search(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Brave Search を実行して結果を取得（極限までシンプル版）。"""
        if not self.api_key:
            log.error("BRAVE_SEARCH_API_KEY が設定されていません。")
            return []

        results = []
        # 👈 422を避けるため、一旦 search_lang や safesearch を全部削除！
        # 日本語の結果が欲しいなら、クエリ自体に含めるのが一番確実よ。
        params = {
            "q": query,
            "count": min(max_results, 20), # count は最大20まで
        }

        try:
            log.info(f"Brave Searching (Minimal) for: {query}")
            response = requests.get(
                self.base_url, 
                headers=self.headers, 
                params=params, 
                timeout=self.timeout
            )
            
            # もしエラーが出たら、何がダメだったのか中身を表示させるわよ！
            if response.status_code != 200:
                log.error(f"Brave API Error Content: {response.text}")

            response.raise_for_status()
            data = response.json()

            if "web" in data and "results" in data["web"]:
                for item in data["web"]["results"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")
                    })
        except Exception as e:
            log.error(f"Brave Search failed: {e}")
        return results

    def read_page(self, url: str, max_chars: int = 5000) -> str:
        """指定されたURLから本文を抽出。"""
        try:
            log.info(f"Reading: {url}")
            # スクレイピング用のヘッダー（API用とは分ける）
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
        """検索から内容抽出までを統合。"""
        results = self.search(query, max_results=3)
        if not results:
            return "Braveでの検索結果が見つかりませんでした。🔑を確認して！"
        
        report_sections = []
        for res in results:
            content = self.read_page(res['url'])
            if "Error" in content:
                content = f"【本文取得失敗】要約: {res['snippet']}"

            section = f"### Source: {res['title']}\nURL: {res['url']}\nContent:\n{content}\n"
            report_sections.append(section)
            
        return "\n" + "="*40 + "\n" + "\n".join(report_sections)

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    logging.basicConfig(level=logging.INFO)
    telescope = WebTelescope()
    # ロマン溢れる日本語検索、いっくわよー！💋
    print(telescope.research("Python 3.12 新機能"))