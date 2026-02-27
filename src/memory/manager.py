"""統合記憶マネージャー - YAML記憶 + ChromaDBベクトル記憶を統合

既存のYAML 3層記憶システムとChromaDBベクトル検索を統合し、
プロンプト構築用の記憶テキストを一元的に提供する。
CRAG（Corrective RAG）により検索結果の妥当性をLLMで評価可能。
"""
from pathlib import Path
from typing import Callable
from memory.yaml_store import YAMLMemoryStore, build_memory_update_prompt
from memory.chroma_store import ChromaMemoryStore
from memory.crag_evaluator import (
    build_crag_evaluation_prompt,
    parse_crag_result,
    filter_memories_by_crag,
)


class MemoryManager:
    """YAML記憶 + ChromaDBを統合した記憶マネージャー

    既存の3層記憶（permanent/recent/topics）を維持しつつ、
    ChromaDBによるセマンティック検索を追加。
    CRAG評価で検索結果の妥当性を判定。

    - **permanent（長期）**: 名前、好み、約束 → YAMLに保存
    - **recent（短期）**: 直近の会話要約 → YAMLに保存
    - **topics（中期）**: 会話トピック → YAMLに保存（キーワードマッチ）
    - **ベクトル記憶**: 全会話ログ → ChromaDBに保存（セマンティック検索）
    """

    def __init__(self, memory_file: Path | None = None,
                 chroma_dir: Path | None = None):
        self._yaml = YAMLMemoryStore(memory_file)
        self._chroma = ChromaMemoryStore(chroma_dir)

    def close(self) -> None:
        """リソースを解放する（テスト用・Windows対応）"""
        self._chroma.close()

    # === YAML記憶のデリゲート ===
    def get_permanent(self, user_id: str) -> str:
        return self._yaml.get_permanent(user_id)

    def update_permanent(self, user_id: str, content: str) -> None:
        self._yaml.update_permanent(user_id, content)

    def get_recent(self, user_id: str) -> str:
        return self._yaml.get_recent(user_id)

    def update_recent(self, user_id: str, content: str) -> None:
        self._yaml.update_recent(user_id, content)

    def get_topics(self, user_id: str) -> list[str]:
        return self._yaml.get_topics(user_id)

    def add_topic(self, user_id: str, topic: str) -> None:
        self._yaml.add_topic(user_id, topic)

    # === ChromaDB記憶 ===
    def save_conversation(self, user_id: str, user_message: str,
                           bot_reply: str) -> str:
        """会話ターンをChromaDBに保存する

        Returns:
            生成されたドキュメントID
        """
        return self._chroma.add_conversation(user_id, user_message, bot_reply)

    def search_similar(self, user_id: str, query: str,
                        n_results: int = 5) -> list[dict]:
        """セマンティック検索で関連する過去の会話を取得する"""
        return self._chroma.search(user_id, query, n_results)

    # === 統合取得（プロンプト用）===
    def get_memory_for_prompt(
        self,
        user_id: str,
        user_message: str = "",
        llm_simple: Callable[[str], str] | None = None,
    ) -> str:
        """プロンプト用に整形された記憶を取得する

        YAML記憶（permanent/recent）+ ChromaDBセマンティック検索の結果を統合。
        llm_simpleが渡された場合はCRAG評価で検索結果をフィルタリングする。

        Args:
            user_id: ユーザーID
            user_message: ユーザーの発言（セマンティック検索に使用）
            llm_simple: LLM呼び出し関数（CRAG評価用、省略時はフィルタなし）

        Returns:
            プロンプトに挿入可能な記憶テキスト
        """
        parts = []

        # 1. 長期記憶(常に含める)
        permanent = self.get_permanent(user_id)
        if permanent:
            parts.append(f"[基本情報] {permanent}")

        # 2. 短期記憶(常に含める)
        recent = self.get_recent(user_id)
        if recent:
            parts.append(f"[直近] {recent}")

        # 3. ChromaDBセマンティック検索 + CRAG評価
        if user_message:
            similar = self._chroma.search(user_id, user_message, n_results=5)
            if similar:
                # CRAG評価（llm_simpleが渡された場合のみ）
                if llm_simple and len(similar) > 0:
                    try:
                        crag_prompt = build_crag_evaluation_prompt(
                            user_message, similar
                        )
                        crag_result = llm_simple(crag_prompt)
                        relevance = parse_crag_result(crag_result, len(similar))
                        similar = filter_memories_by_crag(similar, relevance)
                    except Exception:
                        pass  # CRAG評価失敗時は全件含める

                if similar:
                    chroma_text = self._chroma.format_for_prompt(
                        similar, max_chars=400
                    )
                    if chroma_text:
                        parts.append(f"[関連する過去の会話]\n{chroma_text}")

        # 4. YAMLの中期記憶（キーワードマッチ、フォールバック）
        if user_message:
            relevant_topics = self._yaml.get_relevant_topics(user_id, user_message)
            if relevant_topics:
                topics_str = "、".join([t.split("|")[0] for t in relevant_topics])
                parts.append(f"[関連過去話題] {topics_str}")

        return "\n".join(parts) if parts else ""

