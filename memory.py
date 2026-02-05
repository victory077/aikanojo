"""ユーザー記憶管理モジュール - 会話の重要情報を圧縮保存"""
import json
from pathlib import Path
from typing import Optional

MEMORY_FILE = Path(__file__).parent / "user_memory.json"
MAX_MEMORY_LENGTH = 2000  # 最大文字数


class MemoryManager:
    """ユーザーごとの記憶を管理するクラス"""
    
    def __init__(self):
        self._data: dict[str, str] = self._load()
    
    def _load(self) -> dict:
        """JSONファイルから記憶データを読み込む"""
        if MEMORY_FILE.exists():
            try:
                with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save(self) -> None:
        """記憶データをJSONファイルに保存する"""
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def get_memory(self, user_id: str) -> str:
        """ユーザーの記憶を取得"""
        return self._data.get(str(user_id), "")
    
    def update_memory(self, user_id: str, new_memory: str) -> None:
        """ユーザーの記憶を更新（上限制限付き）"""
        user_id = str(user_id)
        # 上限を超えないように切り詰め
        if len(new_memory) > MAX_MEMORY_LENGTH:
            new_memory = new_memory[:MAX_MEMORY_LENGTH]
        self._data[user_id] = new_memory
        self._save()
    
    def has_memory(self, user_id: str) -> bool:
        """記憶があるかどうか"""
        return str(user_id) in self._data and len(self._data[str(user_id)]) > 0


def build_memory_update_prompt(old_memory: str, user_msg: str, bot_reply: str) -> str:
    """記憶更新用のプロンプトを構築"""
    return f"""既存の記憶と新しい会話から、重要情報を圧縮して更新してください。

【ルール】
- 出力は2000文字以内
- 効率的な形式で保存（略語OK、記号OK）
- 重要度: 名前>好み>約束>話題
- 古い/些細な情報は削除可
- 出力は記憶データのみ（説明不要）

【既存記憶】
{old_memory if old_memory else "(なし)"}

【新しい会話】
U:{user_msg[:200]}
B:{bot_reply[:200]}

【更新後の記憶】"""
