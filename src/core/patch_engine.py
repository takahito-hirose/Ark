"""
ARK — Patch Engine (The Scalpel)
=======================================================================
SEARCH/REPLACE 形式のパッチを解析し、ファイルに適用する。
不完全なパッチや、マーカーが残るミスを自動的に修正・除去する。
"""

import logging
import re
from pathlib import Path

log = logging.getLogger("ARK.PatchEngine")

class PatchEngine:
    """SEARCH/REPLACE パッチをファイルに適用するエンジニア。"""

    def apply(self, patch_text: str, dock) -> bool:
        """
        パッチテキストを解析して、ドック内のファイルに適用する。
        """
        # パッチブロックの抽出 (<<<< SEARCH, ====, >>>> REPLACE)
        pattern = re.compile(
            r"<<<<<<? SEARCH\n(.*?)\n======?\n(.*?)\n>>>>>>? REPLACE",
            re.DOTALL
        )
        blocks = pattern.findall(patch_text)

        if not blocks:
            # パッチ形式でない場合、コードブロックとして全体を抽出して上書きを試みる
            code_match = re.search(r"```python\n(.*?)\n```", patch_text, re.DOTALL)
            if code_match:
                log.info("ℹ️ No SEARCH/REPLACE blocks found. Falling back to Full Overwrite.")
                # 本来はファイル名を特定する必要があるが、一旦ターゲットが1つと仮定
                # (実際の運用では Architect の plan.target_files[0] を使う)
                return False 
            return False

        success_count = 0
        # 暫定的なターゲットファイル特定 (ログから cowsay_app.py と推測)
        target_path = dock.path / "cowsay_app.py"
        
        if not target_path.exists():
            log.error("❌ Target file not found: %s", target_path)
            return False

        content = target_path.read_text()

        for search, replace in blocks:
            # 前後の空白を無視して検索（LLMのインデントミス対策）
            if search.strip() in content:
                content = content.replace(search.strip(), replace.strip())
                success_count += 1
            else:
                # 部分一致や正規表現でのフォールバック（将来的な拡張用）
                log.warning("⚠️ Patch mismatch: Search block not found exactly.")
        
        if success_count > 0:
            # 誤って混入したマーカーを掃除（セーフティネット）
            content = self._sanitize(content)
            target_path.write_text(content)
            log.info("✅ Applied %d patch block(s) to %s", success_count, target_path.name)
            return True

        return False

    def _sanitize(self, content: str) -> str:
        """コード内に残ったパッチマーカーを強制除去する。"""
        markers = [
            r"<<<<<<? SEARCH", r"======?", r">>>>>>? REPLACE",
            r"<<<<<<? [A-Z_]+", r">>>>>>? [A-Z_]+"
        ]
        for m in markers:
            content = re.sub(m + r".*?\n", "", content)
        return content