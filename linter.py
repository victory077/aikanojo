"""出力整形モジュール - Discord向けにLLM出力を修正"""
import re
import yaml
from pathlib import Path

LINTER_FILE = Path(__file__).parent / "linter.yaml"


def load_linter_rules() -> dict:
    """linter.yamlからルールを読み込む"""
    if LINTER_FILE.exists():
        with open(LINTER_FILE, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def format_for_discord(text: str) -> str:
    """LLM出力をDiscord向けに整形する"""
    rules = load_linter_rules()
    
    # 禁止パターンを削除
    for pattern in rules.get("forbidden_patterns", []):
        text = text.replace(pattern, "```")
    
    # 置換ルールを適用
    for rule in rules.get("replacements", []):
        pattern = rule.get("pattern", "")
        replacement = rule.get("replacement", "")
        flags_str = rule.get("flags", "")
        
        flags = 0
        if "multiline" in flags_str:
            flags |= re.MULTILINE
        if "ignorecase" in flags_str:
            flags |= re.IGNORECASE
        
        try:
            text = re.sub(pattern, replacement, text, flags=flags)
        except re.error:
            pass  # 正規表現エラーは無視
    
    # 空行の連続を2つまでに制限
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 先頭・末尾の空白を削除
    text = text.strip()
    
    return text
