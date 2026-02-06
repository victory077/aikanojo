"""memory.py のユニットテスト"""
import pytest
import tempfile
import shutil
from pathlib import Path
import sys

# srcをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestMemoryManager:
    """MemoryManagerクラスのテスト"""
    
    @pytest.fixture
    def temp_dir(self):
        """一時ディレクトリを作成"""
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d)
    
    @pytest.fixture
    def memory_manager(self, temp_dir, monkeypatch):
        """テスト用MemoryManagerを作成"""
        # MEMORY_FILEを一時ディレクトリに変更
        import memory
        test_file = temp_dir / "test_memory.yaml"
        monkeypatch.setattr(memory, "MEMORY_FILE", test_file)
        return memory.MemoryManager()
    
    def test_empty_memory(self, memory_manager):
        """新規ユーザーの記憶は空"""
        assert memory_manager.get_permanent("new_user") == ""
        assert memory_manager.get_recent("new_user") == ""
        assert memory_manager.get_topics("new_user") == []
    
    def test_update_permanent(self, memory_manager):
        """長期記憶の更新"""
        memory_manager.update_permanent("user1", "名前:テスト, 好み:寿司")
        assert memory_manager.get_permanent("user1") == "名前:テスト, 好み:寿司"
    
    def test_permanent_max_length(self, memory_manager):
        """長期記憶の文字数制限（300文字）"""
        long_text = "あ" * 500
        memory_manager.update_permanent("user1", long_text)
        assert len(memory_manager.get_permanent("user1")) == 300
    
    def test_update_recent(self, memory_manager):
        """短期記憶の更新"""
        memory_manager.update_recent("user1", "今日は寿司の話をした")
        assert memory_manager.get_recent("user1") == "今日は寿司の話をした"
    
    def test_recent_max_length(self, memory_manager):
        """短期記憶の文字数制限（200文字）"""
        long_text = "あ" * 300
        memory_manager.update_recent("user1", long_text)
        assert len(memory_manager.get_recent("user1")) == 200
    
    def test_add_topic(self, memory_manager):
        """中期記憶（トピック）の追加"""
        memory_manager.add_topic("user1", "WoTの話")
        topics = memory_manager.get_topics("user1")
        assert len(topics) == 1
        assert "WoTの話" in topics[0]
    
    def test_topic_max_count(self, memory_manager):
        """中期記憶は最大10件"""
        for i in range(15):
            memory_manager.add_topic("user1", f"話題{i}")
        topics = memory_manager.get_topics("user1")
        assert len(topics) == 10
    
    def test_get_relevant_topics(self, memory_manager):
        """キーワードマッチによる関連トピック取得"""
        memory_manager.add_topic("user1", "WoT 戦車の話")  # スペースで分離
        memory_manager.add_topic("user1", "寿司の話")
        memory_manager.add_topic("user1", "音楽の話")
        
        # 「戦車」を含むメッセージ
        relevant = memory_manager.get_relevant_topics("user1", "戦車って強いの？")
        assert len(relevant) >= 1
        assert any("WoT" in t or "戦車" in t for t in relevant)
        
        # 「寿司」を含むメッセージ
        relevant = memory_manager.get_relevant_topics("user1", "寿司食べたい")
        assert len(relevant) >= 1
        
        # 関係ないメッセージ
        relevant = memory_manager.get_relevant_topics("user1", "今日の天気は？")
        assert len(relevant) == 0
    
    def test_get_memory_for_prompt(self, memory_manager):
        """プロンプト用記憶の取得"""
        memory_manager.update_permanent("user1", "名前:テスト")
        memory_manager.update_recent("user1", "直近の会話")
        memory_manager.add_topic("user1", "WoTの話")
        
        # 関連キーワードなし
        prompt = memory_manager.get_memory_for_prompt("user1", "こんにちは")
        assert "【基本情報】" in prompt
        assert "【直近】" in prompt
        assert "【関連する過去の話題】" not in prompt
        
        # 関連キーワードあり
        prompt = memory_manager.get_memory_for_prompt("user1", "WoTってゲーム？")
        assert "【関連する過去の話題】" in prompt
    
    def test_has_memory(self, memory_manager):
        """記憶の有無判定"""
        assert not memory_manager.has_memory("user1")
        
        memory_manager.update_permanent("user1", "test")
        assert memory_manager.has_memory("user1")
    
    def test_persistence(self, temp_dir, monkeypatch):
        """データの永続化"""
        import memory
        test_file = temp_dir / "test_memory.yaml"
        monkeypatch.setattr(memory, "MEMORY_FILE", test_file)
        
        # 保存
        mm1 = memory.MemoryManager()
        mm1.update_permanent("user1", "テストデータ")
        
        # 新しいインスタンスで読み込み
        mm2 = memory.MemoryManager()
        assert mm2.get_permanent("user1") == "テストデータ"
