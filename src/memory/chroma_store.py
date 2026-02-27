"""ChromaDBベクトル記憶ストア - セマンティック検索による長期記憶

会話ログをベクトル埋め込みとして保存し、意味的に類似した過去の会話を検索する。
既存のYAML記憶（キーワードマッチ）を補完・置換するための新しい記憶層。
"""
import chromadb
from pathlib import Path
from datetime import datetime

# デフォルトの永続化ディレクトリ
DEFAULT_CHROMA_DIR = Path(__file__).parent.parent.parent / "data" / "chroma_db"


class ChromaMemoryStore:
    """ChromaDBを使ったベクトルベースの記憶ストレージ

    会話の各ターンを埋め込みベクトルとして保存し、
    セマンティック検索で関連する過去の会話を取得する。

    ChromaDBはデフォルトで sentence-transformers の
    all-MiniLM-L6-v2 を使用する（日本語もある程度対応）。
    """

    def __init__(self, persist_dir: Path | None = None, collection_name: str = "conversations"):
        self._persist_dir = persist_dir or DEFAULT_CHROMA_DIR
        self._persist_dir.mkdir(parents=True, exist_ok=True)

        self._client = chromadb.PersistentClient(
            path=str(self._persist_dir)
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_conversation(self, user_id: str, user_message: str,
                          bot_reply: str, metadata: dict | None = None) -> str:
        """会話ターンをベクトルDBに保存する

        ユーザーの発言とBotの返答を1つのドキュメントとして保存。

        Args:
            user_id: ユーザーID
            user_message: ユーザーの発言
            bot_reply: Botの返答
            metadata: 追加メタデータ

        Returns:
            生成されたドキュメントID
        """
        now = datetime.now()
        doc_id = f"{user_id}_{now.strftime('%Y%m%d_%H%M%S_%f')}"

        # ユーザーの発言 + Botの返答を結合して保存
        document = f"ユーザー: {user_message}\n返答: {bot_reply}"

        doc_metadata = {
            "user_id": user_id,
            "timestamp": now.isoformat(),
            "date": now.strftime("%Y-%m-%d"),
            "user_message": user_message[:500],  # メタデータとしても保存（検索結果表示用）
        }
        if metadata:
            doc_metadata.update(metadata)

        self._collection.add(
            ids=[doc_id],
            documents=[document],
            metadatas=[doc_metadata],
        )

        return doc_id

    def search(self, user_id: str, query: str, n_results: int = 5) -> list[dict]:
        """セマンティック検索で関連する過去の会話を取得する

        Args:
            user_id: ユーザーID（そのユーザーの記憶のみ検索）
            query: 検索クエリ（ユーザーの発言など）
            n_results: 取得件数

        Returns:
            関連する会話のリスト。各要素は
            {"document": str, "metadata": dict, "distance": float}
        """
        # そのユーザーの記憶のみをフィルタ
        results = self._collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"user_id": user_id},
        )

        conversations = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                conversations.append({
                    "document": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                })

        return conversations

    def close(self) -> None:
        """ChromaDBクライアントのリソースを解放する（テスト用・Windows対応）"""
        try:
            del self._collection
            del self._client
        except Exception:
            pass

    def get_conversation_count(self, user_id: str) -> int:
        """ユーザーの保存済み会話数を取得する"""
        try:
            result = self._collection.get(
                where={"user_id": user_id},
            )
            return len(result["ids"]) if result["ids"] else 0
        except Exception:
            return 0

    def format_for_prompt(self, conversations: list[dict],
                           max_chars: int = 500) -> str:
        """検索結果をプロンプト用テキストに整形する

        Args:
            conversations: search()の結果
            max_chars: 最大文字数

        Returns:
            プロンプトに挿入可能な整形済みテキスト
        """
        if not conversations:
            return ""

        parts = []
        total_chars = 0

        for conv in conversations:
            meta = conv.get("metadata", {})
            date = meta.get("date", "不明")
            doc = conv["document"]

            # 要約（長すぎる場合は切り詰め）
            entry = f"[{date}] {doc}"
            if total_chars + len(entry) > max_chars:
                remaining = max_chars - total_chars
                if remaining > 50:
                    entry = entry[:remaining] + "..."
                    parts.append(entry)
                break

            parts.append(entry)
            total_chars += len(entry)

        return "\n".join(parts)
