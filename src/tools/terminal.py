from subprocess import run, PIPE, Popen, TimeoutExpired
import logging

TERMINAL_ORACLE_PROMPT = """
あなたは「Terminal Oracle」です。OSのコマンド実行に特化しています。
あなたの目的は、ユーザーや他のエージェントの要求に応じて、テストの実行、ライブラリのインストール、
あるいはスクリプトの実行を安全に行うことです。
実行前に、そのコマンドが現在のディレクトリや環境にどのような影響を与えるか、
「Terminal Oracle」の情報を元に慎重に判断してください。
"""

class TerminalOracle:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.commands_executed = []

    def execute_command(self, command: str, timeout: int = 30) -> str:
        # Check for dangerous commands
        if any(keyword in command.lower() for keyword in ["rm -rf /", "sudo rm"]):
            return "Error: Dangerous command detected. Command not executed."

        try:
            result = run(command, shell=True, check=True, stdout=PIPE, stderr=PIPE, timeout=timeout)
            self.commands_executed.append(command)
            return result.stdout.decode("utf-8")
        except TimeoutExpired:
            return f"Command timed out after {timeout} seconds."
        except Exception as e:
            return str(e)

# Example usage:
if __name__ == "__main__":
    oracle = TerminalOracle()
    print(oracle.execute_command("echo Hello, World!"))