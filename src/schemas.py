"""構造化出力用スキーマ."""

from __future__ import annotations

from pydantic import BaseModel, Field


class DebateTurn(BaseModel):
    """ディベート1ラウンド分の出力."""

    data_scientist_view: str = Field(description="データサイエンティストの分析と提案")
    ml_engineer_view: str = Field(description="MLエンジニアの評価と補正")
    consensus_summary: str = Field(description="このラウンドの合意要約")


class DebateResult(BaseModel):
    """ディベート全体の結果."""

    rounds: list[DebateTurn]
    final_plan: str = Field(description="次期実験プランの最終合意内容")


class TemplateEssentials(BaseModel):
    """cursor_template から抽出した重要事項."""

    essentials_markdown: str = Field(
        description=(
            "後続エージェント（ディベート・生成・レッドチーム）が参照する重要事項。"
            "Markdown の箇条書きで、実装規約・ディレクトリ構造・order に書かない一般事項を含める"
        ),
    )


class OrderDraft(BaseModel):
    """生成する指示書（実験固有の内容のみ）."""

    content: str = Field(
        description=(
            "実験固有の指示のみ。"
            "cursor_template で既に規定されている一般事項（Docstring, document.md, "
            "ディレクトリ構造, train.ipynb, outputs 保存規則, visualize_result.ipynb 等）は含めない"
        ),
    )

    def to_markdown(self) -> str:
        """order_000.md と同様の簡潔な形式へ変換する."""
        from src.template_guard import ORDER_REFERENCE_LINE

        text = self.content.strip()
        if text.startswith(ORDER_REFERENCE_LINE):
            text = text[len(ORDER_REFERENCE_LINE):].strip()
        if not text:
            return f"{ORDER_REFERENCE_LINE}\n"
        return f"{ORDER_REFERENCE_LINE}\n\n{text}\n"


class RedTeamReview(BaseModel):
    """レッドチームのレビュー結果."""

    approved: bool = Field(description="指示書が実行可能で論理的に妥当なら true")
    severity: str = Field(description="critical / major / minor / none")
    bottleneck_addressed: bool = Field(
        description="前回のボトルネックが今回の指示で解消されるか"
    )
    specificity_ok: bool = Field(
        description="Cursor が迷わず実装できる具体性があるか"
    )
    issues: list[str] = Field(default_factory=list, description="指摘事項リスト")
    revision_instructions: str = Field(
        default="",
        description="不合格時の修正指示",
    )


class MarkdownValidation(BaseModel):
    """Markdown 形式の検証結果."""

    valid: bool
    issues: list[str] = Field(default_factory=list)
