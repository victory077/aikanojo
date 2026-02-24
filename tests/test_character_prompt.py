"""character_prompt.pyのユニットテスト

テスト対象:
- build_character_generation_prompt: LLM向けプロンプトに必須情報が含まれるか
- build_greetings_generation_prompt: 挨拶生成プロンプトが正しく構築されるか
- extract_yaml_from_response: LLMレスポンスからYAML部分を正しく抽出できるか
- validate_character_yaml: 必須フィールドの検証が正しく動作するか
"""
import pytest
import sys
from pathlib import Path

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from character_prompt import (
    build_character_generation_prompt,
    build_greetings_generation_prompt,
    extract_yaml_from_response,
    validate_character_yaml,
)


class TestBuildCharacterGenerationPrompt:
    """build_character_generation_prompt関数のテスト"""

    def test_returns_non_empty_string(self):
        result = build_character_generation_prompt("学園アイドルマスター", "姫崎莉波")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_series_and_character(self):
        result = build_character_generation_prompt("鬼滅の刃", "竈門禰豆子")
        assert "鬼滅の刃" in result
        assert "竈門禰豆子" in result

    def test_contains_required_field_name(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "name:" in result

    def test_contains_required_field_base_prompt(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "base_prompt:" in result

    def test_contains_required_field_voice_examples(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "voice_examples:" in result

    def test_contains_required_field_affinity_levels(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "affinity_levels:" in result

    def test_contains_required_field_affinity_config(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "affinity_config:" in result

    def test_mentions_web_search(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "Web検索" in result

    def test_mentions_yaml_format(self):
        result = build_character_generation_prompt("テスト作品", "テストキャラ")
        assert "YAML" in result or "yaml" in result


class TestBuildGreetingsGenerationPrompt:
    """build_greetings_generation_prompt関数のテスト"""

    def test_returns_non_empty_string(self):
        result = build_greetings_generation_prompt("name: テスト")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_character_yaml(self):
        yaml_content = "name: 姫崎莉波\npersonality: 元気"
        result = build_greetings_generation_prompt(yaml_content)
        assert "姫崎莉波" in result

    def test_contains_time_slots(self):
        result = build_greetings_generation_prompt("name: テスト")
        assert "early_morning" in result
        assert "midnight" in result
        assert "startup" in result
        assert "shutdown" in result


class TestExtractYamlFromResponse:
    """extract_yaml_from_response関数のテスト"""

    def test_plain_yaml(self):
        text = "name: テスト\npersonality: 元気"
        assert extract_yaml_from_response(text) == text

    def test_yaml_in_code_fence(self):
        text = "以下がYAMLです:\n```yaml\nname: テスト\n```\n説明文"
        assert extract_yaml_from_response(text) == "name: テスト"

    def test_yaml_in_plain_code_fence(self):
        text = "```\nname: テスト\n```"
        assert extract_yaml_from_response(text) == "name: テスト"

    def test_strips_whitespace(self):
        text = "  \n  name: テスト  \n  "
        assert extract_yaml_from_response(text) == "name: テスト"


class TestValidateCharacterYaml:
    """validate_character_yaml関数のテスト"""

    def test_valid_yaml(self):
        yaml_content = """
name: テスト
base_prompt: |
  テストプロンプト
voice_examples:
  - "セリフ1"
affinity_levels:
  low:
    threshold: 0
affinity_config:
  initial: 20
"""
        valid, msg = validate_character_yaml(yaml_content)
        assert valid is True
        assert msg == ""

    def test_missing_required_field(self):
        yaml_content = "name: テスト\npersonality: 元気"
        valid, msg = validate_character_yaml(yaml_content)
        assert valid is False
        assert "必須フィールドが不足" in msg

    def test_invalid_yaml(self):
        yaml_content = "{{invalid yaml: ["
        valid, msg = validate_character_yaml(yaml_content)
        assert valid is False
        assert "YAML解析エラー" in msg

    def test_non_dict_yaml(self):
        yaml_content = "- item1\n- item2"
        valid, msg = validate_character_yaml(yaml_content)
        assert valid is False
        assert "dict形式" in msg
