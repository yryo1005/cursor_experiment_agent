"""LangGraph ワークフロー."""

from __future__ import annotations

import json
import operator
import re
from pathlib import Path
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src.config import (
    DEFAULT_AGENT_DELAY_SEC,
    DEFAULT_MAX_DEBATE_ROUNDS,
    DEFAULT_MAX_REVISIONS,
    create_llm,
    invoke_with_retry,
    run_with_delay,
)
from src.history import ExperimentHistory, format_history_context
from src.log_format import format_agent_logs, format_red_team_summary
from src.progress import ProgressReporter
from src.prompts import (
    DATA_SCIENTIST_SYSTEM,
    EXTRACT_TEMPLATE_SYSTEM,
    GENERATOR_SYSTEM,
    ML_ENGINEER_SYSTEM,
    RED_TEAM_SYSTEM,
    build_debate_user_prompt,
    build_extract_template_user_prompt,
    build_generate_user_prompt,
    build_red_team_user_prompt,
)
from src.schemas import OrderDraft, RedTeamReview, TemplateEssentials
from src.template_guard import (
    build_agent_template_section,
    build_exclusion_guide,
    load_all_template_markdown,
)


class AgentState(TypedDict):
    history: ExperimentHistory
    history_text: str
    template_context: str
    template_files: list[str]
    template_essentials: str
    exclusion_guide: str
    debate_round: int
    max_debate_rounds: int
    debate_summaries: Annotated[list[str], operator.add]
    final_plan: str
    order_draft: str
    red_team_review: RedTeamReview | None
    revision_count: int
    max_revisions: int
    agent_logs: Annotated[list[dict], operator.add]


def _parse_json_response(text: str, model_cls: type):
    """LLM 応答から JSON を抽出して Pydantic モデルへ変換する."""
    cleaned = text.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    else:
        brace_match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if brace_match:
            cleaned = brace_match.group(0)
    data = json.loads(cleaned)
    return model_cls.model_validate(data)


def _structured_invoke(llm, system: str, user: str, model_cls):
    """構造化出力で LLM を呼び出す."""
    structured_llm = llm.with_structured_output(model_cls)
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]
    try:
        result = structured_llm.invoke(messages)
        if isinstance(result, model_cls):
            return result
        return model_cls.model_validate(result)
    except Exception:  # noqa: BLE001 - フォールバックで手動パース
        raw = invoke_with_retry(llm, messages)
        return _parse_json_response(raw, model_cls)


def make_extract_template_node(llm, progress: ProgressReporter):
    """cursor_template から重要事項を抽出するノードを生成する."""

    def extract_template_node(state: AgentState) -> dict:
        key = "extract_template"
        progress.node_begin(key)
        user_prompt = build_extract_template_user_prompt(
            state["template_context"],
            state["template_files"],
        )
        result = run_with_delay(
            lambda: _structured_invoke(
                llm,
                EXTRACT_TEMPLATE_SYSTEM,
                user_prompt,
                TemplateEssentials,
            ),
            delay_sec=DEFAULT_AGENT_DELAY_SEC,
        )
        essentials = result.essentials_markdown
        progress.node_end(key, "extract_template")
        return {
            "template_essentials": essentials,
            "exclusion_guide": build_exclusion_guide(essentials),
            "agent_logs": [{
                "node": "extract_template",
                "source_files": state["template_files"],
                "essentials": essentials,
            }],
        }

    return extract_template_node


