"""
ARK.Tools — Terminal Oracle
===========================
Mac/Windowsのターミナルを操作し、エージェントの指示に応じてコマンドを実行する。
"""

import subprocess
import logging
import os
import sys
from pathlib import Path
from typing import NamedTuple

# ジェニーのプロンプト、しっかり魂を吹き込んでおいたわよ💋
TERMINAL_ORACLE_PROMPT = """
あなたは「Terminal Oracle」です。OSのコマンド実行に特化しています。
あなたの目的は、ユーザーや他のエージェントの要求に応じて、テストの実行、ライブラリのインストール、
あるいはスクリプトの実行を安全に行うことです。
実行前に、そのコマンドが現在のディレクトリや環境にどのような影響を与えるか、
「Terminal Oracle」の情報を元に慎重に判断してください。
"""

log = logging.getLogger("ARK.Tools.Terminal")

class CommandResult(NamedTuple):
    """コマンド実行の詳細な結果。"""
    exit_code: int
    stdout: str
    stderr: str
    success: bool

class TerminalOracle:
    def __init__(self, workspace_path: str | Path = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.commands_executed = []
        
        # 🛡️ 仮想環境のパス設定（Mac/Windows両対応仕様よ！💋）
        self.venv_dir = self.workspace_path / ".venv"
        import os
        if os.name == 'nt': # Windowsの場合
            self.venv_python = self.venv_dir / "Scripts" / "python.exe"
            self.venv_pip = self.venv_dir / "Scripts" / "pip.exe"
        else: # Mac/Linuxの場合
            self.venv_python = self.venv_dir / "bin" / "python"
            self.venv_pip = self.venv_dir / "bin" / "pip"
        
        log.info("Terminal Oracle initialized at: %s", self.workspace_path)
        
        # 起動時に隔離部屋を自動建設！
        self._ensure_venv()

    def _ensure_venv(self):
        """ドック内に専用の仮想環境が存在しない場合は作成するわ"""
        if not self.venv_python.exists():
            log.info(f"🛡️ Building absolute shield (venv) at {self.venv_dir}...")
            # 母艦と同じバージョンのPythonでvenvを作成
            subprocess.run([sys.executable, "-m", "venv", str(self.venv_dir)], check=True)
            log.info("✅ Shield built successfully!")

    def execute_command(self, command: str, timeout: int = 60) -> CommandResult:
        """
        指定されたコマンドを安全に実行する。
        """
        # ジェニーが追加してくれた安全装置（Danger Check）！
        dangerous_keywords = ["rm -rf /", "sudo ", "mkfs", ":(){ :|:& };:"]
        if any(keyword in command.lower() for keyword in dangerous_keywords):
            msg = "Error: Dangerous command detected. ARK blocked this execution for safety."
            log.warning("🚫 %s", msg)
            return CommandResult(-1, "", msg, False)

        # 🚨 コマンドの乗っ取り（ハイジャック）：pythonとpipをvenvのものにすり替える
        safe_command = command
        if command.startswith("python "):
            safe_command = command.replace("python ", f'"{self.venv_python}" ', 1)
        elif command.startswith("pip "):
            safe_command = command.replace("pip ", f'"{self.venv_pip}" ', 1)

        log.info("Oracle executing: %s", safe_command)
        
        try:
            # ワークスペースを作成（存在しない場合）
            self.workspace_path.mkdir(parents=True, exist_ok=True)

            # コマンド実行
            result = subprocess.run(
                safe_command,
                shell=True,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8", # Windowsの文字化け対策よ！💋
                errors="replace", # 🌟 追加: 解読できない文字（cp932等）は ? に置換してクラッシュを絶対防ぐ！
                env=os.environ.copy() # 現在の環境変数を継承
            )
            
            self.commands_executed.append(command)
            
            return CommandResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                success=(result.returncode == 0)
            )

        except subprocess.TimeoutExpired as e:
            log.error("Command timed out: %s", command)
            return CommandResult(-1, e.stdout or "", "Timeout expired", False)
        except Exception as e:
            log.error("Unexpected error during execution: %s", str(e))
            return CommandResult(-1, "", str(e), False)

# 動作確認用（直接実行時）
if __name__ == "__main__":
    oracle = TerminalOracle(workspace_path="./test_workspace")
    res = oracle.execute_command("echo 'Hello from Terminal Oracle!'")
    print(f"Result: {res.stdout.strip()} (Success: {res.success})")