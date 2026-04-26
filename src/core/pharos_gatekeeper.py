"""
Phase 16: The Pharos (Gatekeeper Module)
Orchestratorから独立し、AIによるコード品質監査と自動差し戻しを担当する門番クラス。
"""
import requests
from pathlib import Path
from typing import Callable

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.core.models import CodePayload, ReviewPayload, ReviewStatus

console = Console()

class PharosGatekeeper:
    def __init__(self, api_url: str = "http://localhost:8001/api/v1/audit/ai", max_retries: int = 3):
        self.api_url = api_url
        self.max_retries = max_retries
        self.is_active = self._check_health()

    def _check_health(self) -> bool:
        """起動時にPharos APIが生きているか確認する（死活監視）"""
        console.print("[dim]Checking The Pharos API health...[/dim]")
        try:
            base_url = "/".join(self.api_url.split("/")[:3]) 
            res = requests.get(base_url, timeout=2)
            if res.status_code == 200 or res.status_code == 404: 
                console.print("[bold green]🗼 The Pharos Gatekeeper is ONLINE. Absolute Defense activated.[/bold green]")
                return True
        except requests.RequestException:
            pass
        
        # 🌟 ここを「GitHub Actionsへの引き継ぎ」を意識したメッセージに変更！
        console.print(Panel(
            "[bold yellow]⚠️ ローカルの The Pharos API は OFFLINE です。[/bold yellow]\n"
            "ローカルでの即時コード監査はスキップされ、Reviewerへ直接引き継がれます。\n\n"
            "[dim]※安心してください。コードをPushしてPRを作成した際、[/dim]\n"
            "[dim]クラウド上の 🐙 GitHub Actions が自動で最終監査を実行します！[/dim]\n\n"
            "（ローカルで即時監査を有効化するには: [cyan]uvicorn main:app --reload --port 8001[/cyan] を実行）",
            title="Gatekeeper Status (Fallback to Cloud)"
        ))
        return False

    def audit_and_review(
        self,
        code: CodePayload,
        retry: int,
        dock_path: Path,
        reviewer_callback: Callable[[], ReviewPayload]
    ) -> ReviewPayload:
        """
        Pharos APIを呼び出し、スコアが低ければREJECTEDを返し、
        問題なければ本来のReviewerへ処理を委譲する。
        """
        if not self.is_active:
            return reviewer_callback()

        # 1. 監査対象のファイルを特定（不要なディレクトリの除外）
        ignore_dirs = {".venv", "__pycache__", ".git", "node_modules", ".ark_memory"}
        valid_files = []
        
        for f in code.files:
            # Pythonファイルのみ対象（テストコードは除外）
            if not f.path.endswith(".py") or f.path.startswith("test_"):
                continue
                
            # パスの途中にブラックリストのディレクトリが含まれていないかチェック
            parts = Path(f.path).parts
            if any(ignored in parts for ignored in ignore_dirs):
                continue
                
            valid_files.append(f)

        if not valid_files:
            return reviewer_callback()

        # 複数ファイルの絶対パスリストを作成
        target_paths = [str(dock_path / f.path) for f in valid_files]
        file_names = [f.path for f in valid_files]
        
        console.print(f"\n[bold cyan]🗼 The Pharos is scanning ({len(file_names)} files):[/bold cyan]")
        for name in file_names:
            console.print(f"[cyan]  - {name}[/cyan]")

        # 2. Pharos API へのリクエスト（複数パス対応）
        try:
            res = requests.post(
                self.api_url,
                json={"target_paths": target_paths}, # 🌟 ここが複数形のリストになったわ！
                timeout=120 # 🌟 複数ファイルを読むので制限時間を延長
            )
            res.raise_for_status()
            pharos_result = res.json()
        except Exception as e:
            console.print(f"[bold red]⚠️ Pharos API 通信エラー (スキップして人間の/AI Reviewerへ渡します): {e}[/bold red]")
            return reviewer_callback()

        # 3. 結果のターミナル描画 (rich)
        table = Table(show_header=True, header_style="bold magenta", title="Pharos 5-Axis Audit")
        table.add_column("Category", style="dim", width=20)
        table.add_column("Score", justify="right")
        table.add_column("Status")

        failed_issues = []
        is_all_green = True

        for category in ["security", "performance", "maintainability", "resilience", "testability"]:
            cat_data = pharos_result.get(category, {})
            score = cat_data.get("score", 0)
            
            if score < 80:
                is_all_green = False
                status = "[bold red]Refine Required[/bold red]"
                issues_text = "\n".join([f"- {i}" for i in cat_data.get("issues", [])])
                failed_issues.append(f"【{category.capitalize()} (Score: {score})】\n{issues_text}")
            else:
                status = "[bold green]Pass[/bold green]"

            table.add_row(category.capitalize(), str(score), status)

        console.print(table)
        console.print(f"[italic]Summary: {pharos_result.get('overall_summary', '')}[/italic]\n")

        # 4. Gatekeeper Logic (自動差し戻し判定)
        if not is_all_green and retry < self.max_retries:
            console.print(Panel("[bold red]🚨 The Pharos Rejected the code! Sending back to Coder...[/bold red]"))
            feedback = (
                "The Pharos (AI Quality Auditor) rejected your code. "
                "Please fix the following issues and try again:\n\n" +
                "\n\n".join(failed_issues)
            )
            return ReviewPayload(
                status=ReviewStatus.REJECTED,
                feedback=feedback,
                approved_files=[]
            )

        # 5. 監査通過
        if is_all_green:
            console.print("[bold green]✅ The Pharos Approved! Handing over to Human/AI Reviewer...[/bold green]")
        else:
            console.print(f"[bold yellow]⚠️ Max retries ({self.max_retries}) reached. Forcing code to Reviewer...[/bold yellow]")

        return reviewer_callback()