"""AI彼女BOT - Discord Botエントリポイント

core/とmemory/モジュールを統合し、Discord上でAI彼女との会話を提供する。
"""
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import yaml
import re
import random
from pathlib import Path
from datetime import datetime

from core.llm_client import LLMClient
from core.prompt_builder import build_system_prompt, build_mood_hint
from memory import MemoryManager, build_memory_update_prompt
from affinity import AffinityManager, get_affinity_level
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
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_BASE_URL = os.getenv('LLM_BASE_URL')
MODEL_IDENTIFIER = os.getenv('MODEL_IDENTIFIER')
NOTIFY_CHANNEL_ID = os.getenv('NOTIFY_CHANNEL_ID')

# LLMパラメータ定数
CHAT_TEMPERATURE = 0.7          # メイン会話の創造性
CHAT_MAX_TOKENS = None          # メイン会話のトークン上限(None=モデルデフォルト)
MEMORY_TEMPERATURE = 0.3        # 記憶更新・CRAG評価(低め=正確性重視)
MEMORY_UPDATE_MAX_TOKENS = 800  # 記憶更新の出力トークン上限
CRAG_MAX_TOKENS = 200           # CRAG評価の出力トークン上限
GENERATE_CHAR_MAX_TOKENS = 5000 # キャラクター生成のトークン上限
GENERATE_GREET_MAX_TOKENS = 2000 # 挨拶生成のトークン上限

# キャラクター設定
CHARACTER_FILE = Path(__file__).parent.parent.parent / "config" / "character.yaml"
with open(CHARACTER_FILE, "r", encoding="utf-8") as f:
    character = yaml.safe_load(f)

# マネージャーの初期化
affinity_config = character.get("affinity_config", {})
affinity_manager = AffinityManager(
    initial_affinity=affinity_config.get("initial", 20),
    max_affinity=affinity_config.get("max", 100),
    min_affinity=affinity_config.get("min", 0)
)
memory_manager = MemoryManager()
llm = LLMClient(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY,
    model=MODEL_IDENTIFIER,
)

# Discord Bot設定
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


# === 挨拶 ===

GREETINGS_FILE = Path(__file__).parent.parent.parent / "config" / "greetings.yaml"


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

    char_name = character.get("name", "AI")
    if is_startup:
        return f"{char_name}、起動しました！"
    else:
        return f"{char_name}、停止します。おやすみなさい。"


# === Bot イベント ===

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    print(f'Character: {character.get("name", "Unknown")} ({character.get("personality", "")})')
    await bot.tree.sync()

    if NOTIFY_CHANNEL_ID:
        try:
            channel = bot.get_channel(int(NOTIFY_CHANNEL_ID))
            if channel:
                await channel.send(get_time_greeting(is_startup=True))
        except Exception as e:
            print(f"起動メッセージ送信失敗: {e}")


# === コマンド ===

