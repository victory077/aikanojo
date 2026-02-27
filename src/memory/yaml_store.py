"""YAML記憶ストア - 既存の3層記憶システム（短期・中期・長期）

ChromaDB導入後も互換レイヤーとして残す。
長期記憶（permanent）と短期記憶（recent）のKV保存を担当。
"""
import yaml
from pathlib import Path
from datetime import datetime

MAX_PERMANENT_LENGTH = 300  # 長期記憶の最大文字数
MAX_RECENT_LENGTH = 200    # 短期記憶の最大文字数
MAX_TOPICS = 10            # 中期記憶の最大件数

# デフォルトパス（ManagerやChromaStoreから上書き可能）
DEFAULT_MEMORY_FILE = Path(__file__).parent.parent.parent / "data" / "user_memory.yaml"


class YAMLMemoryStore:
    """YAMLベースの記憶ストレージ

    既存のYAML形式の記憶データを読み書きする。
    ChromaDBと併用して、構造化データ（permanent/recent）の保存を担当。
    """

    def __init__(self, memory_file: Path | None = None):
        self._file = memory_file or DEFAULT_MEMORY_FILE
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict:
        """YAMLファイルから記憶データを読み込む"""
        if self._file.exists():
            try:
                with open(self._file, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError):
                return {}
        return {}

    def _save(self) -> None:
        """記憶データをYAMLファイルに保存する"""
        self._file.parent.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w", encoding="utf-8") as f:
            yaml.dump(self._data, f, allow_unicode=True, default_flow_style=False)

    def _ensure_user(self, user_id: str) -> dict:
        """ユーザーのデータ構造を確保"""
        user_id = str(user_id)
        if user_id not in self._data:
            self._data[user_id] = {
                "permanent": "",
                "topics": [],
                "recent": ""
            }
        return self._data[user_id]

    # === 長期記憶(permanent) ===
    def get_permanent(self, user_id: str) -> str:
        """長期記憶を取得(名前、好み、約束など)"""
        user = self._ensure_user(user_id)
        return user.get("permanent", "")

    def update_permanent(self, user_id: str, content: str) -> None:
        """長期記憶を更新"""
        user = self._ensure_user(user_id)
        if len(content) > MAX_PERMANENT_LENGTH:
            content = content[:MAX_PERMANENT_LENGTH]
        user["permanent"] = content
        self._save()

    # === 短期記憶(recent) ===
    def get_recent(self, user_id: str) -> str:
        """短期記憶を取得(直近の会話要約)"""
        user = self._ensure_user(user_id)
        return user.get("recent", "")

    def update_recent(self, user_id: str, content: str) -> None:
        """短期記憶を更新"""
        user = self._ensure_user(user_id)
        if len(content) > MAX_RECENT_LENGTH:
            content = content[:MAX_RECENT_LENGTH]
        user["recent"] = content
        self._save()

    # === 中期記憶(topics) ===
    def get_topics(self, user_id: str) -> list[str]:
        """全ての中期記憶を取得"""
        user = self._ensure_user(user_id)
        return user.get("topics", [])

    def get_relevant_topics(self, user_id: str, message: str) -> list[str]:
        """ユーザーの発言に関連する中期記憶を取得(キーワードマッチ)"""
        topics = self.get_topics(user_id)
        if not topics or not message:
            return []

        message_lower = message.lower()
        relevant = []
        for topic in topics:
            topic_content = topic.split("|")[0] if "|" in topic else topic
            words = topic_content.replace("の話", "").replace("の約束", "").split()
            for word in words:
                if len(word) >= 2 and word.lower() in message_lower:
                    relevant.append(topic)
                    break

        return relevant[:3]

    def add_topic(self, user_id: str, topic: str) -> None:
        """中期記憶にトピックを追加"""
        user = self._ensure_user(user_id)
        topics = user.get("topics", [])

        today = datetime.now().strftime("%Y-%m-%d")
        topic_with_date = f"{topic}|{today}"

        topics = [t for t in topics if not t.startswith(topic.split("|")[0])]
        topics.insert(0, topic_with_date)

        user["topics"] = topics[:MAX_TOPICS]
        self._save()


def build_memory_update_prompt(old_permanent: str, old_recent: str,
                                user_msg: str, bot_reply: str) -> str:
    """記憶更新用のプロンプトを構築(3層対応)"""
    return f"""会話から記憶を更新してください。

[ルール]
- 比喩・アナロジー禁止(事実のみ)
- 異なるトピックを無理に結びつけない
- 簡潔に(略語OK)

[現在の基本情報]
{old_permanent if old_permanent else "(なし)"}

[直近の記憶]
{old_recent if old_recent else "(なし)"}

[新しい会話]
U:{user_msg[:150]}
B:{bot_reply[:150]}

以下の形式で出力:
PERMANENT: 名前/好み/約束(変更あれば)
RECENT: 今回の会話の要約(1行)
TOPIC: 新しい話題があれば(なければ空)"""
