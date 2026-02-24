"""main.pyの挨拶機能(get_time_greeting)のユニットテスト"""
import pytest
import sys
from pathlib import Path
from unittest.mock import patch

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestGetTimeKeyStartup:
    """_get_time_key_startup関数のテスト"""

    def test_early_morning(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(5) == "early_morning"
        assert _get_time_key_startup(9) == "early_morning"

    def test_late_morning(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(10) == "late_morning"
        assert _get_time_key_startup(11) == "late_morning"

    def test_noon(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(12) == "noon"
        assert _get_time_key_startup(13) == "noon"

    def test_afternoon(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(14) == "afternoon"
        assert _get_time_key_startup(16) == "afternoon"

    def test_evening(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(17) == "evening"
        assert _get_time_key_startup(20) == "evening"

    def test_night(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(21) == "night"
        assert _get_time_key_startup(23) == "night"

    def test_midnight(self):
        from main import _get_time_key_startup
        assert _get_time_key_startup(0) == "midnight"
        assert _get_time_key_startup(4) == "midnight"


class TestGetTimeKeyShutdown:
    """_get_time_key_shutdown関数のテスト"""

    def test_morning(self):
        from main import _get_time_key_shutdown
        assert _get_time_key_shutdown(5) == "morning"
        assert _get_time_key_shutdown(11) == "morning"

    def test_afternoon(self):
        from main import _get_time_key_shutdown
        assert _get_time_key_shutdown(12) == "afternoon"
        assert _get_time_key_shutdown(16) == "afternoon"

    def test_evening(self):
        from main import _get_time_key_shutdown
        assert _get_time_key_shutdown(17) == "evening"
        assert _get_time_key_shutdown(20) == "evening"

    def test_night(self):
        from main import _get_time_key_shutdown
        assert _get_time_key_shutdown(21) == "night"
        assert _get_time_key_shutdown(23) == "night"

    def test_midnight(self):
        from main import _get_time_key_shutdown
        assert _get_time_key_shutdown(0) == "midnight"
        assert _get_time_key_shutdown(4) == "midnight"
