import os
import json
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import chromadb
from pathlib import Path

# ロガーの名前を "ARK.Memory" に統一 💋
logger = logging.getLogger("ARK.Memory")

class MemoryManager:
    """
    ARK's Tiered Memory System (The Deep Archives)
    Tier 2: Core Knowledge (JSON) - Rules that are always in context.
    Tier 3: Episodic Archive (ChromaDB) - Optimized for Cosine Similarity with Metadata.
    """
    def __init__(self, base_dir: str = "data/memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Tier 2: Core Rules Path
        self.core_rules_path = self.base_dir / "core_rules.json"
        if not self.core_rules_path.exists():
            with open(self.core_rules_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # Tier 3: Episodic Memory (ChromaDB)
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.base_dir / "chroma_db")
            )
            # metadata で 'hnsw:space': 'cosine' を指定して意味検索を強化 💋
            self.collection = self.chroma_client.get_or_create_collection(
                name="ark_experiences",
                metadata={"hnsw:space": "cosine"}
            )
            logger.debug("ChromaDB initialized with Cosine Similarity.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def load_core_rules_prompt(self) -> str:
        """システムプロンプト用のコアルールを取得"""
        try:
            with open(self.core_rules_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            if not rules:
                return "現在、特定のプロジェクト・コアルールは設定されていません。"
            
            formatted = "\n".join([f"- {k}: {v}" for k, v in rules.items()])
            return f"\n### 📌 現在適用されているコアルール\n{formatted}\n"
        except Exception as e:
            logger.error(f"Failed to load core rules: {e}")
            return ""

    def save_core_rule(self, key: str, value: str):
        """Tier 2 (JSON) に掟を保存"""
        try:
            with open(self.core_rules_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            rules[key] = value
            with open(self.core_rules_path, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=4, ensure_ascii=False)
            logger.info(f"Core rule saved: {key}")
        except Exception as e:
            logger.error(f"Failed to save core rule: {e}")

    def archive_experience(self, summary: str, source: str = "local_execution", trust_level: str = "verified", role: str = "general"):
        """Tier 3 (ChromaDB) に知見を保存（ロールのメタデータ付き）💋"""
        if not self.collection:
            return
        
        try:
            doc_id = f"mem_{int(time.time() * 1000)}"
            metadata = {
                "source": source,
                "trust_level": trust_level,
                "timestamp": datetime.now().isoformat(),
                "role": role  # 🌟 NEW: 誰の記憶かをタグ付け！
            }
            self.collection.add(
                documents=[summary],
                metadatas=[metadata],
                ids=[doc_id]
            )
            logger.info(f"Experience archived [{doc_id}] (Role: {role}, Source: {source})")
        except Exception as e:
            logger.error(f"Failed to archive experience: {e}")

    def recall_memory(self, query: str, n_results: int = 3, role: Optional[str] = None) -> str:
        """類似する過去の記憶を検索（ロールで絞り込み可能！）💋"""
        if not self.collection:
            return ""
            
        try:
            # 🌟 NEW: role が指定されていれば、そのロールの記憶だけを Where 句で絞り込む！
            where_clause = {"role": role} if role else None
            
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
            
            docs = results.get("documents", [[]])[0]
            if not docs:
                return "" # 見つからなかった時は空文字を返す（プロンプトを汚さないため）
            
            formatted = "\n".join([f"- {doc}" for doc in docs])
            return f"\n### 🧠 {role.capitalize() if role else 'General'} の過去の教訓（地雷マップ）\n{formatted}\n"
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return ""

    def _get_collection(self):
        """ChromaDBのコレクション変数を安全に取得するヘルパーよ💋"""
        return getattr(self, '_collection', None) or getattr(self, 'collection', None)

    def dump_memory(self, limit: int = 50) -> str:
        """
        記憶の全件（最大 limit 件）をフォーマットして返すわ💋
        /memory コマンドで呼び出されるメソッドよ！
        """
        col = self._get_collection()
        if not col:
            return "📭 記憶システム（ChromaDB）が初期化されていないか、オフラインよ。"
        
        try:
            # ChromaDBからメタデータとドキュメントを取得
            results = col.get(limit=limit, include=["documents", "metadatas"])
            
            if not results or not results["ids"]:
                return "📭 大図書館にはまだ何も記録されていません。"
            
            output = ["📚 【大図書館の記憶一覧】"]
            output.append("=" * 60)
            
            for i in range(len(results["ids"])):
                mem_id = results["ids"][i]
                doc = results["documents"][i]
                meta = results["metadatas"][i]
                
                # メタデータを綺麗に文字列化
                meta_str = ", ".join([f"{k}: {v}" for k, v in meta.items()]) if meta else "タグなし"
                # 長いテキストは省略して見やすく！
                short_doc = doc[:150].replace('\n', ' ') + "..." if len(doc) > 150 else doc.replace('\n', ' ')
                
                output.append(f"🔹 ID: {mem_id}")
                output.append(f"   🏷️ : [{meta_str}]")
                output.append(f"   📝 : {short_doc}")
                output.append("-" * 60)
                
            return "\n".join(output)
            
        except Exception as e:
            logger.error(f"Failed to dump memory: {e}")
            return f"❌ 記憶の抽出に失敗しました: {e}"

    def delete_memory(self, memory_id: str) -> bool:
        """
        指定されたIDの記憶を永久に消去するわ💋
        /forget コマンドで呼び出されるメソッドよ！
        """
        col = self._get_collection()
        if not col:
            return False
        
        try:
            # まずはそのIDが存在するか確認するわ
            check = col.get(ids=[memory_id])
            if not check or not check["ids"]:
                logger.warning(f"Memory ID '{memory_id}' は見つからなかったわ。")
                return False
                
            # 存在すれば ChromaDB から削除！
            col.delete(ids=[memory_id])
            logger.info(f"🗑️ 記憶を削除しました: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete memory {memory_id}: {e}")
            return False

    # =========================================================================
    # 🧹 [NEW PHASE 10-2] 記憶のガベージコレクション用メソッド群 💋
    # =========================================================================

    def get_all_memory_dump(self) -> str:
        """
        現在のすべての記憶（Tier 2 & Tier 3）を抽出し、JSON文字列として返すわ💋
        司書（Reflector）に渡して整理させるための生データよ！
        """
        dump_data = {
            "core_rules": {},
            "experiences": []
        }
        
        # 1. Tier 2: Core Rules を取得
        try:
            with open(self.core_rules_path, "r", encoding="utf-8") as f:
                dump_data["core_rules"] = json.load(f)
        except Exception as e:
            logger.error(f"Failed to read core rules for GC dump: {e}")

        # 2. Tier 3: Experiences (ChromaDB) を取得
        col = self._get_collection()
        if col:
            try:
                results = col.get(include=["documents", "metadatas"])
                if results and results["ids"]:
                    for i in range(len(results["ids"])):
                        doc = results["documents"][i]
                        meta = results["metadatas"][i] or {}
                        dump_data["experiences"].append({
                            "summary": doc,
                            "source": meta.get("source", "unknown"),
                            "trust_level": meta.get("trust_level", "unknown")
                        })
            except Exception as e:
                logger.error(f"Failed to read experiences for GC dump: {e}")
                
        # LLMが読みやすいように綺麗にフォーマットして返すわ
        return json.dumps(dump_data, ensure_ascii=False, indent=2)

    def rebuild_memory_from_gc(self, gc_data: Dict[str, Any]) -> bool:
        """
        司書（Reflector）が整理した新しいJSONデータを元に、
        現在の記憶をすべて一度焼却し、美しく再構築するわ💋
        """
        logger.info("🔥 [MemoryManager] 記憶の破壊と創造（再構築）を開始します...")
        
        try:
            # 1. Tier 2: Core Rules の再構築
            new_core_rules = gc_data.get("core_rules", {})
            with open(self.core_rules_path, "w", encoding="utf-8") as f:
                json.dump(new_core_rules, f, indent=4, ensure_ascii=False)
            logger.info(f"✅ Tier 2: {len(new_core_rules)} 件のコアルールを再構築しました！")

            # 2. Tier 3: Experiences (ChromaDB) の再構築
            col = self._get_collection()
            if col:
                # 🔥 既存の記憶をすべて取得して焼却（Delete）
                existing = col.get()
                if existing and existing["ids"]:
                    col.delete(ids=existing["ids"])
                    logger.info(f"🗑️ Tier 3: 既存の記憶 {len(existing['ids'])} 件を完全に焼却しました。")

                # ✨ 整理された新しい記憶を注入
            new_experiences = gc_data.get("experiences", [])
            for exp in new_experiences:
                # 🌟 [Resilience Fix] 文字列が来ても辞書が来ても大丈夫なようにガードを入れるわ！
                if isinstance(exp, str):
                    summary = exp
                    source = "gc_rebuild"
                    trust_level = "verified"
                else:
                    # 辞書の場合は get で安全に取得
                    summary = exp.get("summary")
                    source = exp.get("source", "gc_rebuild")
                    trust_level = exp.get("trust_level", "verified")
                
                if summary:
                    # archive_experience を呼び出す（role 引数は Step 3 で追加したものね💋）
                    self.archive_experience(summary, source, trust_level, role="general")
                    time.sleep(0.01)
                        
                logger.info(f"✅ Tier 3: {len(new_experiences)} 件の知見を再構築しました！")

            return True

        except Exception as e:
            logger.error(f"❌ 記憶の再構築中に致命的なエラーが発生しました: {e}")
            return False