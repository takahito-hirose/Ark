from typing import Annotated
from src.memory import MemoryManager
import logging

log = logging.getLogger("ARK.MemoryTools")

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
    # 🚨 【入庫審査】プレースホルダーなどのゴミデータを弾く！
    invalid_keywords = ["ルール名", "内容", "key", "value", "string"]
    if key in invalid_keywords or value in invalid_keywords or not key.strip() or not value.strip():
        log.warning(f"🚫 [Memory] ゴミデータの保存をブロックしました: {key}={value}")
        return "❌ Error: プレースホルダー（'ルール名'や'内容'）のまま保存することは禁止されています。具体的なプロジェクトの掟を記述してやり直してください💋"

    if _manager:
        _manager.save_core_rule(key, value)
        return f"✅ コアルール '{key}' を ARK の脳内に記録しました。"
    return "Error: Memory Manager が初期化されていません。"

def archive_experience(
    summary: Annotated[str, "解決した問題の概要、エラー修正の知見、または学んだことの要約"],
    source: Annotated[str, "情報の出所（例: 'local_execution', 'telescope'）"] = "local_execution",
    trust_level: Annotated[str, "情報の信頼度（'verified': 実行・実証済み, 'unverified': 未検証の知識）"] = "verified"
) -> str:
    """
    現在のタスクで得られた重要な知見や経験をアーカイブ（Tier 3）に保存します。
    将来、似たような状況に直面した際に recall_memory で検索可能になります。
    """
    # 🚨 【入庫審査】薄っぺらい要約やゴミデータを弾く！
    invalid_summaries = ["知見の要約", "解決した問題の概要", "summary", "string"]
    if summary in invalid_summaries or len(summary) < 10:
        log.warning(f"🚫 [Memory] 内容の薄いアーカイブをブロックしました: {summary}")
        return "❌ Error: '知見の要約' のようなプレースホルダーや、短すぎる内容は保存できません。後から検索して役立つように、具体的に何をどう解決したか記述してやり直してください💋"

    if _manager:
        # 🌟 バックエンドのManagerにメタデータ（タグ）も一緒に渡すように変更！
        _manager.archive_experience(summary, source=source, trust_level=trust_level)
        return f"✅ この経験は ARK のアーカイブに保管されました。（Source: {source}, Trust: {trust_level}）"
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