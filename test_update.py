import os
from pathlib import Path
from dotenv import load_dotenv
from src.core.orchestrator import Orchestrator

def main():
    load_dotenv()
    
    # 1. テスト用のダミープロジェクトを作成
    target_dir = Path("workspace/test_update_repo").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # ダミーのPythonファイルを作成
    hello_file = target_dir / "hello.py"
    hello_file.write_text(
        "def greet():\n    print('Hello, World!')\n\nif __name__ == '__main__':\n    greet()\n", 
        encoding="utf-8"
    )
    
    # Gitリポジトリとして初期化（すでにリポジトリならスキップされる）
    print("📦 Initializing dummy git repository...")
    os.system(f'cd "{target_dir}" && git init && git add . && git commit -m "Initial commit" > /dev/null 2>&1')
    
    print(f"🎯 Target repository setup complete: {target_dir}")
    print("🚀 Launching ARK in UPDATE MODE...\n")

    # 2. Orchestratorに既存のパスを渡して実行！
    # ※本番と同じようにテストしたい場合は mode="RICH" に変えてもOKよ！
    orc = Orchestrator(workspace_path=target_dir, mode="ECO")
    
    goal = "hello.py の greet() 関数の中身を、ギャル語で挨拶するように書き換えて！SEARCH/REPLACE形式のパッチを使ってね💋"
    
    try:
        orc.run(goal)
        print("\n🎉 テスト完了！ダミーリポジトリのログやPRURLを確認してみて！")
    except Exception as e:
        print(f"\n❌ テスト中にエラーが発生したわ: {e}")

if __name__ == "__main__":
    main()