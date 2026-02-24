import discord
from discord.ext import commands
from openai import OpenAI
from dotenv import load_dotenv
import os
import yaml
import json
import re
from pathlib import Path
from datetime import datetime

from affinity import AffinityManager, get_affinity_level
from memory import MemoryManager, build_memory_update_prompt
from linter import format_for_discord
from character_prompt import (
    build_character_generation_prompt,
    build_greetings_generation_prompt,
    extract_yaml_from_response,
    validate_character_yaml,
)

# 設定読み込み
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LM_STUDIO_API_KEY = os.getenv('LM_STUDIO_API_KEY')
LM_STUDIO_BASE_URL = os.getenv('LM_STUDIO_BASE_URL')
MODEL_IDENTIFIER = os.getenv('MODEL_IDENTIFIER')
NOTIFY_CHANNEL_ID = os.getenv('NOTIFY_CHANNEL_ID')  # 通知チャンネルID

# キャラクター設定を読み込む
CHARACTER_FILE = Path(__file__).parent.parent / "config" / "character.yaml"
with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
    character = yaml.safe_load(f)

# 好感度マネージャーの初期化
affinity_config = character.get("affinity_config", {})
affinity_manager = AffinityManager(
    initial_affinity=affinity_config.get("initial", 20),
    max_affinity=affinity_config.get("max", 100),
    min_affinity=affinity_config.get("min", 0)
)

# メモリマネージャーの初期化
memory_manager = MemoryManager()

# Discord Bot設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)
client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key=LM_STUDIO_API_KEY)


@bot.event
async def on_ready():
    """BOT起動時にスラッシュコマンドを同期し、通知を送信"""
    await bot.tree.sync()

    # 起動通知
    if NOTIFY_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(get_time_greeting(is_startup=True))
        except Exception:
            pass


def build_system_prompt(user_id: str, user_message: str = "") -> str:
    """ユーザーの好感度と記憶に応じたシステムプロンプトを構築する"""
    affinity = affinity_manager.get_affinity(user_id)
    level_name, level_prompt = get_affinity_level(affinity, character.get("affinity_levels", {}))
    
    # 3層記憶を取得(関連トピックのみ)
    memory = memory_manager.get_memory_for_prompt(user_id, user_message)
    
    base_prompt = character.get("base_prompt", "あなたはAIアシスタントです。")
    
    # 共通ルール(全キャラ共通・キャラYAMLに書かない)
    common_rules = """[共通ルール]
- 必ず日本語のみで回答してください。中国語や英語を混ぜないでください
- 絵文字は控えめにしてください"""

    prompt = f"""{common_rules}

{base_prompt}

[好感度: {affinity}/100 - {level_name}]
{level_prompt}

[記憶の使用ルール]
- 記憶はユーザーがその話題に触れた時のみ自然に参照
- 唐突に過去の話題を持ち出さない
- 現在の会話の流れを最優先"""
    
    if memory:
        prompt += f"\n\n[この人の記憶]\n{memory}"
    
    return prompt


def analyze_message_sentiment(user_message: str) -> int:
    """
    メッセージの内容を分析して好感度の変動値を返す
    ひどい内容: -5 ~ -1
    普通: +1
    優しい内容: +2 ~ +5
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_IDENTIFIER,
            messages=[
                {"role": "system", "content": """あなたはメッセージの感情分析をするAIです。
ユーザーのメッセージが「優しい・褒め言葉・好意的」か「普通」か「ひどい・侮辱的・攻撃的」かを判定し、
好感度の変動値を-5から+5の整数で返してください。

判定基準:
- +5: とても優しい、愛情表現、褒め言葉
- +3: 優しい、気遣い、励まし
- +1: 普通の会話、質問
- -1: 少し失礼、からかい
- -3: 失礼、批判的
- -5: 非常にひどい、侮辱、暴言

