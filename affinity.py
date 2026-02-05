"""ユーザー好感度管理モジュール"""
import json
from pathlib import Path
from typing import Optional

# 好感度データの保存先
AFFINITY_FILE = Path(__file__).parent / "user_affinity.json"


class AffinityManager:
    """ユーザーごとの好感度を管理するクラス"""
    
    def __init__(self, initial_affinity: int = 20, max_affinity: int = 100, min_affinity: int = 0):
        self.initial_affinity = initial_affinity
        self.max_affinity = max_affinity
        self.min_affinity = min_affinity
        self._data: dict[str, dict] = self._load()
    
    def _load(self) -> dict:
        """JSONファイルから好感度データを読み込む"""
        if AFFINITY_FILE.exists():
            try:
                with open(AFFINITY_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def _save(self) -> None:
        """好感度データをJSONファイルに保存する"""
        with open(AFFINITY_FILE, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
    
    def get_affinity(self, user_id: str) -> int:
        """ユーザーの好感度を取得する"""
        user_id = str(user_id)
        if user_id not in self._data:
            self._data[user_id] = {
                "affinity": self.initial_affinity,
                "message_count": 0
            }
            self._save()
        return self._data[user_id]["affinity"]
    
    def add_affinity(self, user_id: str, amount: int = 1) -> int:
        """好感度を加算する（範囲内に収める）"""
        user_id = str(user_id)
        current = self.get_affinity(user_id)
        new_affinity = max(self.min_affinity, min(self.max_affinity, current + amount))
        self._data[user_id]["affinity"] = new_affinity
        self._data[user_id]["message_count"] = self._data[user_id].get("message_count", 0) + 1
        self._save()
        return new_affinity
    
    def set_affinity(self, user_id: str, value: int) -> int:
        """好感度を直接設定する"""
        user_id = str(user_id)
        value = max(self.min_affinity, min(self.max_affinity, value))
        if user_id not in self._data:
            self._data[user_id] = {"message_count": 0}
        self._data[user_id]["affinity"] = value
        self._save()
        return value
    
    def get_stats(self, user_id: str) -> dict:
        """ユーザーの統計情報を取得する"""
        user_id = str(user_id)
        if user_id not in self._data:
            return {"affinity": self.initial_affinity, "message_count": 0}
        return self._data[user_id]


def get_affinity_level(affinity: int, levels: dict) -> tuple[str, str]:
    """
    好感度に応じたレベル名とプロンプト追加文を返す
    
    Args:
        affinity: 現在の好感度
        levels: character.yamlのaffinity_levels
    
    Returns:
        (レベル名, プロンプト追加文)
    """
    # しきい値でソート（降順）
    sorted_levels = sorted(
        levels.items(),
        key=lambda x: x[1].get("threshold", 0),
        reverse=True
    )
    
    for level_name, level_data in sorted_levels:
        if affinity >= level_data.get("threshold", 0):
            return level_data.get("description", level_name), level_data.get("prompt_addition", "")
    
    # デフォルト（最低レベル）
    first_level = list(levels.values())[0]
    return first_level.get("description", ""), first_level.get("prompt_addition", "")