@bot.tree.command(name="ask", description="AIに話しかける")
async def ask(interaction: discord.Interaction, message: str):
    await interaction.response.defer()

    user_id = str(interaction.user.id)

    try:
        # 感情分析 → 好感度更新
        affinity_change = llm.analyze_sentiment(message)
        old_affinity = affinity_manager.get_affinity(user_id)
        new_affinity = affinity_manager.add_affinity(user_id, affinity_change)

        # システムプロンプト構築（CRAG付きメモリ検索）
        def _llm_simple(prompt: str) -> str:
            return llm.simple(prompt, temperature=MEMORY_TEMPERATURE, max_tokens=CRAG_MAX_TOKENS)

        memory_text = memory_manager.get_memory_for_prompt(
            user_id, message, llm_simple=_llm_simple
        )
        system_prompt = build_system_prompt(
            character=character,
            affinity=new_affinity,
            memory_text=memory_text,
            user_message=message,
        )

        # ムードヒント追加
        mood_hint = build_mood_hint(affinity_change)

        # LLM呼び出し
        reply = llm.chat(
            system_prompt + mood_hint, message,
            temperature=CHAT_TEMPERATURE, max_tokens=CHAT_MAX_TOKENS,
        )

        # <thought>タグを除去（ユーザーには見せない内部思考）
        reply = re.sub(r'<thought>.*?</thought>\s*', '', reply, flags=re.DOTALL)

        # Discord向け整形
        reply = format_for_discord(reply)

        # 送信（2000文字制限対応）
        if len(reply) <= 2000:
            await interaction.followup.send(reply)
        else:
            chunks = [reply[i:i+1990] for i in range(0, len(reply), 1990)]
            for i, chunk in enumerate(chunks):
                if i == 0:
                    await interaction.followup.send(chunk)
                else:
                    await interaction.channel.send(chunk)

        # 会話をChromaDBに保存
        try:
            memory_manager.save_conversation(user_id, message, reply)
        except Exception:
            pass  # ChromaDB保存失敗は無視

        # YAML記憶を更新
        try:
            old_permanent = memory_manager.get_permanent(user_id)
            old_recent = memory_manager.get_recent(user_id)
            memory_prompt = build_memory_update_prompt(
                old_permanent, old_recent, message, reply
            )
            result = llm.simple(memory_prompt, temperature=MEMORY_TEMPERATURE, max_tokens=MEMORY_UPDATE_MAX_TOKENS)

            for line in result.strip().split("\n"):
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

    # ChromaDB記憶数も表示
    chroma_count = memory_manager._chroma.get_conversation_count(user_id)
    embed.add_field(name="記憶数(ベクトル)", value=f"{chroma_count}件", inline=True)

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="change", description="LLMでキャラクターYAMLを自動生成する")
async def change_character_cmd(interaction: discord.Interaction, series: str, character_name: str):
    """LLMを呼び出してキャラクターYAMLと挨拶テンプレートを自動生成する"""
    await interaction.response.defer()

    config_dir = Path(__file__).parent.parent.parent / "config"
    safe_name = re.sub(r'[^\w]', '_', character_name).lower()

    try:
        # 注意書き
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

        # ステップ1: キャラクターYAML生成
        await interaction.channel.send("📝 **ステップ1/2**: キャラクター設定を生成中...")

        char_prompt = build_character_generation_prompt(series, character_name)
        char_yaml_raw = llm.chat(
            "あなたはアニメ・ゲームキャラクターの設定資料を作成する専門家です。YAML形式のみで出力してください。",
            char_prompt,
            max_tokens=GENERATE_CHAR_MAX_TOKENS,
        )
        char_yaml_content = extract_yaml_from_response(char_yaml_raw)

        valid, error_msg = validate_character_yaml(char_yaml_content)
        if not valid:
            await interaction.channel.send(f"❌ キャラクターYAMLの生成に失敗しました: {error_msg}")
            return

        char_file = config_dir / f"character_{safe_name}.yaml"
        with open(char_file, "w", encoding="utf-8") as f:
            f.write(char_yaml_content)

        await interaction.channel.send(f"✅ キャラクター設定を `{char_file.name}` に保存しました")

        # ステップ2: 挨拶テンプレート生成
        await interaction.channel.send("📝 **ステップ2/2**: 挨拶テンプレートを生成中...")

        greet_prompt = build_greetings_generation_prompt(char_yaml_content)
        greet_yaml_raw = llm.chat(
            "あなたはキャラクターの口調で挨拶文を作成する専門家です。YAML形式のみで出力してください。",
            greet_prompt,
            max_tokens=GENERATE_GREET_MAX_TOKENS,
        )
        greet_yaml_content = extract_yaml_from_response(greet_yaml_raw)

        greet_file = config_dir / f"greetings_{safe_name}.yaml"
        with open(greet_file, "w", encoding="utf-8") as f:
            f.write(greet_yaml_content)

        await interaction.channel.send(f"✅ 挨拶テンプレートを `{greet_file.name}` に保存しました")

        # 完了メッセージ
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
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ このコマンドは管理者のみ使用できます", ephemeral=True)
        return

    await interaction.response.send_message("シャットダウンします...", ephemeral=True)

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
