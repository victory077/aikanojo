"""linter.py のユニットテスト"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestFormatForDiscord:
    """format_for_discord関数のテスト"""
    
    def test_basic_text(self):
        """通常テキストはそのまま"""
        from linter import format_for_discord
        text = "こんにちは！"
        assert format_for_discord(text) == "こんにちは！"
    
    def test_strip_whitespace(self):
        """先頭・末尾の空白を削除"""
        from linter import format_for_discord
        text = "  こんにちは  \n\n"
        assert format_for_discord(text) == "こんにちは"
    
    def test_reduce_empty_lines(self):
        """連続空行を2つまでに制限"""
        from linter import format_for_discord
        text = "あ\n\n\n\n\nい"
        result = format_for_discord(text)
        assert "\n\n\n" not in result
        assert "あ\n\nい" == result


class TestLoadLinterRules:
    """linter.yamlの読み込みテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d)
    
    def test_missing_file(self, temp_dir, monkeypatch):
        """ファイルがない場合は空辞書"""
        import linter
        monkeypatch.setattr(linter, "LINTER_FILE", temp_dir / "missing.yaml")
        
        rules = linter.load_linter_rules()
        assert rules == {}
    
    def test_load_rules(self, temp_dir, monkeypatch):
        """ルールファイルの読み込み"""
        import linter
        import yaml
        
        test_file = temp_dir / "test_linter.yaml"
        test_file.write_text(
            yaml.dump({"forbidden_patterns": ["test"]}),
            encoding="utf-8"
        )
        monkeypatch.setattr(linter, "LINTER_FILE", test_file)
        
        rules = linter.load_linter_rules()
        assert "forbidden_patterns" in rules
        assert "test" in rules["forbidden_patterns"]
