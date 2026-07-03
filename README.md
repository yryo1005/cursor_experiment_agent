# Experiment Agent

過去の実験指示書（`order_{k}.md`）と結果報告書（`report_{k}.md`）を読み込み、マルチエージェント・ディベート（MAD）とレッドチーミングを経て、次期実験指示書 `order_{k+1}.md` を自動生成する LangGraph × Gemini API ベースの Agent です。

親リポジトリの Git サブモジュールとして配置し、実験リポジトリのルートから呼び出すことを想定しています。

## 概要

| 項目 | 内容 |
|:---|:---|
| 入力 | `order_*.md` + `report_*.md`（完了済み実験のペア）、`tokens.json`、`cursor_template/` |
| 出力 | `order_{n+1}.md`（次期実験指示書）、`log_{n+1}.md`（エージェント会話ログ） |
| LLM | Gemini API（`gemini-3.5-flash` 既定） |

### ワークフロー

1. **extract_template** — `cursor_template/` 内の全 `.md` を再帰読み込みし、重要事項を抽出
2. **debate** — データサイエンティストと ML エンジニアが議論（既定 3 ラウンド）
3. **generate** — 合意プランから実験固有の指示書を生成
4. **red_team** — 批評家が検証（不合格時は差し戻し）

技術詳細は [document.md](document.md) を参照してください。

---

## 使用方法

### 前提条件

- Python 3.10 以上
- Gemini API キー
- 親リポジトリに `cursor_template/`（実験プログラム作成用テンプレート）が配置されていること

### ディレクトリ構成（親リポジトリ）

```text
parent-repo/
├── cursor_template/          # テンプレート（本 Agent リポジトリ外）
├── orders/                   # order_000.md, order_001.md, …
├── reports/                  # report_000.md, report_001.md, …
├── logs/                     # log_000.md, log_001.md, …（Agent 出力）
├── ex001_.../                # 実験コード
└── Experiment_Agent_v2/      # 本リポジトリ（サブモジュール）
    ├── run_agent.py
    ├── src/
    ├── tokens.json           # API キー（git 管理外）
    └── tokens.json.example
```

### セットアップ

```bash
# 本リポジトリ（サブモジュール）で
pip install -r requirements.txt
cp tokens.json.example tokens.json
# tokens.json の "gemini" に API キーを設定
```

### 基本的な実行

実験を実施し `report_{k}.md` を作成したあと、親リポジトリのルートで:

```bash
python3 Experiment_Agent_v2/run_agent.py orders reports logs cursor_template
```

| 引数 | 説明 |
|:---|:---|
| `order_dir` | `order_*.md` の読み込み先・次期 order の出力先 |
| `report_dir` | `report_*.md` の読み込み先 |
| `log_dir` | `log_*.md` の出力先（**存在しなければ自動作成**） |
| `template_dir` | `cursor_template` の場所 |

### 実行例

```bash
# 親リポジトリから（推奨）
cd parent-repo
python3 Experiment_Agent_v2/run_agent.py orders reports logs cursor_template

# 本リポジトリ内のサンプルでデバッグ
cd Experiment_Agent_v2
python3 run_agent.py orders reports logs /path/to/cursor_template

# 進捗表示を抑制
python3 run_agent.py orders reports logs cursor_template --quiet

# 既存の出力を上書き
python3 run_agent.py orders reports logs cursor_template --force

# 短時間で試す（ディベート 2 ラウンド）
python3 run_agent.py orders reports logs cursor_template --max-debate-rounds 2
```

### 進捗表示

既定では、**各ノードの完了時のみ**所要時間を表示します。

```text
[info] 出力予定: order_001.md, log_001.md（履歴 1 件）
extract_template 完了 (12.3s)
debate ラウンド 1/3 完了 (48.7s)
debate ラウンド 2/3 完了 (51.2s)
...
generate 完了 (9.4s)
red_team（承認） 完了 (6.1s)
[done] orders/order_001.md
[done] logs/log_001.md
[done] レッドチーム: 承認
```

`--quiet` を付けると上記の進捗行は表示されません（エラーと最終結果のみ）。

