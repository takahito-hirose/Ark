import re
import os

class PatchEngine:
    """
    🚢 ARK Surgical Patch Engine
    LLMが出力した SEARCH/REPLACE ブロックを解析し、既存ファイルに適用するわよ！💋
    """

    @staticmethod
    def apply_patches(file_path: str, patch_content: str) -> bool:
        """
        指定されたファイルに SEARCH/REPLACE パッチを適用するわ。
        形式:
        <<<<<<< SEARCH
        旧コード
        =======
        新コード
        >>>>>>> REPLACE
        """
        if not os.path.exists(file_path):
            return False

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 🔍 SEARCH/REPLACE ブロックを正規表現で抽出
        pattern = re.compile(
            r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", 
            re.DOTALL
        )
        matches = pattern.findall(patch_content)

        if not matches:
            # パッチ形式じゃない場合は、従来通り全上書きとして扱うわ
            return False

        new_content = content
        for search_block, replace_block in matches:
            # 前後の空白を調整して、より柔軟にマッチさせるわよ
            if search_block.strip() in new_content:
                new_content = new_content.replace(search_block, replace_block)
            else:
                # 厳密な一致に失敗した場合は、インデントなどを無視して試行（ここは今後の課題ね！）
                print(f"⚠️  Patch Match Failed for block:\n{search_block}")
                return False

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        return True