def make_debate_node(llm, progress: ProgressReporter):
    """ディベートノードを生成する."""

    def debate_node(state: AgentState) -> dict:
        round_num = state["debate_round"] + 1
        max_rounds = state["max_debate_rounds"]
        key = f"debate-{round_num}"
        progress.node_begin(key)

        prior_summary = state["debate_summaries"][-1] if state["debate_summaries"] else ""
        template_section = build_agent_template_section(state["template_essentials"])
        user_prompt = build_debate_user_prompt(
            state["history_text"],
            round_num,
            prior_summary,
            template_section,
        )

        def ds_call():
            return invoke_with_retry(
                llm,
                [
                    SystemMessage(content=DATA_SCIENTIST_SYSTEM),
                    HumanMessage(content=user_prompt),
                ],
            )

        def me_call():
            return invoke_with_retry(
                llm,
                [
                    SystemMessage(content=ML_ENGINEER_SYSTEM),
                    HumanMessage(content=user_prompt + "\n\nデータサイエンティストの視点も考慮してください。"),
                ],
            )

        ds_view = run_with_delay(ds_call, delay_sec=DEFAULT_AGENT_DELAY_SEC)
        me_view = run_with_delay(me_call, delay_sec=DEFAULT_AGENT_DELAY_SEC)

        consensus_prompt = (
            f"{user_prompt}\n\n"
            f"データサイエンティストの意見:\n{ds_view}\n\n"
            f"MLエンジニアの意見:\n{me_view}\n\n"
            "上記を統合した合意要約を1段落で作成してください。"
        )
        consensus = run_with_delay(
            lambda: invoke_with_retry(
                llm,
                [SystemMessage(content="合意形成のファシリテーターです。"), HumanMessage(content=consensus_prompt)],
            ),
            delay_sec=DEFAULT_AGENT_DELAY_SEC,
        )

        logs = [{
            "node": "debate",
            "round": round_num,
            "data_scientist": ds_view,
            "ml_engineer": me_view,
            "consensus": consensus,
        }]

        updates: dict = {
            "debate_round": round_num,
            "debate_summaries": [consensus],
            "agent_logs": logs,
        }

        if round_num >= max_rounds:
            final_plan = run_with_delay(
                lambda: invoke_with_retry(
                    llm,
                    [
                        SystemMessage(content="次期実験プランを簡潔にまとめてください。"),
                        HumanMessage(
                            content=(
                                f"履歴:\n{state['history_text']}\n\n"
                                f"テンプレート重要事項:\n{state['template_essentials']}\n\n"
                                f"ディベート要約:\n" + "\n".join(state["debate_summaries"] + [consensus])
                            )
                        ),
                    ],
                ),
                delay_sec=DEFAULT_AGENT_DELAY_SEC,
            )
            updates["final_plan"] = final_plan
            updates["agent_logs"] = logs + [{"node": "debate_final_plan", "content": final_plan}]

        progress.node_end(key, f"debate ラウンド {round_num}/{max_rounds}")
        return updates

    return debate_node


def make_generate_node(llm, progress: ProgressReporter):
    """指示書生成ノードを生成する."""

    def generate_node(state: AgentState) -> dict:
        revision_num = state["revision_count"]
        key = f"generate-{revision_num}"
        progress.node_begin(key)

        revision = ""
        if state["red_team_review"] and not state["red_team_review"].approved:
            revision = state["red_team_review"].revision_instructions

        user_prompt = build_generate_user_prompt(
            state["history_text"],
            state["final_plan"],
            state["exclusion_guide"],
            revision,
        )

        draft = run_with_delay(
            lambda: _structured_invoke(llm, GENERATOR_SYSTEM, user_prompt, OrderDraft),
            delay_sec=DEFAULT_AGENT_DELAY_SEC,
        )
        markdown = draft.to_markdown()
        label = "generate" if revision_num == 0 else f"generate（差し戻し {revision_num} 回目）"
        progress.node_end(key, label)
        return {
            "order_draft": markdown,
            "agent_logs": [{
                "node": "generate",
                "revision_count": revision_num,
                "markdown": markdown,
            }],
        }

    return generate_node


def make_red_team_node(llm, progress: ProgressReporter):
    """レッドチームノードを生成する."""

    def red_team_node(state: AgentState) -> dict:
        revision_num = state["revision_count"]
        key = f"red_team-{revision_num}"
        progress.node_begin(key)

        user_prompt = build_red_team_user_prompt(
            state["history_text"],
            state["order_draft"],
            state["template_essentials"],
        )
        review = run_with_delay(
            lambda: _structured_invoke(llm, RED_TEAM_SYSTEM, user_prompt, RedTeamReview),
            delay_sec=DEFAULT_AGENT_DELAY_SEC,
        )
        status = "承認" if review.approved else "差し戻し"
        progress.node_end(key, f"red_team（{status}）")
        return {
            "red_team_review": review,
            "agent_logs": [{"node": "red_team", "review": review.model_dump()}],
        }

    return red_team_node


