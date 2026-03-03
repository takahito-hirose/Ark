from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path
from src.core.models import RunResult

log = logging.getLogger("ARK.Runner")

class PythonRunner:
    """
    独立したプロセスでPythonスクリプトを実行するランナー。
    """

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def run_file(self, file_path: Path, cwd: Path | None = None) -> RunResult:
        """
        指定されたPythonファイルを子プロセスとして実行します。
        """
        cmd = ["python", str(file_path)]
        return self._execute(cmd, cwd or file_path.parent)

    def run_command(self, command: str, cwd: Path) -> RunResult:
        """
        指定されたコマンドを実行します。
        """
        # shell=True はセキュリティリスクがあるため、リスト形式を推奨しますが、
        # 自由なコマンド実行を許容する場合は注意が必要です。
        log.debug("Running command: %s in %s", command, cwd)
        start_time = time.perf_counter()
        timed_out = False
        
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as e:
            log.warning("⏱️ Execution timed out after %ds", self.timeout)
            exit_code = -1
            stdout = e.stdout.decode("utf-8", "replace") if e.stdout else ""
            stderr = e.stderr.decode("utf-8", "replace") if e.stderr else f"TimeoutExpired: {self.timeout}s"
            timed_out = True
        except Exception as e:
            log.error("❌ Execution failed: %s", e)
            exit_code = -1
            stdout = ""
            stderr = str(e)

        duration = time.perf_counter() - start_time
        return RunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timed_out=timed_out
        )

    def _execute(self, cmd: list[str], cwd: Path) -> RunResult:
        log.debug("Executing: %s", cmd)
        start_time = time.perf_counter()
        timed_out = False
        
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace"
            )
            exit_code = process.returncode
            stdout = process.stdout
            stderr = process.stderr
        except subprocess.TimeoutExpired as e:
            log.warning("⏱️ Execution timed out after %ds", self.timeout)
            exit_code = -1
            stdout = e.stdout.decode("utf-8", "replace") if e.stdout else ""
            stderr = e.stderr.decode("utf-8", "replace") if e.stderr else f"TimeoutExpired: {self.timeout}s"
            timed_out = True
        except Exception as e:
            log.error("❌ Unexpected error during execution: %s", e)
            exit_code = -1
            stdout = ""
            stderr = str(e)

        duration = time.perf_counter() - start_time
        return RunResult(
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration=duration,
            timed_out=timed_out
        )
