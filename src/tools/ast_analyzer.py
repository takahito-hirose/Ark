"""
ARK — AST Analyzer Tool (The Blueprint Scanner)
=======================================================================
Pythonの抽象構文木（AST）を解析し、コードの構造（クラス、メソッド、関数）
をアウトラインとして抽出する。
これによりLLMはトークンを節約しつつ、プロジェクトの全体像を深く理解できる。
"""

import ast
from pathlib import Path

def generate_code_outline(file_path: Path | str) -> str:
    """
    指定されたPythonファイルのASTを解析し、構造のアウトラインを文字列として返す。
    
    Args:
        file_path (Path | str): 解析対象のPythonファイルのパス
        
    Returns:
        str: クラス、関数、メソッドのシグネチャをまとめたアウトラインテキスト
    """
    path = Path(file_path)
    if not path.exists() or not path.name.endswith(".py"):
        return ""
    
    try:
        content = path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(path))
    except Exception as e:
        return f"# Error parsing {path.name}: {e}"

    outline = [f"📄 File: {path.name}"]
    
    # ASTノードを巡回して構造を抽出
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            outline.append(f"class {node.name}:")
            # Docstringがあれば1行目だけ抽出
            doc = ast.get_docstring(node)
            if doc:
                first_line = doc.split("\n")[0].strip()
                outline.append(f"    \"\"\"{first_line}...\"\"\"")
            
            # クラス内のメソッドを抽出
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef):
                    # 引数リストの取得 (self, arg1, arg2...)
                    args = [a.arg for a in sub_node.args.args]
                    outline.append(f"    def {sub_node.name}({', '.join(args)}): ...")
            outline.append("") # クラス間の空行
            
        elif isinstance(node, ast.FunctionDef):
            # グローバル関数の抽出
            args = [a.arg for a in node.args.args]
            outline.append(f"def {node.name}({', '.join(args)}):")
            doc = ast.get_docstring(node)
            if doc:
                first_line = doc.split("\n")[0].strip()
                outline.append(f"    \"\"\"{first_line}...\"\"\"")
            else:
                outline.append("    ...")
            outline.append("")
                
    return "\n".join(outline).strip()

if __name__ == "__main__":
    # 簡単なテスト用（自分自身を解析）
    print(generate_code_outline(__file__))