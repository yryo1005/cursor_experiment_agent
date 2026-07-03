"""エージェント会話ログの Markdown 整形."""

from __future__ import annotations

from src.schemas import RedTeamReview


def format_agent_logs(agent_logs: list[dict]) -> str:
    """構造化ログを読みやすい Markdown に変換する."""
    if not agent_logs:
        return "（ログなし）"

    sections: list[str] = []
    for entry in agent_logs:
        node = entry.get("node", "unknown")
        if node == "debate":
            round_num = entry.get("round", "?")
            sections.append(f"### ディベート Round {round_num}")
            sections.append("")
            sections.append("#### データサイエンティスト")
            sections.append(entry.get("data_scientist", ""))
            sections.append("")
            sections.append("#### MLエンジニア")
            sections.append(entry.get("ml_engineer", ""))
            sections.append("")
            sections.append("#### 合意要約")
            sections.append(entry.get("consensus", ""))
            sections.append("")
        elif node == "debate_final_plan":
            sections.append("### 最終プラン（ディベート後）")
            sections.append("")
            sections.append(entry.get("content", ""))
            sections.append("")
        elif node == "extract_template":
            sections.append("### テンプレート重要事項の抽出")
            sections.append("")
            sources = entry.get("source_files") or []
            if sources:
                sections.append("#### 読み込んだファイル")
                for name in sources:
                    sections.append(f"- {name}")
                sections.append("")
            sections.append("#### 抽出結果")
            sections.append(entry.get("essentials", ""))
            sections.append("")
        elif node == "generate":
            revision = entry.get("revision_count", 0)
            sections.append(f"### 指示書生成（差し戻し回数: {revision}）")
            sections.append("")
            sections.append(entry.get("markdown", ""))
            sections.append("")
        elif node == "red_team":
            review = entry.get("review", {})
            sections.append("### レッドチームレビュー（詳細）")
            sections.append("")
            sections.extend(_format_review_dict(review))
            sections.append("")
        else:
            sections.append(f"### {node}")
            for key, value in entry.items():
                if key == "node":
                    continue
                sections.append(f"**{key}**: {value}")
            sections.append("")

    return "\n".join(sections).strip()


def format_red_team_summary(review: RedTeamReview | None) -> list[str]:
    """レッドチーム結果のサマリ行を返す."""
    if not review:
        return []

    lines = [
        "## レッドチームレビュー",
        f"- 承認: {'はい' if review.approved else 'いいえ'}",
        f"- 重大度: {review.severity}",
        f"- ボトルネック解消: {'はい' if review.bottleneck_addressed else 'いいえ'}",
        f"- 具体性: {'十分' if review.specificity_ok else '不足'}",
        "",
    ]
    if review.issues:
        lines.append("### 指摘事項")
        for issue in review.issues:
            lines.append(f"- {issue}")
        lines.append("")
    if review.revision_instructions:
        lines.extend(["### 修正指示", review.revision_instructions, ""])
    return lines


def _format_review_dict(review: dict) -> list[str]:
    lines = [
        f"- 承認: {'はい' if review.get('approved') else 'いいえ'}",
        f"- 重大度: {review.get('severity', 'unknown')}",
        f"- ボトルネック解消: {'はい' if review.get('bottleneck_addressed') else 'いいえ'}",
        f"- 具体性: {'十分' if review.get('specificity_ok') else '不足'}",
        "",
    ]
    issues = review.get("issues") or []
    if issues:
        lines.append("#### 指摘事項")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")
    revision = review.get("revision_instructions", "")
    if revision:
        lines.extend(["#### 修正指示", revision, ""])
    return lines
