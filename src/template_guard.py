"""cursor_template の読み込みと重要事項の整形."""

from __future__ import annotations

from pathlib import Path

ORDER_REFERENCE_LINE = (
    "@cursor_template/root_prompt.md の指示に従いプログラムを作成してください"
)


def collect_markdown_files(template_dir: Path) -> list[Path]:
    """cursor_template 以下の .md ファイルを再帰的に収集する."""
    if not template_dir.is_dir():
        raise NotADirectoryError(f"cursor_template ディレクトリが存在しません: {template_dir}")

    files = sorted(template_dir.rglob("*.md"))
    if not files:
        raise FileNotFoundError(
            f"cursor_template 内に .md ファイルがありません: {template_dir}"
        )
    return files


def load_all_template_markdown(template_dir: Path) -> tuple[str, list[str]]:
    """cursor_template 内の全 .md を読み込み、結合テキストと相対パス一覧を返す."""
    files = collect_markdown_files(template_dir)
    parts: list[str] = []
    rel_paths: list[str] = []
    for path in files:
        rel = path.relative_to(template_dir).as_posix()
        rel_paths.append(rel)
        parts.append(f"### {rel}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(parts), rel_paths


def build_agent_template_section(template_essentials: str) -> str:
    """後続エージェント向けのテンプレート重要事項セクションを組み立てる."""
    return (
        "## cursor_template 重要事項（事前抽出）\n"
        f"{template_essentials.strip()}\n\n"
        "order には上記で既に規定されている一般事項を繰り返し書かないこと。"
    )


def build_exclusion_guide(template_essentials: str) -> str:
    """order 生成・レビュー用の除外ガイドを組み立てる."""
    return build_agent_template_section(template_essentials)
