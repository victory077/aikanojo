"""memory パッケージのユニットテスト（YAML記憶 + ChromaDB）"""
import pytest
import tempfile
import shutil
from pathlib import Path

from memory.yaml_store import YAMLMemoryStore, build_memory_update_prompt
from memory.chroma_store import ChromaMemoryStore
from memory.manager import MemoryManager


class TestYAMLMemoryStore:
    """YAMLMemoryStoreクラスのテスト（既存memory.pyの互換テスト）"""

    @pytest.fixture
    def temp_dir(self):
        d = tempfile.mkdtemp()
        yield Path(d)
        shutil.rmtree(d)

    @pytest.fixture
    def store(self, temp_dir):
        return YAMLMemoryStore(temp_dir / "test_memory.yaml")

    def test_empty_memory(self, store):
        """新規ユーザーの記憶は空"""
        assert store.get_permanent("new_user") == ""
        assert store.get_recent("new_user") == ""
        assert store.get_topics("new_user") == []

    def test_update_permanent(self, store):
        """長期記憶の更新"""
        store.update_permanent("user1", "名前:テスト, 好み:寿司")
        assert store.get_permanent("user1") == "名前:テスト, 好み:寿司"

    def test_permanent_max_length(self, store):
        """長期記憶の文字数制限(300文字)"""
        long_text = "あ" * 500
        store.update_permanent("user1", long_text)
        assert len(store.get_permanent("user1")) == 300

    def test_update_recent(self, store):
        """短期記憶の更新"""
        store.update_recent("user1", "今日は寿司の話をした")
        assert store.get_recent("user1") == "今日は寿司の話をした"

    def test_recent_max_length(self, store):
        """短期記憶の文字数制限(200文字)"""
        long_text = "あ" * 300
        store.update_recent("user1", long_text)
        assert len(store.get_recent("user1")) == 200

    def test_add_topic(self, store):
        """中期記憶(トピック)の追加"""
        store.add_topic("user1", "WoTの話")
        topics = store.get_topics("user1")
        assert len(topics) == 1
        assert "WoTの話" in topics[0]

    def test_topic_max_count(self, store):
        """中期記憶は最大10件"""
        for i in range(15):
            store.add_topic("user1", f"話題{i}")
        topics = store.get_topics("user1")
        assert len(topics) == 10

    def test_get_relevant_topics(self, store):
        """キーワードマッチによる関連トピック取得"""
        store.add_topic("user1", "WoT 戦車の話")
        store.add_topic("user1", "寿司の話")
        store.add_topic("user1", "音楽の話")

        relevant = store.get_relevant_topics("user1", "戦車って強いの？")
        assert len(relevant) >= 1
        assert any("WoT" in t or "戦車" in t for t in relevant)

        relevant = store.get_relevant_topics("user1", "寿司食べたい")
        assert len(relevant) >= 1

        relevant = store.get_relevant_topics("user1", "今日の天気は？")
        assert len(relevant) == 0

    def test_persistence(self, temp_dir):
        """データの永続化"""
        test_file = temp_dir / "test_memory.yaml"
        store1 = YAMLMemoryStore(test_file)
        store1.update_permanent("user1", "テストデータ")

        store2 = YAMLMemoryStore(test_file)
        assert store2.get_permanent("user1") == "テストデータ"


def _safe_rmtree(path: Path) -> None:
    """WindowsでChromaDBのファイルロックを回避しつつ削除"""
    try:
        shutil.rmtree(path)
    except PermissionError:
        import gc
        gc.collect()
        try:
            shutil.rmtree(path)
        except PermissionError:
            pass  # Windowsではプロセス終了時に解放される


