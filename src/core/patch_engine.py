import re
import os
import logging

log = logging.getLogger("ARK.PatchEngine")

class PatchEngine:
    """
    🚢 ARK Surgical Patch Engine (Ultra-Resilient Version)
    二重執刀を防ぎ、ECOモードの精霊たちが生成する「ちょっとしたノイズ」も
    華麗にスルーして執刀する最強の外科医よ！💋
    """

    @staticmethod
    def apply_patches(file_path: str, patch_content: str) -> bool:
        """
        指定されたファイルに SEARCH/REPLACE パッチを適用します。
        """
        if not os.path.exists(file_path):
            log.error("File not found for patching: %s", file_path)
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 🔍 SEARCH/REPLACE ブロックを抽出（マーカー前後の自由度を最大化！）
        # マーカー直後の改行やスペース、およびブロック内の末尾の空白に寛容な設計よ💋
        pattern = re.compile(
            r"<<<<<<<\s*SEARCH\s*\n(.*?)\n=======\s*\n(.*?)\n>>>>>>>\s*REPLACE", 
            re.DOTALL
        )
        matches = pattern.findall(patch_content)

        if not matches:
            # マーカーが見つからない場合は、外科手術不能として False を返すわ
            return False

        new_content = content
        any_match_failed = False

        for search_block, replace_block in matches:
            # 🌟 ノアぴの超回復処理：精霊がうっかり含めたマークダウンの装飾などを除去
            s_block = PatchEngine._clean_block(search_block)
            r_block = PatchEngine._clean_block(replace_block)

            # 1. 既に適用済みかチェック（二重執刀防止）
            if r_block in new_content:
                log.debug("Patch block already applied to %s. Skipping.", file_path)
                continue

            # 2. 厳密一致で検索
            if s_block in new_content:
                new_content = new_content.replace(s_block, r_block)
            else:
                # 3. 柔軟な一致（インデントの揺らぎや前後の空白を考慮）
                s_stripped = s_block.strip()
                if s_stripped and s_stripped in new_content:
                    # 前後の改行を保持しつつ、中身を置換
                    # ※行全体をターゲットにするためのヒューリスティックな置換よ💋
                    new_content = new_content.replace(s_stripped, r_block.strip())
                else:
                    log.warning("⚠️  Patch Match Failed for block in %s:\n%s", file_path, s_block)
                    any_match_failed = True

        if new_content == content:
            # 変更が一切発生しなかった場合
            return False

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True

    @staticmethod
    def _clean_block(block: str) -> str:
        """
        ブロック内に紛れ込んだマークダウンタグ（```python等）を除去するわ。
        ECOモードの精霊たちは、パッチの中にコードブロックを入れちゃう癖があるからね💋
        """
        # 行単位でスキャンしてマーカーを除去
        lines = block.split('\n')
        cleaned = [l for l in lines if not l.strip().startswith('```')]
        return '\n'.join(cleaned)