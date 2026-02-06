"""ユーザー記憶管理モジュール - 3層構造（短期・中期・長期）"""
import yaml
from pathlib import Path
from typing import Optional
from datetime import datetime

MEMORY_FILE = Path(__file__).parent.parent / "data" / "user_memory.yaml"
MAX_PERMANENT_LENGTH = 300  # 長期記憶の最大文字数
MAX_RECENT_LENGTH = 200    # 短期記憶の最大文字数
MAX_TOPICS = 10            # 中期記憶の最大件数


class MemoryManager:
    """ユーザーごとの記憶を3層で管理するクラス"""
    
    def __init__(self):
        self._data: dict[str, dict] = self._load()
    
    def _load(self) -> dict:
        """YAMLファイルから記憶データを読み込む"""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except (yaml.YAMLError, IOError):
                return {}
        return {}
    
    def _save(self) -> None:
        """記憶データをYAMLファイルに保存する"""
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
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
    
    # === 長期記憶（permanent）===
    def get_permanent(self, user_id: str) -> str:
        """長期記憶を取得（名前、好み、約束など）"""
        user = self._ensure_user(user_id)
        return user.get("permanent", "")
    
    def update_permanent(self, user_id: str, content: str) -> None:
        """長期記憶を更新"""
        user = self._ensure_user(user_id)
        if len(content) > MAX_PERMANENT_LENGTH:
            content = content[:MAX_PERMANENT_LENGTH]
        user["permanent"] = content
        self._save()
    
    # === 短期記憶（recent）===
    def get_recent(self, user_id: str) -> str:
        """短期記憶を取得（直近の会話要約）"""
        user = self._ensure_user(user_id)
        return user.get("recent", "")
    
    def update_recent(self, user_id: str, content: str) -> None:
        """短期記憶を更新"""
        user = self._ensure_user(user_id)
        if len(content) > MAX_RECENT_LENGTH:
            content = content[:MAX_RECENT_LENGTH]
        user["recent"] = content
        self._save()
    
    # === 中期記憶（topics）===
    def get_topics(self, user_id: str) -> list[str]:
        """全ての中期記憶を取得"""
        user = self._ensure_user(user_id)
        return user.get("topics", [])
    
    def get_relevant_topics(self, user_id: str, message: str) -> list[str]:
        """ユーザーの発言に関連する中期記憶を取得（キーワードマッチ）"""
        topics = self.get_topics(user_id)
        if not topics or not message:
            return []
        
        # 簡易キーワードマッチ
        message_lower = message.lower()
        relevant = []
        for topic in topics:
            # トピックからキーワードを抽出（|の前の部分）
            topic_content = topic.split("|")[0] if "|" in topic else topic
            # 単語を抽出してマッチ確認
            words = topic_content.replace("の話", "").replace("の約束", "").split()
            for word in words:
                if len(word) >= 2 and word.lower() in message_lower:
                    relevant.append(topic)
                    break
        
        return relevant[:3]  # 最大3件
    
    def add_topic(self, user_id: str, topic: str) -> None:
        """中期記憶にトピックを追加"""
        user = self._ensure_user(user_id)
        topics = user.get("topics", [])
        
        # 日付を付与
        today = datetime.now().strftime("%Y-%m-%d")
        topic_with_date = f"{topic}|{today}"
        
        # 重複チェック（同じトピックは更新）
        topics = [t for t in topics if not t.startswith(topic.split("|")[0])]
        topics.insert(0, topic_with_date)
        
        # 最大件数に制限
        user["topics"] = topics[:MAX_TOPICS]
        self._save()
    
    # === 統合取得（プロンプト用）===
    def get_memory_for_prompt(self, user_id: str, user_message: str = "") -> str:
        """プロンプト用に整形された記憶を取得"""
        parts = []
        
        # 長期記憶（常に含める）
        permanent = self.get_permanent(user_id)
        if permanent:
            parts.append(f"【基本情報】{permanent}")
        
        # 短期記憶（常に含める）
        recent = self.get_recent(user_id)
        if recent:
            parts.append(f"【直近】{recent}")
        
        # 中期記憶（関連するものだけ）
        if user_message:
            relevant = self.get_relevant_topics(user_id, user_message)
            if relevant:
                topics_str = "、".join([t.split("|")[0] for t in relevant])
                parts.append(f"【関連する過去の話題】{topics_str}")
        
        return "\n".join(parts) if parts else ""
    
    # === 旧API互換 ===
    def get_memory(self, user_id: str) -> str:
        """旧API互換: 全記憶を取得"""
        return self.get_memory_for_prompt(user_id)
    
    def update_memory(self, user_id: str, new_memory: str) -> None:
        """旧API互換: 記憶を更新（短期記憶として）"""
        self.update_recent(user_id, new_memory)
    
    def has_memory(self, user_id: str) -> bool:
        """記憶があるかどうか"""
        user_id = str(user_id)
        if user_id not in self._data:
            return False
        user = self._data[user_id]
        return bool(user.get("permanent") or user.get("recent") or user.get("topics"))


def build_memory_update_prompt(old_permanent: str, old_recent: str, 
                                user_msg: str, bot_reply: str) -> str:
    """記憶更新用のプロンプトを構築（3層対応）"""
    return f"""会話から記憶を更新してください。

【ルール】
- 比喩・アナロジー禁止（事実のみ）
- 異なるトピックを無理に結びつけない
- 簡潔に（略語OK）

【現在の基本情報】
{old_permanent if old_permanent else "(なし)"}

【直近の記憶】
{old_recent if old_recent else "(なし)"}

【新しい会話】
U:{user_msg[:150]}
B:{bot_reply[:150]}

以下の形式で出力:
PERMANENT: 名前/好み/約束（変更あれば）
RECENT: 今回の会話の要約（1行）
TOPIC: 新しい話題があれば（なければ空）"""
