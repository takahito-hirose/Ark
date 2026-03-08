from typing import Annotated
from src.memory import MemoryManager

# グローバルなマネージャー変数。Orchestratorから注入されます。
_manager: MemoryManager = None

def inject_memory_manager(manager: MemoryManager):
    """
    MemoryManagerのインスタンスをツールセットに注入します。
    """
    global _manager
    _manager = manager

def save_core_rule(
    key: Annotated[str, "ルールの名前（例: 'tech_stack', 'naming_convention'）"],
    value: Annotated[str, "保存する具体的な内容や指示"]
) -> str:
    """
    プロジェクト全体の重要なルールや制約を長期記憶（Tier 2）に保存します。
    ここで保存された内容は、今後の思考において常にシステムプロンプトに含まれます。
    """
    if _manager:
        _manager.save_core_rule(key, value)
        return f"コアルール '{key}' を ARK の脳内に記録しました。"
    return "Error: Memory Manager が初期化されていません。"

def archive_experience(
    summary: Annotated[str, "解決した問題の概要、エラー修正の知見、または学んだことの要約"]
) -> str:
    """
    現在のタスクで得られた重要な知見や経験をアーカイブ（Tier 3）に保存します。
    将来、似たような状況に直面した際に recall_memory で検索可能になります。
    """
    if _manager:
        _manager.archive_experience(summary)
        return "この経験は ARK のアーカイブに大切に保管されました。将来の航海に役立つはずです。"
    return "Error: Memory Manager が初期化されていません。"

def recall_memory(
    query: Annotated[str, "過去の記憶から検索したい内容のキーワードや自然言語クエリ"]
) -> str:
    """
    長期記憶（アーカイブ）から過去の類似する経験を検索します。
    未知のエラーが発生した時や、以前同じことをした記憶がある場合に活用してください。
    """
    if _manager:
        return _manager.recall_memory(query)
    return "Error: Memory Manager が初期化されていません。"