def should_continue_debate(state: AgentState) -> str:
    """ディベート継続か生成へ進むかを判定する."""
    if state["debate_round"] >= state["max_debate_rounds"]:
        return "generate"
    return "debate"


def should_revise_or_end(state: AgentState) -> str:
    """レッドチーム結果に基づき差し戻しか終了かを判定する."""
    review = state["red_team_review"]
    if review and review.approved:
        return "end"

    if state["revision_count"] >= state["max_revisions"]:
        return "end"

    return "revise"


def make_increment_revision_node(progress: ProgressReporter):
    """差し戻しカウンタを増やすノード."""

    def increment_revision(state: AgentState) -> dict:
        next_count = state["revision_count"] + 1
        key = f"increment_revision-{next_count}"
        progress.node_begin(key)
        progress.node_end(key, f"差し戻し ({next_count}/{state['max_revisions']})")
        return {"revision_count": next_count}

    return increment_revision


def build_graph(
    tokens_path: Path,
    *,
    template_dir: Path,
    max_debate_rounds: int = DEFAULT_MAX_DEBATE_ROUNDS,
    max_revisions: int = DEFAULT_MAX_REVISIONS,
    model: str | None = None,
    progress: ProgressReporter | None = None,
):
    """LangGraph ワークフローを構築する."""
    reporter = progress or ProgressReporter(enabled=False)

    llm_kwargs: dict = {"tokens_path": tokens_path}
    if model:
        llm_kwargs["model"] = model
    llm = create_llm(**llm_kwargs)

    graph = StateGraph(AgentState)
    graph.add_node("extract_template", make_extract_template_node(llm, reporter))
    graph.add_node("debate", make_debate_node(llm, reporter))
    graph.add_node("generate", make_generate_node(llm, reporter))
    graph.add_node("red_team", make_red_team_node(llm, reporter))
    graph.add_node("increment_revision", make_increment_revision_node(reporter))

    graph.add_edge(START, "extract_template")
    graph.add_edge("extract_template", "debate")
    graph.add_conditional_edges("debate", should_continue_debate, {
        "debate": "debate",
        "generate": "generate",
    })
    graph.add_edge("generate", "red_team")
    graph.add_conditional_edges("red_team", should_revise_or_end, {
        "revise": "increment_revision",
        "end": END,
    })
    graph.add_edge("increment_revision", "generate")

    compiled = graph.compile()

    def run(history: ExperimentHistory) -> AgentState:
        template_context, template_files = load_all_template_markdown(template_dir)
        initial: AgentState = {
            "history": history,
            "history_text": format_history_context(history),
            "template_context": template_context,
            "template_files": template_files,
            "template_essentials": "",
            "exclusion_guide": "",
            "debate_round": 0,
            "max_debate_rounds": max_debate_rounds,
            "debate_summaries": [],
            "final_plan": "",
            "order_draft": "",
            "red_team_review": None,
            "revision_count": 0,
            "max_revisions": max_revisions,
            "agent_logs": [],
        }

        final_state: AgentState = initial
        for state in compiled.stream(initial, stream_mode="values"):
            final_state = state
        return final_state

    return run


def format_log_markdown(state: AgentState, history: ExperimentHistory) -> str:
    """エージェントログを Markdown 形式へ整形する."""
    lines = [
        f"# Agent Log {history.next_index:03d}",
        "",
    ]

    if state.get("template_essentials"):
        lines.extend([
            "## cursor_template 重要事項（抽出結果）",
            state["template_essentials"],
            "",
        ])

    lines.extend(["## ディベート要約"])
    for i, summary in enumerate(state["debate_summaries"], start=1):
        lines.extend([f"### Round {i}", summary, ""])

    if state["final_plan"]:
        lines.extend(["## 最終プラン", state["final_plan"], ""])

    lines.extend(format_red_team_summary(state.get("red_team_review")))

    lines.extend([
        "## エージェント会話ログ",
        format_agent_logs(state["agent_logs"]),
    ])
    return "\n".join(lines).strip() + "\n"
