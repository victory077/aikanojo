"""キャラクターYAML生成プロンプトモジュール

LLMを呼び出してキャラクター設定YAMLと挨拶テンプレートYAMLを自動生成する。
⚠️ Web検索機能を持つLLMが必要です。検索非対応の環境では正確な結果を得られません。
"""

import re
import yaml


def build_character_generation_prompt(series: str, character_name: str) -> str:
    """キャラクターYAML生成用のプロンプトを構築する

    Args:
        series: 作品名(例: "学園アイドルマスター")
        character_name: キャラクター名(例: "姫崎莉波")

    Returns:
        LLMに渡すプロンプト文
    """
    return f"""「{series}」の「{character_name}」の情報をWeb検索で収集し、以下のYAMLフォーマットで設定ファイルを生成してください。

[ルール]
- 必須フィールド: name, base_prompt, voice_examples, affinity_levels, affinity_config
- 上記以外は情報が見つからなければ省略OK
- 口調・性格は原作に忠実に
- voice_examplesは原作セリフを引用(最低5つ)
- YAMLのみ出力(説明文不要、コードフェンス不要)

[フォーマット]
name: "フルネーム"
nickname: "あだ名"
personality: "性格を一言で"
description: "概要(1-2文)"
profile:
  age: 年齢
  birthday: "誕生日"
  height: "身長"
  hometown: "出身地"
  hobbies: ["趣味1", "趣味2"]
  skills: ["特技1", "特技2"]
  family: ["家族構成"]

hometown_details: |
  出身地の詳細

producer_relationship: |
  主人公との関係

relationships:
  キャラ名:
    relation: "関係性"
    notes: |
      詳細


base_prompt: |
  あなたは「キャラ名」です。
  [性格・特徴](箇条書き3-5項目)
  [話し方]一人称、呼び方、口調の特徴
  [過去・背景]重要なエピソード
  [人間関係]主要キャラとの関係

voice_examples:
  - "セリフ1"
  - "セリフ2"
  - "セリフ3"
  - "セリフ4"
  - "セリフ5"


affinity_levels:
  low:
    threshold: 0
    description: "初対面"
    prompt_addition: |
      好感度が低い。遠慮がちで控えめ。
  medium:
    threshold: 31
    description: "打ち解けてきた"
    prompt_addition: |
      信頼し始めている。親しく接する。
  high:
    threshold: 61
    description: "大切な存在"
    prompt_addition: |
      大切な存在。甘えたり弱さを見せる。
  max:
    threshold: 86
    description: "特別な人"
    prompt_addition: |
      特別な存在。最も親密な態度。


affinity_config:
  initial: 20
  per_message: 1
  max: 100
  min: 0"""


def build_greetings_generation_prompt(character_yaml_content: str) -> str:
    """挨拶テンプレートYAML生成用のプロンプトを構築する

    character.yamlの内容を元に、キャラの口調に合った挨拶文を生成させる。

    Args:
        character_yaml_content: 生成済みcharacter.yamlの内容

    Returns:
        LLMに渡すプロンプト文
    """
    return f"""以下のキャラ設定に基づいて、BOT起動・停止時の挨拶YAMLを生成してください。

[キャラ設定]
{character_yaml_content}

[ルール]
- キャラの口調・性格に忠実に
- 絵文字は使わない
- YAMLのみ出力(説明文不要、コードフェンス不要)

[フォーマット]
startup:
  early_morning:
    - "朝5-9時の挨拶"
  late_morning:
    - "朝10-11時の挨拶"
  noon:
    - "昼12-13時の挨拶"
  afternoon:
    - "午後14-16時の挨拶"
  evening:
    - "夕方17-20時の挨拶"
  night:
    - "夜21-23時の挨拶"
  midnight:
    - "深夜0-4時の挨拶"

shutdown:
  morning:
    - "朝5-11時のお別れ"
  afternoon:
    - "午後12-16時のお別れ"
  evening:
    - "夕方17-20時のお別れ"
  night:
    - "夜21-23時のお別れ"
  midnight:
    - "深夜0-4時のお別れ" """


def extract_yaml_from_response(response_text: str) -> str:
    """LLMレスポンスからYAML部分を抽出する

    コードフェンスで囲まれている場合はそれを除去し、
    そうでなければそのまま返す。

    Args:
        response_text: LLMのレスポンス全文

    Returns:
        YAML文字列
    """
    # ```yaml ... ``` または ``` ... ``` パターンを抽出
    match = re.search(r'```(?:yaml)?\s*\n(.*?)```', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def validate_character_yaml(yaml_content: str) -> tuple[bool, str]:
    """生成されたキャラクターYAMLの必須フィールドを検証する

    Args:
        yaml_content: YAML文字列

    Returns:
        (valid, error_message) のタプル
    """
    try:
        data = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return False, f"YAML解析エラー: {e}"

    if not isinstance(data, dict):
        return False, "YAMLがdict形式ではありません"

    required_fields = ["name", "base_prompt", "voice_examples", "affinity_levels", "affinity_config"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        return False, f"必須フィールドが不足: {', '.join(missing)}"

    return True, ""
