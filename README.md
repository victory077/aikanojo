# AI彼女BOT - 莉波 (Rinami)

Discord上でローカルLLMを使ったAI彼女BOTです。学園アイドルマスターの姫崎莉波をモデルにしています。

## 機能

- **キャラクターロールプレイ**: YAMLで定義されたキャラクター設定に基づいて応答
- **ユーザー別好感度システム**: 会話内容に応じて好感度が増減（-5〜+5）
- **ユーザー別記憶**: 重要な会話内容を圧縮保存（最大2000文字）
- **時間帯別挨拶**: 起動・停止時に時間に応じたセリフ
- **Discord向け出力整形**: Linterによる自動フォーマット

## セットアップ

### 1. 依存関係のインストール
```bash
uv sync
```

### 2. 環境変数の設定
`.env`ファイルを作成:
```env
DISCORD_BOT_TOKEN=your_discord_bot_token
LM_STUDIO_API_KEY=lm-studio
LM_STUDIO_BASE_URL=http://localhost:1234/v1
MODEL_IDENTIFIER=your_model_name
NOTIFY_CHANNEL_ID=your_channel_id
```

### 3. 起動
```bash
uv run src/main.py
```

## コマンド

| コマンド | 説明 |
|----------|------|
| `/ask <メッセージ>` | AIに話しかける |
| `/affinity` | 自分の好感度を確認 |
| `/shutdown` | BOTを停止（管理者のみ） |

## ファイル構成

```
aikanojo/
├── src/                    # ソースコード
│   ├── __init__.py
│   ├── main.py             # メインBOT
│   ├── affinity.py         # 好感度管理
│   ├── memory.py           # 記憶管理
│   └── linter.py           # 出力整形
├── config/                 # 設定ファイル
│   ├── character.yaml      # キャラクター設定
│   └── linter.yaml         # 整形ルール
├── data/                   # ユーザーデータ（自動生成）
│   ├── user_affinity.json
│   └── user_memory.json
├── .env                    # 環境変数
├── pyproject.toml
└── README.md
```

## カスタマイズ

- **キャラクター変更**: `config/character.yaml`を編集
- **整形ルール変更**: `config/linter.yaml`を編集
- **好感度設定**: `config/character.yaml`の`affinity_config`を編集

## ライセンス

MIT
