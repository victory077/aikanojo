# AI彼女BOT - 莉波 (Rinami)

Discord上でローカルLLM（LM Studio）を使ったAI彼女BOT。キャラクターロールプレイ + セマンティック記憶。

## 機能

- **キャラクターロールプレイ**: YAML定義のキャラ設定に基づいて応答（断定形プロンプト + `<thought>`タグによる心理分析）
- **セマンティック記憶**: ChromaDBベクトルDBで過去の会話を意味的に検索 + CRAG（妥当性評価）
- **4層記憶システム**: 長期（名前・好み）/ 中期（トピック）/ 短期（直近要約）/ ベクトル記憶
- **ユーザー別好感度**: 感情分析で-5〜+5変動、4段階レベルでプロンプトが動的変化
- **キャラクター生成**: `/change`コマンドでLLMによるキャラYAML自動生成
- **時間帯別挨拶**: 起動・停止時にキャラの口調で時間に応じたセリフ
- **Discord向け出力整形**: Linterによる自動フォーマット

## 必要環境

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) パッケージマネージャー
- [LM Studio](https://lmstudio.ai/)（ローカルLLMサーバー）
- Discord Bot Token

## セットアップ

### 1. 依存関係のインストール

```bash
uv sync
```

### 2. 環境変数の設定

`.env`ファイルを作成:

```env
DISCORD_BOT_TOKEN=your_discord_bot_token
LLM_API_KEY=lm-studio
LLM_BASE_URL=http://localhost:1234/v1
MODEL_IDENTIFIER=your_model_name
NOTIFY_CHANNEL_ID=your_channel_id
```

### 3. 起動

```bash
uv run src/bot/main.py
```

## コマンド

| コマンド | 説明 |
|----------|------|
| `/ask <メッセージ>` | AIに話しかける |
| `/affinity` | 自分の好感度を確認（ベクトル記憶数も表示） |
| `/change <作品名> <キャラ名>` | LLMでキャラYAML + 挨拶を自動生成 |
| `/shutdown` | BOTを停止（管理者のみ） |

## プロジェクト構成

```text
aikanojo/
├── src/
│   ├── bot/                    # Discord Botインターフェース層
│   │   └── main.py             # エントリポイント・コマンド定義
│   ├── core/                   # 推論・プロンプト構築
│   │   ├── llm_client.py       # OpenAI互換APIクライアント
│   │   └── prompt_builder.py   # システムプロンプト構築（断定形+thought）
│   ├── memory/                 # 記憶システム
│   │   ├── yaml_store.py       # YAML 3層記憶
│   │   ├── chroma_store.py     # ChromaDBベクトル記憶
│   │   ├── crag_evaluator.py   # CRAG（検索結果の妥当性評価）
│   │   └── manager.py          # 統合記憶マネージャー
│   ├── affinity.py             # 好感度管理
│   ├── linter.py               # 出力整形
│   └── character_prompt.py     # キャラYAML生成プロンプト
├── config/
│   ├── character.yaml          # キャラクター設定
│   ├── greetings.yaml          # 時間帯別挨拶テンプレート
│   └── linter.yaml             # 整形ルール
├── data/                       # ユーザーデータ（自動生成）
│   ├── user_affinity.yaml
│   ├── user_memory.yaml
│   └── chroma_db/              # ChromaDBベクトルデータ
└── tests/                      # ユニットテスト（80件）
```

## 技術スタック

| カテゴリ | 技術 |
|----------|------|
| 言語 | Python 3.12+ |
| パッケージ管理 | uv |
| Discord | discord.py |
| LLM | LM Studio（OpenAI互換API） |
| ベクトルDB | ChromaDB |
| データ永続化 | YAML（pyyaml） |
| テスト | pytest |

## 開発

```bash
# テスト実行
uv run pytest

# 特定テストのみ
uv run pytest tests/test_memory.py -v
```

## キャラクターの追加方法

1. BOT上で `/change <作品名> <キャラ名>` を実行（Web検索対応LLM推奨）
2. または [`docs/character_generation_prompt.md`](docs/character_generation_prompt.md) のプロンプトをChatGPT等に貼り付け
3. 生成されたYAMLを `config/character.yaml` と差し替えてBOT再起動

## カスタマイズ

- **キャラクター設定**: `config/character.yaml` を編集
- **整形ルール**: `config/linter.yaml` を編集
- **好感度設定**: `config/character.yaml` の `affinity_config` を編集

## ライセンス

MIT
