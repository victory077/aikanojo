# CLAUDE.md - AI彼女BOT「莉波」開発ガイド

Discord上でローカルLLM（LM Studio）を使ったAI彼女BOT。キャラクターをモデルにしたキャラクターロールプレイBOT。

## Workflow Orchestration

### 1. Plan Mode Default

- 非自明なタスク（3ステップ以上or設計判断が必要）は必ずプランモードから始める
- うまくいかなければ即座に止めて再計画する — 強引に推し進めない
- 検証ステップにもプランモードを使う（ビルドだけではなく）
- 曖昧さを減らすために、事前に詳細な仕様を書き出す

### 2. Verification Before Done

- 動作確認なしにタスク完了としない
- `uv run pytest` でテストを実行し、全テストがパスすることを確認する
- 「スタッフエンジニアが承認するか？」を自問する
- テスト実行、ログ確認、正しさの実証を行う

### 3. Self-Improvement Loop

- ユーザーの修正後、`ISSUES.md`にパターンを記録
- 同じミスを防ぐルールを自分で書く
- ミス率が下がるまでこのルールを繰り返しブラッシュアップ

### 4. Demand Elegance (Balanced)

- 非自明な変更はまず「もっとエレガントな方法はないか？」と立ち止まる
- ハック感のある修正は避け、知識を総動員して最善の解を実装
- 単純で明白な修正にはこのステップを省いてOK — 過剰設計しない

### 5. Autonomous Bug Fixing

- バグレポートを受けたら自分で直す。手取り足取り聞かない
- ログ、エラー、失敗テストを指差し確認してから解決する
- ユーザーのコンテキストスイッチをゼロにする

## Task Management

1. **Plan First**: 計画を`tasks/todo.md`にチェック可能な箇条書きで書く
2. **Verify Plan**: 実装開始前にユーザーに確認
3. **Track Progress**: 完了した項目を随時マークする
4. **Explain Changes**: 各ステップでハイレベルなサマリーを記述
5. **Document Results**: `tasks/todo.md`にレビューセクションを追加
6. **Capture Lessons**: 修正があれば`ISSUES.md`を更新

## Core Principles

- **Simplicity First**: 変更はできる限りシンプルに。影響コードを最小限にする
- **No Laziness**: 根本原因を見つける。一時的な修正は禁止。シニア開発者基準
- **Minimal Impact**: 必要な箇所だけ変更する。バグの導入を避ける

## Project Overview

```
aikanojo/
├── src/                    # ソースコード
│   ├── __init__.py
│   ├── main.py             # メインBOT（Discord連携、LLM呼び出し）
│   ├── affinity.py         # 好感度管理（AffinityManager）
│   ├── memory.py           # 記憶管理（MemoryManager、3層構造）
│   ├── linter.py           # 出力整形（Discord向けフォーマット）
│   └── character_prompt.py # キャラYAML生成プロンプト
├── config/                 # 設定ファイル
│   ├── character.yaml      # キャラクター設定（プロフィール、プロンプト、好感度レベル）
│   └── linter.yaml         # 出力整形ルール（禁止パターン、置換ルール）
├── data/                   # ユーザーデータ（自動生成、gitignore対象）
│   ├── user_affinity.yaml  # 好感度データ
│   └── user_memory.yaml    # 記憶データ
├── tests/                  # テストコード
│   ├── test_affinity.py
│   ├── test_character_prompt.py
│   ├── test_linter.py
│   └── test_memory.py
├── .env                    # 環境変数（gitignore対象）
├── pyproject.toml          # プロジェクト設定（uv）
├── pytest.ini              # テスト設定
├── CHANGELOG.md            # 変更履歴
├── ISSUES.md               # 課題・要望リスト
└── README.md               # プロジェクト説明
```

## Tech Stack

- **Language**: Python 3.12+
- **Package Manager**: uv（`uv sync` / `uv run`）
- **Discord**: discord.py 2.6.4+
- **LLM**: LM Studio（OpenAI互換API経由）、openai パッケージ使用
- **Data**: YAML（pyyaml）で永続化
- **Env**: python-dotenv
- **Test**: pytest

