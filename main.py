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

# 設定読み込み
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
LM_STUDIO_API_KEY = os.getenv('LM_STUDIO_API_KEY')
LM_STUDIO_BASE_URL = os.getenv('LM_STUDIO_BASE_URL')
MODEL_IDENTIFIER = os.getenv('MODEL_IDENTIFIER')
NOTIFY_CHANNEL_ID = os.getenv('NOTIFY_CHANNEL_ID')  # 通知チャンネルID

# キャラクター設定を読み込む
CHARACTER_FILE = Path(__file__).parent / "character.yaml"
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


def build_system_prompt(user_id: str) -> str:
    """ユーザーの好感度と記憶に応じたシステムプロンプトを構築する"""
    affinity = affinity_manager.get_affinity(user_id)
    level_name, level_prompt = get_affinity_level(affinity, character.get("affinity_levels", {}))
    memory = memory_manager.get_memory(user_id)
    
    base_prompt = character.get("base_prompt", "あなたはAIアシスタントです。")
    
    prompt = f"""{base_prompt}

【好感度: {affinity}/100 - {level_name}】
{level_prompt}"""
    
    if memory:
        prompt += f"\n\n【この人の記憶】\n{memory}"
    
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


def get_time_greeting(is_startup: bool = True) -> str:
    """時間帯に応じた挨拶を生成"""
    hour = datetime.now().hour
    
    if is_startup:  # 起動時
        if 5 <= hour < 10:
            return "おはよう！プロデューサーくん！今日も一緒にがんばろうね✨"
        elif 10 <= hour < 12:
            return "やっと起きたの…？もう、午前中だよ！プロデューサーくん！"
        elif 12 <= hour < 14:
            return "おはようプロデューサーくん！お昼ご飯はもう食べた？"
        elif 14 <= hour < 17:
            return "こんにちはプロデューサーくん！午後も一緒にがんばろうね"
        elif 17 <= hour < 21:
            return "こんばんは！プロデューサーくん、今日もお疲れ様！"
        elif 21 <= hour < 24:
            return "こんな時間から？…まぁ、会えて嬉しいけどね。プロデューサーくん！"
        else:  # 0-4時
            return "こんな深夜に…？無理しちゃダメだよ、プロデューサーくん。"
    else:  # 停止時
        if 5 <= hour < 12:
            return "じゃあね！今日も一日がんばってね、プロデューサーくん！"
        elif 12 <= hour < 17:
            return "いってらっしゃい！また後で会おうね、プロデューサーくん！"
        elif 17 <= hour < 21:
            return "お疲れ様！ゆっくり休んでね、プロデューサーくん！"
        elif 21 <= hour < 24:
            return "おやすみ…プロデューサーくんもゆっくり休んでね🌙"
        else:  # 0-4時
            return "こんな時間まで…お疲れ様。ちゃんと寝るんだよ！プロデューサーくん。"


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
        
        # 好感度を更新（返信の前に更新して、反応に反映させる）
        old_affinity = affinity_manager.get_affinity(user_id)
        new_affinity = affinity_manager.add_affinity(user_id, affinity_change)
        
        # システムプロンプトを構築
        system_prompt = build_system_prompt(user_id)
        
        # 好感度変動をプロンプトに追加
        if affinity_change < 0:
            mood_hint = f"\n\n【注意: ユーザーの発言は少し失礼でした。好感度が{affinity_change}下がりました。少し傷ついた様子で返答してください】"
        elif affinity_change >= 3:
            mood_hint = f"\n\n【注意: ユーザーの発言はとても優しかったです。好感度が+{affinity_change}上がりました。嬉しそうに返答してください】"
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
        
        # Discord 2000文字制限に対応（分割送信）
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
        
        # 記憶を更新（バックグラウンドで）
        try:
            old_memory = memory_manager.get_memory(user_id)
            memory_prompt = build_memory_update_prompt(old_memory, message, reply)
            memory_response = client.chat.completions.create(
                model=MODEL_IDENTIFIER,
                messages=[{"role": "user", "content": memory_prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            new_memory = memory_response.choices[0].message.content.strip()
            memory_manager.update_memory(user_id, new_memory)
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


@bot.tree.command(name="shutdown", description="BOTを停止する（管理者のみ）")
async def shutdown_bot(interaction: discord.Interaction):
    # 管理者チェック（サーバー管理者のみ実行可能）
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
    """BOTを実行（graceful shutdown対応）"""
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