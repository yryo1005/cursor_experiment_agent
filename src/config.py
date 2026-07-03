"""API認証とLLM初期化."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, TypeVar

from langchain_google_genai import ChatGoogleGenerativeAI

T = TypeVar("T")

DEFAULT_MODEL = "gemini-3.5-flash"
DEFAULT_MAX_DEBATE_ROUNDS = 3
DEFAULT_MAX_REVISIONS = 2
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SEC = 5.0
DEFAULT_AGENT_DELAY_SEC = 2.0


def load_gemini_api_key(tokens_path: Path) -> str:
    """tokens.json から Gemini API キーを読み込む."""
    if not tokens_path.is_file():
        raise FileNotFoundError(f"tokens.json が見つかりません: {tokens_path}")

    with tokens_path.open(encoding="utf-8") as f:
        data = json.load(f)

    api_key = data.get("gemini")
    if not api_key or not isinstance(api_key, str):
        raise KeyError(f'tokens.json に有効な "gemini" キーがありません: {tokens_path}')

    return api_key


def create_llm(
    tokens_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
) -> ChatGoogleGenerativeAI:
    """ChatGoogleGenerativeAI インスタンスを生成する."""
    api_key = load_gemini_api_key(tokens_path)
    return ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=temperature,
    )


def invoke_with_retry(
    llm: ChatGoogleGenerativeAI,
    messages: list,
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay_sec: float = DEFAULT_RETRY_DELAY_SEC,
) -> str:
    """レートリミット対策付きで LLM を呼び出す."""
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = llm.invoke(messages)
            content = response.content
            if isinstance(content, list):
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            return str(content)
        except Exception as exc:  # noqa: BLE001 - API エラー種別は多様
            last_error = exc
            if attempt < max_retries - 1:
                time.sleep(retry_delay_sec * (attempt + 1))
    raise RuntimeError(f"LLM 呼び出しに失敗しました: {last_error}") from last_error


def run_with_delay(
    func: Callable[[], T],
    *,
    delay_sec: float = DEFAULT_AGENT_DELAY_SEC,
) -> T:
    """連続呼び出し間に遅延を入れて関数を実行する."""
    result = func()
    time.sleep(delay_sec)
    return result
