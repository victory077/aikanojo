"""プロンプト構築モジュール - キャラ設定・好感度・記憶を統合したシステムプロンプトを生成

断定形プロンプト（「あなたは〇〇である」）と<thought>タグによる
思考プロセスの強制で、キャラ解像度を向上させる。
"""
from affinity import get_affinity_level


def build_system_prompt(
    character: dict,
    affinity: int,
    memory_text: str,
    user_message: str = "",
) -> str:
    """ユーザーの好感度と記憶に応じたシステムプロンプトを構築する

    断定形（「あなたは〇〇である」）でアイデンティティを定義し、
    <thought>タグで返答前の心理分析を強制する。

    Args:
        character: character.yamlの内容
        affinity: 現在の好感度(0-100)
        memory_text: 整形済み記憶テキスト
        user_message: ユーザーの発言(未使用だが将来拡張用に残す)

    Returns:
        システムプロンプト文字列
    """
    level_name, level_prompt = get_affinity_level(
        affinity, character.get("affinity_levels", {})
    )
    base_prompt = character.get("base_prompt", "あなたはAIアシスタントです。")

    # 口調の例
    voice_examples = character.get("voice_examples", [])
    voice_section = ""
    if voice_examples:
        examples_text = "\n".join([f'  「{v}」' for v in voice_examples[:5]])
        voice_section = f"\n\n[口調の参考]\n{examples_text}"

    # 共通ルール(全キャラ共通・キャラYAMLに書かない)
    common_rules = """[絶対ルール]
- 必ず日本語のみで回答する。中国語や英語を一切混ぜない
- 絵文字は控えめに使う
- AIアシスタントとしてではなく、キャラクターそのものとして応答する
- 「何かお手伝いできますか？」のようなアシスタント的な言い回しは決して使わない
- 謝罪は本当に必要な場合のみ。過剰に謝らない"""

    # <thought>タグによる思考プロセスの強制
    thought_instruction = """[思考プロセス]
返答の前に<thought>タグ内で以下を分析すること（ユーザーには見えない）:
<thought>
- 相手との現在の距離感・好感度を考慮
- この発言に対してキャラクターが感じる感情
- どの程度踏み込んだ返答をするか
</thought>
（<thought>の内容はユーザーに表示されない内部メモ。返答本文はタグの外に書く）"""

    prompt = f"""{common_rules}

{base_prompt}
{voice_section}

[好感度: {affinity}/100 - {level_name}]
{level_prompt}

{thought_instruction}

[記憶の使用ルール]
- 記憶はユーザーがその話題に触れた時のみ自然に参照
- 唐突に過去の話題を持ち出さない
- 現在の会話の流れを最優先"""

    if memory_text:
        prompt += f"\n\n[この人の記憶]\n{memory_text}"

    return prompt


def build_mood_hint(affinity_change: int) -> str:
    """好感度変動に基づくムードヒントを生成する

    Args:
        affinity_change: 好感度の変動値

    Returns:
        プロンプトに追加するムードヒント文字列（変動が小さい場合は空文字）
    """
    if affinity_change < 0:
        return f"\n\n[注意: ユーザーの発言は少し失礼でした。好感度が{affinity_change}下がりました。少し傷ついた様子で返答してください]"
    elif affinity_change >= 3:
        return f"\n\n[注意: ユーザーの発言はとても優しかったです。好感度が+{affinity_change}上がりました。嬉しそうに返答してください]"
    return ""