JSONフォーマットで回答: {"score": 数値, "reason": "理由"}"""},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
        )
        
        result_text = response.choices[0].message.content
        # JSONを抽出
        json_match = re.search(r'\{[^}]+\}', result_text)
        if json_match:
            result = json.loads(json_match.group())
            score = int(result.get("score", 1))
            # -5から+5の範囲に制限
            return max(-5, min(5, score))
    except Exception as e:
        print(f"Sentiment analysis error: {e}")
    
    return 1  # デフォルトは+1


# 挨拶テンプレートを読み込む
GREETINGS_FILE = Path(__file__).parent.parent / "config" / "greetings.yaml"


def _load_greetings() -> dict:
    """挨拶テンプレートをYAMLファイルから読み込む"""
    if GREETINGS_FILE.exists():
        try:
            with open(GREETINGS_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except (yaml.YAMLError, IOError):
            pass
    return {}


def _get_time_key_startup(hour: int) -> str:
    """起動時の時間帯キーを返す"""
    if 5 <= hour < 10:
        return "early_morning"
    elif 10 <= hour < 12:
        return "late_morning"
    elif 12 <= hour < 14:
        return "noon"
    elif 14 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    elif 21 <= hour < 24:
        return "night"
    else:
        return "midnight"


def _get_time_key_shutdown(hour: int) -> str:
    """停止時の時間帯キーを返す"""
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 21:
        return "evening"
    elif 21 <= hour < 24:
        return "night"
    else:
        return "midnight"


def get_time_greeting(is_startup: bool = True) -> str:
    """時間帯に応じた挨拶を返す(config/greetings.yamlから読み込み)"""
    import random

    greetings = _load_greetings()
    hour = datetime.now().hour

    if is_startup:
        section = greetings.get("startup", {})
        time_key = _get_time_key_startup(hour)
    else:
        section = greetings.get("shutdown", {})
        time_key = _get_time_key_shutdown(hour)

    messages = section.get(time_key, [])
    if messages:
        return random.choice(messages)

    # フォールバック(greetings.yamlが無い/不完全な場合)
    char_name = character.get("name", "AI")
    if is_startup:
        return f"{char_name}、起動しました！"
    else:
        return f"{char_name}、停止します。おやすみなさい。"


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print(f'Character: {character.get("name", "Unknown")} ({character.get("personality", "")})')
    await bot.tree.sync()
    
    # 起動メッセージを送信
    if NOTIFY_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(get_time_greeting(is_startup=True))
        except Exception as e:
            print(f"Failed to send startup message: {e}")


@bot.tree.command(name="ask", description="AIに話しかける")
async def ask(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    
    user_id = str(interaction.user.id)
    
    try:
        # メッセージの感情を分析して好感度変動値を決定
        affinity_change = analyze_message_sentiment(message)
        
        # 好感度を更新(返信の前に更新して、反応に反映させる)
        old_affinity = affinity_manager.get_affinity(user_id)
        new_affinity = affinity_manager.add_affinity(user_id, affinity_change)
        
        # システムプロンプトを構築(ユーザーメッセージも渡して関連記憶を取得)
        system_prompt = build_system_prompt(user_id, message)
        
        # 好感度変動をプロンプトに追加
        if affinity_change < 0:
            mood_hint = f"\n\n[注意: ユーザーの発言は少し失礼でした。好感度が{affinity_change}下がりました。少し傷ついた様子で返答してください]"
        elif affinity_change >= 3:
            mood_hint = f"\n\n[注意: ユーザーの発言はとても優しかったです。好感度が+{affinity_change}上がりました。嬉しそうに返答してください]"
        else:
            mood_hint = ""
        
        # LLMに問い合わせ
        response = client.chat.completions.create(
            model=MODEL_IDENTIFIER,
            messages=[
                {"role": "system", "content": system_prompt + mood_hint},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        
        # Discord向けに出力を整形
        reply = format_for_discord(reply)
        
        # Discord 2000文字制限に対応(分割送信)
        if len(reply) <= 2000:
            await interaction.followup.send(reply)
        else:
            # 2000文字ごとに分割
            chunks = [reply[i:i+1990] for i in range(0, len(reply), 1990)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await interaction.followup.send(chunk)
                else:
                    await interaction.channel.send(chunk)
        
        # 記憶を更新(3層対応)
        try:
            old_permanent = memory_manager.get_permanent(user_id)
            old_recent = memory_manager.get_recent(user_id)
            memory_prompt = build_memory_update_prompt(old_permanent, old_recent, message, reply)
            memory_response = client.chat.completions.create(
                model=MODEL_IDENTIFIER,
                messages=[{"role": "user", "content": memory_prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            result = memory_response.choices[0].message.content.strip()
            
            # 結果をパース
            for line in result.split("\n"):
                if line.startswith("PERMANENT:"):
                    perm = line.replace("PERMANENT:", "").strip()
                    if perm and perm != "(変更なし)":
                        memory_manager.update_permanent(user_id, perm)
                elif line.startswith("RECENT:"):
                    recent = line.replace("RECENT:", "").strip()
                    if recent:
                        memory_manager.update_recent(user_id, recent)
                elif line.startswith("TOPIC:"):
                    topic = line.replace("TOPIC:", "").strip()
                    if topic and topic != "(なし)":
                        memory_manager.add_topic(user_id, topic)
        except Exception:
            pass  # 記憶更新失敗は無視
        
    except Exception as e:
        await interaction.followup.send(f"エラーが発生しました: {str(e)}")


@bot.tree.command(name="affinity", description="自分の好感度を確認する")
async def check_affinity(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    stats = affinity_manager.get_stats(user_id)
    affinity = stats.get("affinity", 0)
    message_count = stats.get("message_count", 0)
    
    level_name, _ = get_affinity_level(affinity, character.get("affinity_levels", {}))
    
    embed = discord.Embed(
        title=f"💕 {character.get('name', 'AI')}との関係",
        color=discord.Color.pink()
    )
    embed.add_field(name="好感度", value=f"{affinity}/100", inline=True)
    embed.add_field(name="状態", value=level_name, inline=True)
    embed.add_field(name="会話回数", value=f"{message_count}回", inline=True)
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="change", description="LLMでキャラクターYAMLを自動生成する")
async def change_character(interaction: discord.Interaction, series: str, character_name: str):
    """LLMを呼び出してキャラクターYAMLと挨拶テンプレートを自動生成する"""
    await interaction.response.defer()

    config_dir = Path(__file__).parent.parent / "config"
    # ファイル名用にキャラ名を安全な形式に変換
    safe_name = re.sub(r'[^\w]', '_', character_name).lower()

    try:
        # --- 注意書き ---
        warning_embed = discord.Embed(
            title=f"🎭 {character_name}({series})を生成中...",
            description=(
                "⚠️ **注意**: この機能はWeb検索対応のLLMが必要です。\n"
                "ローカルLLMでは正確なキャラ情報を取得できない場合があります。\n"
                "また、この機能は**動作確認が十分ではありません**。"
            ),
            color=discord.Color.orange()
        )
        await interaction.followup.send(embed=warning_embed)

        # --- ステップ1: キャラクターYAML生成 ---
        await interaction.channel.send("📝 **ステップ1/2**: キャラクター設定を生成中...")

        char_prompt = build_character_generation_prompt(series, character_name)
        char_response = client.chat.completions.create(
            model=MODEL_IDENTIFIER,
            messages=[
                {"role": "system", "content": "あなたはアニメ・ゲームキャラクターの設定資料を作成する専門家です。YAML形式のみで出力してください。"},
                {"role": "user", "content": char_prompt}
            ],
            temperature=0.7,
            max_tokens=4000,
        )

        char_yaml_raw = char_response.choices[0].message.content.strip()
        char_yaml_content = extract_yaml_from_response(char_yaml_raw)

        # 必須フィールドの検証
        valid, error_msg = validate_character_yaml(char_yaml_content)
        if not valid:
            await interaction.channel.send(f"❌ キャラクターYAMLの生成に失敗しました: {error_msg}")
            return

        # 保存(元のcharacter.yamlは上書きしない)
        char_file = config_dir / f"character_{safe_name}.yaml"
        with open(char_file, "w", encoding="utf-8") as f:
            f.write(char_yaml_content)

        await interaction.channel.send(f"✅ キャラクター設定を `{char_file.name}` に保存しました")

        # --- ステップ2: 挨拶テンプレート生成 ---
        await interaction.channel.send("📝 **ステップ2/2**: 挨拶テンプレートを生成中...")

        greet_prompt = build_greetings_generation_prompt(char_yaml_content)
        greet_response = client.chat.completions.create(
            model=MODEL_IDENTIFIER,
            messages=[
                {"role": "system", "content": "あなたはキャラクターの口調で挨拶文を作成する専門家です。YAML形式のみで出力してください。"},
                {"role": "user", "content": greet_prompt}
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        greet_yaml_raw = greet_response.choices[0].message.content.strip()
        greet_yaml_content = extract_yaml_from_response(greet_yaml_raw)

        # 保存
        greet_file = config_dir / f"greetings_{safe_name}.yaml"
        with open(greet_file, "w", encoding="utf-8") as f:
            f.write(greet_yaml_content)

        await interaction.channel.send(f"✅ 挨拶テンプレートを `{greet_file.name}` に保存しました")

        # --- 完了メッセージ ---
        done_embed = discord.Embed(
            title=f"🎉 {character_name} の生成が完了しました！",
            description=(
                f"以下のファイルが生成されました:\n"
                f"• `config/{char_file.name}` — キャラクター設定\n"
                f"• `config/{greet_file.name}` — 挨拶テンプレート\n\n"
                f"**切り替え方法:**\n"
                f"1. `config/{char_file.name}` → `config/character.yaml` にコピー\n"
                f"2. `config/{greet_file.name}` → `config/greetings.yaml` にコピー\n"
                f"3. BOTを再起動\n\n"
                f"⚠️ 生成されたYAMLの内容を確認してから切り替えてください。"
            ),
            color=discord.Color.green()
        )
        await interaction.channel.send(embed=done_embed)

    except Exception as e:
        await interaction.channel.send(f"❌ エラーが発生しました: {str(e)}")


@bot.tree.command(name="shutdown", description="BOTを停止する(管理者のみ)")
async def shutdown_bot(interaction: discord.Interaction):
    # 管理者チェック(サーバー管理者のみ実行可能)
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます", ephemeral=True)
        return
    
    await interaction.response.send_message("シャットダウンします...", ephemeral=True)
    
    # おやすみメッセージを送信
    if NOTIFY_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(get_time_greeting(is_startup=False))
        except Exception:
            pass
    
    await bot.close()


async def send_shutdown_message():
    """停止メッセージを送信"""
    if NOTIFY_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(get_time_greeting(is_startup=False))
        except Exception:
            pass


def run_bot():
    """BOTを実行(graceful shutdown対応)"""
    import signal
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def shutdown():
        await send_shutdown_message()
        await bot.close()
    
    def signal_handler():
        loop.create_task(shutdown())
    
    try:
        loop.run_until_complete(bot.start(DISCORD_BOT_TOKEN))
    except KeyboardInterrupt:
        loop.run_until_complete(shutdown())
    finally:
        loop.close()


if __name__ == "__main__":
    run_bot()