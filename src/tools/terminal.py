"""
ARK.Tools — Terminal Oracle
===========================
Macのターミナルを操作し、エージェントの指示に応じてコマンドを実行する。
"""

import subprocess
import logging
import os
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
        log.info("Terminal Oracle initialized at: %s", self.workspace_path)

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

        log.info("Oracle executing: %s", command)
        
        try:
            # ワークスペースを作成（存在しない場合）
            self.workspace_path.mkdir(parents=True, exist_ok=True)

            # コマンド実行
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
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