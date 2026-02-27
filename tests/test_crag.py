"""crag_evaluator.py のユニットテスト"""
from memory.crag_evaluator import (
    build_crag_evaluation_prompt,
    parse_crag_result,
    filter_memories_by_crag,
)


class TestBuildCragEvaluationPrompt:
    """CRAG評価プロンプト構築のテスト"""

    def test_returns_non_empty(self):
        memories = [{"document": "テスト会話", "metadata": {"date": "2026-01-01"}}]
        result = build_crag_evaluation_prompt("こんにちは", memories)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_query(self):
        memories = [{"document": "テスト", "metadata": {}}]
        result = build_crag_evaluation_prompt("寿司食べたい", memories)
        assert "寿司食べたい" in result

    def test_contains_memory(self):
        memories = [{"document": "過去の寿司の話", "metadata": {"date": "2026-01-01"}}]
        result = build_crag_evaluation_prompt("テスト", memories)
        assert "過去の寿司の話" in result


class TestParseCragResult:
    """CRAG評価結果パースのテスト"""

    def test_basic_parse(self):
        result = parse_crag_result("1: Y\n2: N\n3: Y", 3)
        assert result == [True, False, True]

    def test_all_yes(self):
        result = parse_crag_result("1: Y\n2: Y", 2)
        assert result == [True, True]

    def test_all_no(self):
        result = parse_crag_result("1: N\n2: N", 2)
        assert result == [False, False]

    def test_invalid_format(self):
        """パース失敗時はデフォルト（全てTrue）"""
        result = parse_crag_result("なんか変なレスポンス", 3)
        assert result == [True, True, True]

    def test_partial_parse(self):
        """一部のみパース可能な場合"""
        result = parse_crag_result("1: Y\n変なテキスト\n3: N", 3)
        assert result[0] is True
        assert result[2] is False


class TestFilterMemoriesByCrag:
    """CRAGフィルタリングのテスト"""

    def test_filter_irrelevant(self):
        memories = [
            {"document": "寿司の話"},
            {"document": "天気の話"},
            {"document": "ゲームの話"},
        ]
        relevance = [True, False, True]
        filtered = filter_memories_by_crag(memories, relevance)
        assert len(filtered) == 2
        assert filtered[0]["document"] == "寿司の話"
        assert filtered[1]["document"] == "ゲームの話"

    def test_all_relevant(self):
        memories = [{"document": "a"}, {"document": "b"}]
        relevance = [True, True]
        assert len(filter_memories_by_crag(memories, relevance)) == 2

    def test_none_relevant(self):
        memories = [{"document": "a"}, {"document": "b"}]
        relevance = [False, False]
        assert len(filter_memories_by_crag(memories, relevance)) == 0
