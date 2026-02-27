# Changelog

## [0.6.0] - 2026-02-28

### Added

- **ChromaDBベクトル記憶** — 会話ログをセマンティック検索で取得可能に (`memory/chroma_store.py`)
- **CRAG (Corrective RAG)** — 検索結果の妥当性をLLMで評価しフィルタリング (`memory/crag_evaluator.py`)
- `LLMClient`クラス — LLM API呼び出しの一元管理 (`core/llm_client.py`)
- `build_system_prompt()`をpure function化 (`core/prompt_builder.py`)
- 断定形プロンプト — AIアシスタント的振る舞いの禁止、過剰謝罪防止
- `<thought>`タグによる返答前の心理分析強制（出力からは自動除去）
- voice_examples（口調の例）をシステムプロンプトに自動統合
- `tests/conftest.py` — pytestのsys.path設定を一元化
- `/affinity`コマンドにベクトル記憶数を表示

### Changed

- **ディレクトリ構成を大幅リファクタリング**: フラット`src/` → `src/bot/`, `src/core/`, `src/memory/` の3パッケージに分離
- `MemoryManager`がYAML 3層記憶 + ChromaDBセマンティック検索を統合
- 起動コマンドを `uv run src/main.py` → `uv run src/bot/main.py` に変更
- `pyproject.toml`にchromadb依存を追加、バージョンを0.6.0に更新

---

## [0.5.0] - 2026-02-25

### Added

- `/change`コマンド — LLMでキャラクターYAML + 挨拶テンプレートを自動生成（2ステップ）
- `docs/character_generation_prompt.md` — キャラYAML + 挨拶生成プロンプト（コピペ用・2ステップ）
- `CLAUDE.md` — 開発ガイドを追加

### Changed

- 挨拶文をハードコードから`config/greetings.yaml`に外部化（キャラ切替対応）

---

## [0.4.1] - 2026-02-06

### Added

- テストコードの追加

## [0.4.0] - 2026-02-06

### Added

- ユーザー記憶システムの3層化（短期記憶、中期記憶、長期記憶）（`memory.py`）

### Changed

- JSONをyamlに変更

## [0.3.0] - 2026-02-05

### Added

- 時間帯別挨拶機能（起動・停止時に時間に応じたセリフ）
- `/shutdown`コマンド（管理者のみ、おやすみメッセージ付き）
- 出力整形システム（`linter.py`, `linter.yaml`）
  - 見出しを太字に変換
  - Discord非対応記法の自動修正

### Changed

- 起動・停止メッセージをキャラクターに合わせた口調に変更

---

## [0.2.0] - 2026-02-05

### Added

- ユーザー別記憶システム（`memory.py`）
  - 会話の重要情報を圧縮保存（最大2000文字）
  - `user_memory.json`に永続化
- メッセージ感情分析による好感度変動（-5〜+5）
- Discord 2000文字制限対応（分割送信）

### Changed

- システムプロンプトに記憶情報を含めるよう更新

---

## [0.1.0] - 2026-02-05

### Added

- 基本的なDiscord BOT機能
- `/ask`コマンドでLLMに質問
- `/affinity`コマンドで好感度確認
- ユーザー別好感度システム（`affinity.py`）
  - `user_affinity.json`に永続化
- キャラクター設定ファイル（`character.yaml`）
  - 姫崎莉波のプロフィール・性格・口調
  - 好感度レベル別の態度変化
- LM Studio連携（OpenAI互換API）
