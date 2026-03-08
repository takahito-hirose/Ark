import os
import json
import logging
import time
from typing import List, Dict, Any, Optional
import chromadb
from pathlib import Path

# 👇 ロガーの名前を "ARK.Memory" にして、Orchestrator等とフォーマットを統一！💋
logger = logging.getLogger("ARK.Memory")

class MemoryManager:
    """
    ARK's Tiered Memory System
    Tier 2: Core Knowledge (JSON) - Rules that are always in context.
    Tier 3: Episodic Archive (ChromaDB) - Experiences recalled only when needed.
    """
    def __init__(self, base_dir: str = "data/memory"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Tier 2: Core Rules Path (JSON for persistent constraints)
        self.core_rules_path = self.base_dir / "core_rules.json"
        if not self.core_rules_path.exists():
            with open(self.core_rules_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

        # Tier 3: Episodic Memory (ChromaDB for vector search)
        try:
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.base_dir / "chroma_db")
            )
            self.collection = self.chroma_client.get_or_create_collection(name="ark_experiences")
            logger.debug("ChromaDB initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.collection = None

    def load_core_rules_prompt(self) -> str:
        """Returns core rules as a formatted string for the system prompt."""
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
        """Saves a permanent rule to the JSON store."""
        try:
            with open(self.core_rules_path, "r", encoding="utf-8") as f:
                rules = json.load(f)
            
            rules[key] = value
            
            with open(self.core_rules_path, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=4, ensure_ascii=False)
            logger.info(f"Core rule saved: {key}")
        except Exception as e:
            logger.error(f"Failed to save core rule: {e}")

    def archive_experience(self, summary: str):
        """Archives a lesson or solution into vector storage."""
        if not self.collection:
            logger.warning("Cannot archive experience: ChromaDB collection is not available.")
            return
        
        try:
            doc_id = f"exp_{int(time.time())}"
            self.collection.add(
                documents=[summary],
                ids=[doc_id]
            )
            logger.info(f"Experience archived to Tier 3 storage: {summary[:50]}...")
        except Exception as e:
            logger.error(f"Failed to archive experience: {e}")

    def recall_memory(self, query: str, n_results: int = 3) -> str:
        """Searches vector storage for similar past experiences."""
        if not self.collection:
            return "記憶システム（ChromaDB）が利用できません。"
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            docs = results.get("documents", [[]])[0]
            if not docs:
                return "関連する過去の記憶は見つかりませんでした。"
            
            formatted = "\n".join([f"- {doc}" for doc in docs])
            return f"\n### 🔍 過去の記録からの抜粋\n{formatted}\n"
        except Exception as e:
            logger.error(f"Failed to recall memory: {e}")
            return "記憶の検索中にエラーが発生しました。"