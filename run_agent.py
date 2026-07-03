#!/usr/bin/env python3
"""機械学習実験自動更新マルチエージェント Agent のエントリポイント."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.config import (
    DEFAULT_MAX_DEBATE_ROUNDS,
    DEFAULT_MAX_REVISIONS,
    load_gemini_api_key,
)
from src.graph import build_graph, format_log_markdown
from src.history import load_experiment_history, warn_orphan_orders
from src.progress import ProgressReporter
from src.setup_check import check_output_files, check_template_dir

def _default_tokens_path() -> Path:
    return Path(__file__).resolve().parent / "tokens.json"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """CLI 引数をパースする."""
    parser = argparse.ArgumentParser(
        description="過去の order/report 履歴から次期実験指示書を生成する",
    )
    parser.add_argument(
        "order_dir",
        type=Path,
        help="order_*.md が格納されたディレクトリ",
    )
    parser.add_argument(
        "report_dir",
        type=Path,
        help="report_*.md が格納されたディレクトリ",
    )
    parser.add_argument(
        "log_dir",
        type=Path,
        help="log_*.md の出力先ディレクトリ",
    )
    parser.add_argument(
        "template_dir",
        type=Path,
        help="cursor_template が格納されたディレクトリ",
    )
    parser.add_argument(
        "--tokens-path",
        type=Path,
        default=None,
        help="tokens.json のパス（省略時は本リポジトリ直下）",
    )
    parser.add_argument(
        "--max-debate-rounds",
        type=int,
        default=DEFAULT_MAX_DEBATE_ROUNDS,
        help=f"ディベートの最大ラウンド数（既定: {DEFAULT_MAX_DEBATE_ROUNDS}）",
    )
    parser.add_argument(
        "--max-revisions",
        type=int,
        default=DEFAULT_MAX_REVISIONS,
        help=f"レッドチーム差し戻しの最大回数（既定: {DEFAULT_MAX_REVISIONS}）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="使用する Gemini モデル名",
    )
    parser.add_argument(
        "--stdout-only",
        action="store_true",
        help="ファイル書き込みを行わず標準出力のみに出力する",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="既存の order / log 出力ファイルを上書きする",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="ノード完了の進捗表示を抑制する",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """メイン処理."""
    args = parse_args(argv)

    if args.max_debate_rounds < 1:
        print("[error] --max-debate-rounds は 1 以上を指定してください。", file=sys.stderr)
        return 1
    if args.max_revisions < 0:
        print("[error] --max-revisions は 0 以上を指定してください。", file=sys.stderr)
        return 1

    order_dir = args.order_dir.resolve()
    report_dir = args.report_dir.resolve()
    log_dir = args.log_dir.resolve()
    template_dir = args.template_dir.resolve()
    tokens_path = (args.tokens_path or _default_tokens_path()).resolve()

    try:
        check_template_dir(template_dir)
        load_gemini_api_key(tokens_path)
        warn_orphan_orders(order_dir, report_dir)
        history = load_experiment_history(order_dir, report_dir)
        if not args.stdout_only:
            check_output_files(order_dir, log_dir, history, force=args.force)
    except (FileNotFoundError, FileExistsError, KeyError, NotADirectoryError) as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    if not args.quiet:
        print(
            f"[info] 出力予定: {history.next_order_filename}, {history.next_log_filename}"
            f"（履歴 {len(history.entries)} 件）"
        )

    run_graph = build_graph(
        tokens_path,
        template_dir=template_dir,
        max_debate_rounds=args.max_debate_rounds,
        max_revisions=args.max_revisions,
        model=args.model,
        progress=ProgressReporter(enabled=not args.quiet),
    )

    try:
        state = run_graph(history)
    except RuntimeError as exc:
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    order_path = order_dir / history.next_order_filename
    log_path = log_dir / history.next_log_filename
    order_content = state["order_draft"]
    log_content = format_log_markdown(state, history)

    if args.stdout_only:
        print("\n" + "=" * 60)
        print(f"# {history.next_order_filename}")
        print("=" * 60)
        print(order_content)
        print("\n" + "=" * 60)
        print(f"# {history.next_log_filename}")
        print("=" * 60)
        print(log_content)
    else:
        order_path.write_text(order_content, encoding="utf-8")
        log_path.write_text(log_content, encoding="utf-8")
        print(f"[done] {order_path}")
        print(f"[done] {log_path}")

    review = state.get("red_team_review")
    if review:
        status = "承認" if review.approved else "差し戻し上限到達"
        print(f"[done] レッドチーム: {status}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
