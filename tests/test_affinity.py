"""affinity.py のユニットテスト"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestAffinityManager:
    """AffinityManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d)
    
    @pytest.fixture
    def affinity_manager(self, temp_dir, monkeypatch):
        """テスト用AffinityManagerを作成"""
        import affinity
        test_file = temp_dir / "test_affinity.yaml"
        monkeypatch.setattr(affinity, "AFFINITY_FILE", test_file)
        return affinity.AffinityManager(initial_affinity=20, max_affinity=100, min_affinity=0)
    
    def test_initial_affinity(self, affinity_manager):
        """新規ユーザーの初期好感度"""
        assert affinity_manager.get_affinity("new_user") == 20
    
    def test_add_affinity(self, affinity_manager):
        """好感度の加算"""
        affinity_manager.get_affinity("user1")  # 初期化
        result = affinity_manager.add_affinity("user1", 5)
        assert result == 25
        assert affinity_manager.get_affinity("user1") == 25
    
    def test_add_negative_affinity(self, affinity_manager):
        """好感度の減算"""
        affinity_manager.get_affinity("user1")  # 初期化
        result = affinity_manager.add_affinity("user1", -10)
        assert result == 10
    
    def test_max_affinity_cap(self, affinity_manager):
        """好感度の上限（100）"""
        affinity_manager.get_affinity("user1")
        result = affinity_manager.add_affinity("user1", 1000)
        assert result == 100
    
    def test_min_affinity_cap(self, affinity_manager):
        """好感度の下限（0）"""
        affinity_manager.get_affinity("user1")
        result = affinity_manager.add_affinity("user1", -1000)
        assert result == 0
    
    def test_set_affinity(self, affinity_manager):
        """好感度の直接設定"""
        result = affinity_manager.set_affinity("user1", 50)
        assert result == 50
        assert affinity_manager.get_affinity("user1") == 50
    
    def test_set_affinity_caps(self, affinity_manager):
        """直接設定時の上下限"""
        assert affinity_manager.set_affinity("user1", 150) == 100
        assert affinity_manager.set_affinity("user2", -50) == 0
    
    def test_message_count(self, affinity_manager):
        """メッセージカウントの増加"""
        affinity_manager.add_affinity("user1", 1)
        affinity_manager.add_affinity("user1", 1)
        affinity_manager.add_affinity("user1", 1)
        
        stats = affinity_manager.get_stats("user1")
        assert stats["message_count"] == 3
    
    def test_get_stats(self, affinity_manager):
        """統計情報の取得"""
        affinity_manager.add_affinity("user1", 5)
        
        stats = affinity_manager.get_stats("user1")
        assert "affinity" in stats
        assert "message_count" in stats
        assert stats["affinity"] == 25
        assert stats["message_count"] == 1
    
    def test_persistence(self, temp_dir, monkeypatch):
        """データの永続化"""
        import affinity
        test_file = temp_dir / "test_affinity.yaml"
        monkeypatch.setattr(affinity, "AFFINITY_FILE", test_file)
        
        # 保存
        am1 = affinity.AffinityManager()
        am1.add_affinity("user1", 30)
        
        # 新しいインスタンスで読み込み
        am2 = affinity.AffinityManager()
        assert am2.get_affinity("user1") == 50  # 20 + 30


class TestGetAffinityLevel:
    """get_affinity_level関数のテスト"""
    
    @pytest.fixture
    def sample_levels(self):
        """テスト用の好感度レベル設定"""
        return {
            "stranger": {
                "threshold": 0,
                "description": "他人",
                "prompt_addition": "警戒する"
            },
            "acquaintance": {
                "threshold": 30,
                "description": "知り合い",
                "prompt_addition": "普通に接する"
            },
            "friend": {
                "threshold": 60,
                "description": "友達",
                "prompt_addition": "親しく接する"
            },
            "lover": {
                "threshold": 90,
                "description": "恋人",
                "prompt_addition": "愛情を込めて接する"
            }
        }
    
    def test_lowest_level(self, sample_levels):
        """最低レベルの判定"""
        from affinity import get_affinity_level
        desc, prompt = get_affinity_level(0, sample_levels)
        assert desc == "他人"
    
    def test_mid_level(self, sample_levels):
        """中間レベルの判定"""
        from affinity import get_affinity_level
        desc, prompt = get_affinity_level(50, sample_levels)
        assert desc == "知り合い"
    
    def test_high_level(self, sample_levels):
        """高レベルの判定"""
        from affinity import get_affinity_level
        desc, prompt = get_affinity_level(95, sample_levels)
        assert desc == "恋人"
    
    def test_boundary_value(self, sample_levels):
        """境界値の判定"""
        from affinity import get_affinity_level
        desc, _ = get_affinity_level(30, sample_levels)
        assert desc == "知り合い"
        
        desc, _ = get_affinity_level(29, sample_levels)
        assert desc == "他人"
