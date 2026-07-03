"""実行前の前提条件チェック."""

from __future__ import annotations

from pathlib import Path

from src.history import ExperimentHistory
from src.template_guard import collect_markdown_files


def check_template_dir(template_dir: Path) -> None:
    """親リポジトリの cursor_template が参照可能か確認する."""
    try:
        collect_markdown_files(template_dir)
    except (NotADirectoryError, FileNotFoundError) as exc:
        raise FileNotFoundError(
            f"{exc}\n"
            "template_dir に親リポジトリ上の cursor_template を指定してください。"
        ) from exc


def ensure_log_dir(log_dir: Path) -> None:
    """log 出力先ディレクトリを存在しなければ作成する."""
    if log_dir.exists() and not log_dir.is_dir():
        raise NotADirectoryError(f"log ディレクトリとして使用できません: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)


def check_output_files(
    order_dir: Path,
    log_dir: Path,
    history: ExperimentHistory,
    *,
    force: bool,
) -> None:
    """出力先ファイルの上書き可否を確認する."""
    ensure_log_dir(log_dir)

    order_path = order_dir / history.next_order_filename
    log_path = log_dir / history.next_log_filename
    existing = [p for p in (order_path, log_path) if p.exists()]
    if existing and not force:
        names = ", ".join(p.name for p in existing)
        raise FileExistsError(
            f"出力ファイルが既に存在します: {names}\n"
            "上書きする場合は --force を指定してください。"
        )
