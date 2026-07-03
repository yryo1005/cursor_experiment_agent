"""実行進捗の標準出力（ノード完了時のみ）."""

from __future__ import annotations

import time


class ProgressReporter:
    """ノード完了時に所要時間だけを表示する."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._starts: dict[str, float] = {}

    def node_begin(self, key: str) -> None:
        """ノード処理の開始時刻を記録する（出力はしない）."""
        if self.enabled:
            self._starts[key] = time.monotonic()

    def node_end(self, key: str, label: str) -> None:
        """ノード完了と所要時間を表示する."""
        if not self.enabled:
            return
        start = self._starts.pop(key, time.monotonic())
        elapsed = time.monotonic() - start
        print(f"{label} 完了 ({elapsed:.1f}s)", flush=True)
