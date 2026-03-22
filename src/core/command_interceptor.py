"""
ARK — Command Interceptor
=======================================================================
Orchestratorの肥大化を防ぐための特殊コマンドルーター（傍受器）。
/memory, /forget, /gc などのメタコマンドをキャッチして処理するわ💋
"""
import logging
from typing import Callable, Optional, TYPE_CHECKING
from src.core.models import Phase

if TYPE_CHECKING:
    from src.memory import MemoryManager
    from src.agents.reflector import ReflectorAgent

log = logging.getLogger("ARK.CommandInterceptor")

def handle_special_commands(
    goal: str,
    memory: "MemoryManager",
    update_phase: Callable[[Phase, str, str], None],
    reflector: Optional["ReflectorAgent"] = None  # 🌟 司書を呼び出せるように引数を追加したわ！💋
) -> bool:
    """
    ユーザーの入力が特殊コマンドであれば処理を実行し、Trueを返す。
    通常の造船ミッションであれば False を返す。
    """
    cmd_text = goal.strip()
    if not cmd_text.startswith("/"):
        return False

    # 📚 記憶の検索＆一覧表示
    if cmd_text.startswith("/memory"):
        query = cmd_text.replace("/memory", "").strip()
        if not query:
            # キーワードなしなら全件ダンプ（一覧表示）！
            update_phase(Phase.PLANNING, "DUMP", "大図書館の記憶を全件抽出しています...")
            dump_results = memory.dump_memory() if hasattr(memory, 'dump_memory') else "一覧表示機能は準備中よ💋"
            update_phase(Phase.DONE, "FINISH", f"\n{dump_results}")
        else:
            # キーワードありならベクトル検索！
            update_phase(Phase.PLANNING, "SEARCH", f"大図書館を検索中...: {query}")
            search_results = memory.recall_memory(query, n_results=3)
            update_phase(Phase.DONE, "FINISH", f"{search_results}")
        return True

    # 🗑️ 特定の記憶の削除
    elif cmd_text.startswith("/forget"):
        mem_id = cmd_text.replace("/forget", "").strip()
        if not mem_id:
            update_phase(Phase.DONE, "INFO", "使い方: /forget <Memory ID> (例: /forget mem_1711234567)")
        else:
            update_phase(Phase.PLANNING, "DELETE", f"記憶 '{mem_id}' を消去しています...")
            if hasattr(memory, 'delete_memory'):
                success = memory.delete_memory(mem_id)
                if success:
                    update_phase(Phase.DONE, "FINISH", f"🗑️ 記憶 '{mem_id}' を大図書館から永久に消去しました。")
                else:
                    update_phase(Phase.DONE, "ERROR", f"❌ 記憶 '{mem_id}' の消去に失敗しました。IDが正しいか確認してね💋")
            else:
                update_phase(Phase.DONE, "INFO", "削除機能は準備中よ💋")
        return True
        
    # =========================================================================
    # 🧹 ガベージコレクション（大掃除・破壊と創造の儀式💋）
    # =========================================================================
    elif cmd_text.startswith("/gc"):
        update_phase(Phase.PLANNING, "GC", "🧹 大図書館のガベージコレクションを開始します...")
        
        # 1. 必要なメソッドやエージェントが揃っているかチェック
        if not hasattr(memory, 'get_all_memory_dump') or not hasattr(memory, 'rebuild_memory_from_gc'):
            update_phase(Phase.DONE, "ERROR", "❌ MemoryManagerにGC用のメソッドが実装されていないわ！")
            return True
            
        if not reflector:
            update_phase(Phase.DONE, "ERROR", "❌ 司書（ReflectorAgent）が渡されていないため整理ができないわ！Orchestratorを見直してね💋")
            return True

        # 2. 現在の記憶を全抽出
        update_phase(Phase.PLANNING, "GC", "📦 記憶のダンプデータを抽出中...")
        dump_str = memory.get_all_memory_dump()
        
        # 3. 司書に整理させる（APIを叩くので時間がかかるわ）
        update_phase(Phase.PLANNING, "GC", "🧠 司書が記憶の統合と整理を思考中...(これには数十秒かかるかも💋)")
        cleaned_json = reflector.garbage_collect(dump_str)
        
        if not cleaned_json:
            update_phase(Phase.DONE, "ERROR", "❌ 司書が記憶の整理に失敗したわ。出力形式が狂ったかもしれないわね。")
            return True
            
        # 4. 記憶の焼却と再構築！
        update_phase(Phase.PLANNING, "GC", "🔥 古い記憶を焼却し、整理された新しい記憶を構築中...")
        success = memory.rebuild_memory_from_gc(cleaned_json)
        
        if success:
            update_phase(Phase.DONE, "FINISH", "✨🎉 ガベージコレクション完了！大図書館は美しく最適化されたわ！💋")
        else:
            update_phase(Phase.DONE, "ERROR", "❌ 記憶の再構築中に致命的なエラーが発生したわ...")
            
        return True

    return False