### CLI オプション

| オプション | 既定値 | 説明 |
|:---|:---|:---|
| `order_dir` | （必須） | `order_*.md` のあるディレクトリ |
| `report_dir` | （必須） | `report_*.md` のあるディレクトリ |
| `log_dir` | （必須） | `log_*.md` の出力先（無ければ自動作成） |
| `template_dir` | （必須） | `cursor_template` の場所 |
| `--tokens-path` | 本リポジトリの `tokens.json` | API キーファイル |
| `--max-debate-rounds` | `3` | ディベート最大ラウンド数 |
| `--max-revisions` | `2` | レッドチーム差し戻し上限 |
| `--model` | `gemini-3.5-flash` | Gemini モデル名 |
| `--force` | オフ | 既存の出力ファイルを上書き |
| `--quiet` | オフ | ノード完了の進捗表示を抑制 |
| `--stdout-only` | オフ | ファイル書き込みなし |

### 入出力のルール

**履歴として読み込まれるのは `order_k.md` と `report_k.md` の両方が存在する実験のみです。**

| 状況 | 動作 |
|:---|:---|
| `order_000` + `report_000` あり | 履歴に含め、次は `order_001` を生成 |
| `order_001` のみ（report なし） | 履歴に含めない。警告を表示 |
| 出力ファイルが既に存在 | エラー（`--force` で上書き可） |

**order の形式**（`order_000.md` と同様）:

```markdown
@cursor_template/root_prompt.md の指示に従いプログラムを作成してください

- （実験固有の指示を短い箇条書きで）
```

一般事項（Docstring 義務、`train.ipynb` 配置規則など）は `cursor_template` 側に任せ、order には書きません。

---

## 想定される問題と対策

| 問題 | 原因 | 対策（実装済み） |
|:---|:---|:---|
| 実行中に出力が止まって見える | LLM 呼び出しに数十秒かかる | ノード完了時に所要時間を表示（`--quiet` で非表示） |
| report のない order が履歴に混入 | 旧実装が全 order を読み込んでいた | **report 付きペアのみ**を履歴に使用 |
| 次の order を生成できない | 前回の `order_*.md` が残っている | 上書き防止エラー。`--force` で再生成 |
| `logs/` が未作成 | 初回実行時にフォルダがない | **`log_dir` を自動作成** |
| cursor_template が見つからない | 親リポジトリに未配置 | `template_dir` でパス指定。起動時に検証 |
| order が長すぎる・テンプレートと重複 | 生成プロンプトの不足 | 簡潔な order を促すプロンプト + レッドチーム検証 |
| API キー漏洩 | `tokens.json` のコミット | `.gitignore` + `tokens.json.example` |
| 実行時間が長い | ディベート 3R × 複数 LLM 呼び出し | `--max-debate-rounds` で調整 |
| Gemini レートリミット | 連続 API 呼び出し | リトライ + 呼び出し間スリープ |

---

## 本リポジトリの構成

```text
Experiment_Agent_v2/
├── README.md
├── document.md
├── run_agent.py              # CLI エントリポイント
├── requirements.txt
├── tokens.json.example
├── orders/                     # 検証用サンプル
├── reports/
└── src/
    ├── config.py               # API 認証，LLM 生成，リトライ
    ├── graph.py                # LangGraph ワークフロー
    ├── history.py              # order/report の検出・読み込み
    ├── progress.py             # 進捗表示
    ├── prompts.py              # 各エージェントのプロンプト
    ├── schemas.py              # Pydantic 構造化出力
    ├── template_guard.py       # テンプレート再帰読み込み
    ├── log_format.py           # 会話ログの Markdown 整形
    └── setup_check.py          # 実行前チェック
```

---

## 関連ドキュメント

| ファイル | 内容 |
|:---|:---|
| [document.md](document.md) | アーキテクチャ・技術詳細 |
| [root_order_001.md](root_order_001.md) | 要件定義書 |
| [root_order_002.md](root_order_002.md) | テンプレート重複排除・ログ Markdown 化 |
| [root_order_003.md](root_order_003.md) | ディレクトリ引数・配置仕様 |