class TestChromaMemoryStore:
    """ChromaMemoryStoreクラスのテスト"""

    @pytest.fixture
    def temp_dir(self):
        d = tempfile.mkdtemp()
        yield Path(d)
        _safe_rmtree(Path(d))

    @pytest.fixture
    def store(self, temp_dir):
        s = ChromaMemoryStore(
            persist_dir=temp_dir / "chroma_test",
            collection_name="test_conversations",
        )
        yield s
        s.close()

    def test_add_and_search(self, store):
        """会話の保存とセマンティック検索"""
        store.add_conversation("user1", "寿司が好きなんだ", "寿司いいですね！何が好きですか？")
        store.add_conversation("user1", "音楽のおすすめ教えて", "最近のヒット曲はこちらです")

        results = store.search("user1", "寿司って美味しいよね", n_results=2)
        assert len(results) >= 1
        # 寿司の会話が最初にヒットするはず
        assert "寿司" in results[0]["document"]

    def test_user_isolation(self, store):
        """ユーザー間の記憶は分離される"""
        store.add_conversation("user1", "秘密の話", "はい、それは秘密ですね")
        store.add_conversation("user2", "天気の話", "今日はいい天気ですね")

        # user2の検索ではuser1の記憶は出ない
        results = store.search("user2", "秘密", n_results=5)
        for r in results:
            assert r["metadata"]["user_id"] == "user2"

    def test_conversation_count(self, store):
        """会話数の取得"""
        assert store.get_conversation_count("user1") == 0
        store.add_conversation("user1", "hello", "hi")
        assert store.get_conversation_count("user1") == 1
        store.add_conversation("user1", "bye", "see you")
        assert store.get_conversation_count("user1") == 2

    def test_format_for_prompt(self, store):
        """検索結果のプロンプト用整形"""
        store.add_conversation("user1", "テスト", "テスト応答")
        results = store.search("user1", "テスト", n_results=1)
        formatted = store.format_for_prompt(results)
        assert formatted  # 空でないこと
        assert "テスト" in formatted


class TestMemoryManager:
    """統合MemoryManagerのテスト"""

    @pytest.fixture
    def temp_dir(self):
        d = tempfile.mkdtemp()
        yield Path(d)
        _safe_rmtree(Path(d))

    @pytest.fixture
    def manager(self, temp_dir):
        m = MemoryManager(
            memory_file=temp_dir / "test_memory.yaml",
            chroma_dir=temp_dir / "chroma_test",
        )
        yield m
        m.close()

    def test_yaml_operations(self, manager):
        """YAML記憶操作が統合マネージャー経由で動作する"""
        manager.update_permanent("user1", "名前:テスト")
        assert manager.get_permanent("user1") == "名前:テスト"

        manager.update_recent("user1", "直近の会話")
        assert manager.get_recent("user1") == "直近の会話"

        manager.add_topic("user1", "テストの話題")
        assert len(manager.get_topics("user1")) == 1

    def test_chroma_save_and_search(self, manager):
        """ChromaDB経由の保存と検索"""
        manager.save_conversation("user1", "寿司食べたい", "いいですね！")
        results = manager.search_similar("user1", "寿司", n_results=1)
        assert len(results) >= 1

    def test_get_memory_for_prompt(self, manager):
        """統合メモリのプロンプト取得"""
        manager.update_permanent("user1", "名前:テスト")
        manager.update_recent("user1", "直近の会話")
        manager.save_conversation("user1", "寿司の話をした", "寿司美味しいですよね")

        prompt = manager.get_memory_for_prompt("user1", "寿司食べたい")
        assert "[基本情報]" in prompt
        assert "[直近]" in prompt
        # ChromaDB検索結果も含まれるはず
        assert "[関連する過去の会話]" in prompt


class TestBuildMemoryUpdatePrompt:
    """build_memory_update_prompt関数のテスト"""

    def test_with_existing_data(self):
        prompt = build_memory_update_prompt("名前:テスト", "直近の会話", "新しいメッセージ", "Botの返答")
        assert "名前:テスト" in prompt
        assert "直近の会話" in prompt
        assert "新しいメッセージ" in prompt

    def test_empty_data(self):
        prompt = build_memory_update_prompt("", "", "メッセージ", "返答")
        assert "(なし)" in prompt
