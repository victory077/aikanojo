"""CRAG (Corrective Retrieval Augmented Generation) 評価モジュール

ChromaDBから検索された記憶の妥当性をLLMで評価し、
関連性が低い記憶を除外することでハルシネーションを防ぐ。
"""


def build_crag_evaluation_prompt(query: str, retrieved_memories: list[dict]) -> str:
    """検索結果の妥当性評価プロンプトを構築する

    Args:
        query: ユーザーの発言
        retrieved_memories: ChromaDB検索結果のリスト

    Returns:
        LLMに渡す評価プロンプト
    """
    memories_text = ""
    for i, mem in enumerate(retrieved_memories, 1):
        doc = mem.get("document", "")
        date = mem.get("metadata", {}).get("date", "不明")
        memories_text += f"[記憶{i}] ({date}) {doc}\n"

    return f"""以下の「ユーザーの発言」に対して、検索された「過去の記憶」がそれぞれ関連があるかを判定してください。

[ユーザーの発言]
{query}

[過去の記憶]
{memories_text}

[ルール]
- 各記憶について「関連あり(Y)」か「関連なし(N)」を判定
- 話題・キーワード・文脈が一致するなら「関連あり」
- 全く無関係な内容なら「関連なし」
- 判定は厳格に。曖昧な関連は「関連なし」

以下の形式で出力（記憶番号: Y/N）:
1: Y
2: N
3: Y"""


def parse_crag_result(result_text: str, memory_count: int) -> list[bool]:
    """CRAG評価結果をパースする

    Args:
        result_text: LLMの応答テキスト
        memory_count: 評価対象の記憶数

    Returns:
        各記憶が関連ありかどうかのリスト
    """
    relevance = [True] * memory_count  # デフォルトは全て関連あり（パース失敗時の安全策）

    for line in result_text.strip().split("\n"):
        line = line.strip()
        if ":" in line:
            parts = line.split(":", 1)
            try:
                idx = int(parts[0].strip()) - 1  # 1-indexedを0-indexedに
                value = parts[1].strip().upper()
                if 0 <= idx < memory_count:
                    relevance[idx] = value.startswith("Y")
            except (ValueError, IndexError):
                continue

    return relevance


def filter_memories_by_crag(
    retrieved_memories: list[dict],
    relevance: list[bool],
) -> list[dict]:
    """CRAG評価結果に基づいて記憶をフィルタリングする

    Args:
        retrieved_memories: ChromaDB検索結果
        relevance: parse_crag_resultの結果

    Returns:
        関連があると判定された記憶のリスト
    """
    return [
        mem for mem, is_relevant in zip(retrieved_memories, relevance)
        if is_relevant
    ]
