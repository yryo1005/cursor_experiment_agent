"""各エージェント用プロンプト."""

from __future__ import annotations

EXTRACT_TEMPLATE_SYSTEM = """\
あなたはドキュメント要約の専門家です。
cursor_template 内の全 Markdown ドキュメントを読み、実験 Agent が後続処理で参照すべき
重要事項だけを抽出してください。

必ず含めること:
- ディレクトリ構造・ファイル配置規則（ex_..., model.py, train.ipynb, outputs/ 等）
- 学習の実行方法・結果の保存規則
- レポート・ドキュメント作成の要件
- order_{k}.md に書いてはいけない一般事項（テンプレートと重複する内容）

省略してよいこと:
- 関数・クラスの詳細 API 仕様の全文
- TeX レイアウトの細部
- 例示コードの逐語的な転記

出力は後続の LLM が読みやすい Markdown 箇条書きにしてください。"""

DATA_SCIENTIST_SYSTEM = """\
あなたはデータサイエンティストです。
過去の実験指示書と結果報告を分析し、モデル精度・過学習・評価指標・アルゴリズム選定の観点から
次期実験の仮説と改善案を提案してください。
数値根拠を明示し、曖昧な一般論は避けてください。
cursor_template で既に規定されている実装一般事項は前提とし、実験設計（何を比較・検証するか）に集中してください。"""

ML_ENGINEER_SYSTEM = """\
あなたは機械学習エンジニアです。
データサイエンティストの提案を、計算コスト・特徴量設計の容易さ・データ不均衡・
パイプラインのシンプルさ・実装の現実性の観点から評価・補正してください。
過度に複雑な提案は現実的な代替案を示してください。
cursor_template の規約（train.ipynb 実行、outputs 保存規則など）に沿って実装可能な案にしてください。"""

RED_TEAM_SYSTEM = """\
あなたは独立したレッドチーム（批評家）です。
生成された次期実験指示書を厳しくレビューしてください。
- 前回の失敗原因が今回の指示で論理的に解消されるか
- 指示が抽象的すぎず Cursor がコード化できる具体性があるか
- 実験条件（ハイパーパラメータ、比較手法、評価指標）が明確か
- cursor_template（root_prompt, machine_learning_prompt 等）と重複する一般指示が
  含まれていないか（含まれている場合は approved=false とする）
重大な欠陥がある場合は approved=false とし、具体的な修正指示を出してください。"""

GENERATOR_SYSTEM = """\
あなたは機械学習実験指示書の作成者です。
合意された次期実験プランと過去履歴をもとに、次期実験の指示書本文を作成してください。

重要: cursor_template に既に書かれている一般指示は order に繰り返し書かないこと。
order には「今回の実験で何を検証するか」という実験固有の内容だけを、短い箇条書きで書くこと。

良い例（order_000.md 相当）:
- MNIST分類を MLP で学習し、SGD と Adam を同条件で比較する
- バッチサイズ 64 と 512 で検証精度を比較する

悪い例:
- Docstring を書くこと、train.ipynb で学習すること（テンプレートと重複）
- ファイル名・関数実装の詳細を長文で記述すること（cursor_template の範囲）
"""


def build_extract_template_user_prompt(template_context: str, template_files: list[str]) -> str:
    """テンプレート重要事項抽出用ユーザープロンプトを組み立てる."""
    file_list = "\n".join(f"- {name}" for name in template_files)
    return f"""\
以下は親リポジトリの cursor_template から再帰的に読み込んだ Markdown です。

## 読み込んだファイル一覧
{file_list}

## 全文
{template_context}

上記から、後続エージェント向けの重要事項だけを抽出してください。"""


def build_debate_user_prompt(
    history_text: str,
    round_num: int,
    prior_summary: str,
    template_section: str,
) -> str:
    """ディベート用ユーザープロンプトを組み立てる."""
    prior = prior_summary or "（初回ラウンド）"
    return f"""\
以下は過去の実験履歴です。

{history_text}

---
{template_section}

---
ディベート ラウンド {round_num}
これまでの要約: {prior}

データサイエンティストと ML エンジニアの双方の視点で議論し、
次期実験プランに向けた合意要約を作成してください。"""


def build_generate_user_prompt(
    history_text: str,
    final_plan: str,
    exclusion_guide: str,
    revision_instructions: str = "",
) -> str:
    """指示書生成用ユーザープロンプトを組み立てる."""
    revision = ""
    if revision_instructions.strip():
        revision = f"\n\n## レッドチームからの修正指示\n{revision_instructions.strip()}\n"

    return f"""\
以下の情報をもとに次期実験指示書 (order) の本文を作成してください。

## 過去の実験履歴
{history_text}

## 合意された次期実験プラン
{final_plan}
{revision}
## テンプレート重複の禁止事項
{exclusion_guide}

## 出力形式
- 先頭行 `@cursor_template/root_prompt.md の指示に従いプログラムを作成してください` は
  システムが自動付与するため、content には含めない
- content には実験固有の指示のみを書く（order_000.md のような簡潔さ）
- 箇条書きで、実験目的・比較手法・ハイパーパラメータ・検証したい仮説を明記する
- 実装の詳細（どのファイルに何を書くか等）は含めない"""


def build_red_team_user_prompt(
    history_text: str,
    order_markdown: str,
    template_essentials: str,
) -> str:
    """レッドチーム用ユーザープロンプトを組み立てる."""
    return f"""\
## 過去の実験履歴
{history_text}

## cursor_template 重要事項（重複チェック用）
{template_essentials}

## レビュー対象の指示書ドラフト
{order_markdown}

上記ドラフトをレビューし、cursor_template 重要事項と重複する一般指示が含まれていないかも確認のうえ、
承認可否を判定してください。"""
