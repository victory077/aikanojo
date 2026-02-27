# CLAUDE.md - AI彼女BOT 開発ガイド

プロジェクト概要・セットアップ・コマンド一覧は [README.md](README.md) を参照。
このファイルはAI開発アシスタント向けの**開発ルール・規約・設計判断**に特化する。

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

## Architecture

### モジュール責務

| モジュール | 責務 |
|---|---|
| `bot/main.py` | Discord BOT本体、コマンド管理 |
| `core/llm_client.py` | LLM API呼び出しの一元管理（`LLMClient`） |
| `core/prompt_builder.py` | システムプロンプト構築（断定形 + `<thought>`タグ） |
| `memory/yaml_store.py` | YAML 3層記憶（`YAMLMemoryStore`） |
| `memory/chroma_store.py` | ChromaDBベクトル記憶（`ChromaMemoryStore`） |
| `memory/crag_evaluator.py` | 検索結果の妥当性評価（CRAG） |
| `memory/manager.py` | YAML + ChromaDB + CRAG統合（`MemoryManager`） |
| `affinity.py` | 好感度管理（`AffinityManager`） |
| `linter.py` | LLM出力のDiscord向け整形 |
| `character_prompt.py` | キャラYAML生成プロンプト |

### データフロー

```text
/ask → 感情分析 → 好感度更新
  → 記憶検索（YAML + ChromaDB + CRAG評価）
  → プロンプト構築（断定形 + voice_examples）
  → LLM呼び出し → <thought>タグ除去 → linter整形
  → Discord送信 → ChromaDB保存 → YAML記憶更新
```

### プロンプトエンジニアリング

- **断定形**: 「あなたは〇〇である」でキャラのアイデンティティを定義
- **`<thought>`タグ**: 返答前に距離感・感情・踏み込み度を内部分析（出力から自動除去）
- **voice_examples**: character.yamlの口調例をプロンプトに自動組込
- **AIアシスタント禁止**: AI的言い回し・過剰謝罪を禁止

### CRAG（Corrective RAG）

1. ユーザー発言でChromaDBを検索（5件）
2. LLMに検索結果の関連性を判定させる（Y/N）
3. 関連ありと判定された記憶のみプロンプトに含める

### 記憶システム（4層）

| 層 | 保存先 | 検索方式 | 最大サイズ |
|---|---|---|---|
| 長期（permanent） | YAML | 常時表示 | 300文字 |
| 中期（topics） | YAML | キーワードマッチ | 10件 |
| 短期（recent） | YAML | 常時表示 | 200文字 |
| ベクトル | ChromaDB | セマンティック検索 | 無制限 |

### 好感度システム

- 初期値: 20、範囲: 0–100
- 感情分析で -5〜+5 変動
- 4段階: low(0-30) → medium(31-60) → high(61-85) → max(86-100)

## Key Conventions

### コーディング規約

- 日本語でdocstringとコメントを書く
- 型ヒントを使用する（`-> str`, `dict[str, dict]`など）
- データ永続化はYAML形式（JSON非推奨）
- ファイルパスは`pathlib.Path`を使用
- エンコーディングは常に`utf-8`を明示

### テスト

- `tests/conftest.py`で`sys.path`設定を一元化
- ファイルI/Oはコンストラクタ注入で隔離
- ChromaDBテストは`close()`→`_safe_rmtree()`でWindows対応
- テスト実行: `uv run pytest`

## Known Issues（ISSUES.md参照）

- 語尾の不安定さ（ロールプレイが不自然になることがある）
- 記憶の反映が不十分（記憶を無視した回答をすることがある）
- キャラクター追加機能（yaml増加 + 選択機構）

## Current Version

v0.6.0（2026-02-28）— 80テスト完備
