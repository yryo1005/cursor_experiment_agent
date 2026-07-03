"""order / report 履歴ファイルの検出と読み込み."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ORDER_PATTERN = re.compile(r"^order_(\d+)\.md$", re.IGNORECASE)
REPORT_PATTERN = re.compile(r"^report_(\d+)\.md$", re.IGNORECASE)


@dataclass(frozen=True)
class HistoryEntry:
    """1回分の実験履歴."""

    index: int
    order_path: Path
    report_path: Path
    order_text: str
    report_text: str


@dataclass(frozen=True)
class ExperimentHistory:
    """検出された全履歴と次の通し番号."""

    entries: list[HistoryEntry]
    next_index: int
    next_order_filename: str
    next_log_filename: str

    @property
    def latest_index(self) -> int:
        if not self.entries:
            return -1
        return self.entries[-1].index


def _find_indexed_files(directory: Path, pattern: re.Pattern[str]) -> dict[int, Path]:
    files: dict[int, Path] = {}
    for path in sorted(directory.iterdir()):
        if not path.is_file():
            continue
        match = pattern.match(path.name)
        if match:
            files[int(match.group(1))] = path
    return files


def find_orphan_orders(orders: dict[int, Path], reports: dict[int, Path]) -> list[int]:
    """report が無い order の通し番号一覧を返す."""
    return sorted(i for i in orders if i not in reports)


def load_experiment_history(order_dir: Path, report_dir: Path) -> ExperimentHistory:
    """指定ディレクトリから完了済み実験（order + report のペア）を昇順で読み込む."""
    if not order_dir.is_dir():
        raise NotADirectoryError(f"order ディレクトリが存在しません: {order_dir}")
    if not report_dir.is_dir():
        raise NotADirectoryError(f"report ディレクトリが存在しません: {report_dir}")

    orders = _find_indexed_files(order_dir, ORDER_PATTERN)
    reports = _find_indexed_files(report_dir, REPORT_PATTERN)

    if not orders:
        raise FileNotFoundError(f"order_*.md が見つかりません: {order_dir}")

    entries: list[HistoryEntry] = []
    for index in sorted(orders):
        report_path = reports.get(index)
        if report_path is None:
            continue
        entries.append(
            HistoryEntry(
                index=index,
                order_path=orders[index],
                report_path=report_path,
                order_text=orders[index].read_text(encoding="utf-8"),
                report_text=report_path.read_text(encoding="utf-8"),
            )
        )

    if not entries:
        raise FileNotFoundError(
            f"report 付きの order が1件もありません（order: {order_dir}, report: {report_dir}）\n"
            "実験を実施し report_*.md を作成してから Agent を実行してください。"
        )

    latest = entries[-1].index
    next_index = latest + 1
    width = max(len(str(latest)), 3)
    next_order_filename = f"order_{next_index:0{width}d}.md"
    next_log_filename = f"log_{next_index:0{width}d}.md"

    return ExperimentHistory(
        entries=entries,
        next_index=next_index,
        next_order_filename=next_order_filename,
        next_log_filename=next_log_filename,
    )


def warn_orphan_orders(order_dir: Path, report_dir: Path) -> None:
    """report の無い order について警告を表示する."""
    if not order_dir.is_dir() or not report_dir.is_dir():
        return
    orders = _find_indexed_files(order_dir, ORDER_PATTERN)
    reports = _find_indexed_files(report_dir, REPORT_PATTERN)
    for index in find_orphan_orders(orders, reports):
        print(
            f"[warn] order_{index:03d}.md はありますが report_{index:03d}.md がありません。"
            "履歴には含めず、実験完了後に report を追加してください。",
            file=sys.stderr,
        )


def format_history_context(history: ExperimentHistory) -> str:
    """エージェント向けに履歴を時系列テキストへ整形する."""
    sections: list[str] = []
    for entry in history.entries:
        section = [
            f"## 実験 {entry.index:03d}",
            "",
            "### 指示書 (order)",
            entry.order_text,
            "",
            "### 結果報告 (report)",
            entry.report_text,
        ]
        sections.append("\n".join(section))
    return "\n\n---\n\n".join(sections)