## Architecture

### モジュール構成

| モジュール | 責務 | 主要クラス/関数 |
|-----------|------|----------------|
| `main.py` | Discord BOT本体、LLM呼び出し、コマンド管理 | `build_system_prompt()`, `analyze_message_sentiment()`, `ask()` |
| `affinity.py` | ユーザー別好感度の管理・永続化 | `AffinityManager`, `get_affinity_level()` |
| `memory.py` | ユーザー別記憶の3層管理 | `MemoryManager`, `build_memory_update_prompt()` |
| `linter.py` | LLM出力のDiscord向け整形 | `format_for_discord()`, `load_linter_rules()` |
| `character_prompt.py` | 外部AI用キャラYAML生成プロンプト | `build_character_generation_prompt()` |

### 記憶システム（3層構造）

- **長期記憶（permanent）**: 名前、好み、約束など（最大300文字）
- **中期記憶（topics）**: 会話トピック（最大10件、日付付き、キーワードマッチで取得）
- **短期記憶（recent）**: 直近の会話要約（最大200文字）

### 好感度システム

- 初期値: 20、範囲: 0–100
- メッセージ感情分析で -5〜+5 変動
- 4段階レベル: low(0-30) → medium(31-60) → high(61-85) → max(86-100)
- レベルに応じてシステムプロンプトが動的に変化

### データフロー

```
ユーザー入力 → /askコマンド
  → 感情分析 → 好感度更新（AffinityManager）
  → システムプロンプト構築（好感度レベル + 記憶）
  → LM Studio API呼び出し
  → 出力整形（linter.py）
  → Discord送信（2000文字制限で分割）
  → 記憶更新（MemoryManager）
```

## Discord Commands

| コマンド | 説明 |
| -------- | ---- |
| `/ask <メッセージ>` | AIに話しかける |
| `/affinity` | 自分の好感度を確認 |
| `/change <作品名> <キャラ名>` | キャラYAML生成プロンプトを出力 |
| `/shutdown` | BOTを停止（管理者のみ） |

## Dev Commands

```bash
# 依存関係インストール
uv sync

# BOT起動
uv run src/main.py

# テスト実行
uv run pytest

# 特定テストのみ
uv run pytest tests/test_affinity.py -v
```

## Environment Variables (.env)

```env
DISCORD_BOT_TOKEN=       # Discord Bot トークン
LM_STUDIO_API_KEY=       # LM Studio API キー（通常 "lm-studio"）
LM_STUDIO_BASE_URL=      # LM Studio URL（通常 "http://localhost:1234/v1"）
MODEL_IDENTIFIER=        # 使用するモデル名
NOTIFY_CHANNEL_ID=       # 起動/停止通知チャンネルID
```

## Key Conventions

### コーディング規約

- 日本語でdocstringとコメントを書く
- 型ヒントを使用する（`-> str`, `dict[str, dict]`など）
- データ永続化はYAML形式（JSON非推奨）
- ファイルパスは`pathlib.Path`を使用
- エンコーディングは常に`utf-8`を明示

### キャラクター設定

- キャラクター定義は`config/character.yaml`に集約
- システムプロンプトの動的構築（好感度 + 記憶 + キャラ設定）
- Discord出力の整形ルールは`config/linter.yaml`で外部設定化

### テスト

- `tests/`配下に`test_*.py`形式で配置
- ファイルI/Oは`tmp_path`フィクスチャでテスト用に隔離
- テスト実行は`uv run pytest`

## Known Issues（ISSUES.md参照）

- 語尾の不安定さ（ロールプレイが不自然になることがある）
- 記憶の反映が不十分（記憶を無視した回答をすることがある）
- 過剰な謝罪（ChatGPTの癖が出る）
- キャラクター追加機能（yaml増加 + 選択機構）

## Current Version

v0.4.1（2026-02-06）

- 3層記憶システム
- YAML形式でのデータ保存
- テストコード完備
