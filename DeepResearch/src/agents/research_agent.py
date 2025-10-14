from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

try:
    from pydantic_ai import Agent  # type: ignore
except Exception:  # pragma: no cover
    Agent = None  # type: ignore


from DeepResearch.src.datatypes.research import ResearchOutcome
from DeepResearch.src.prompts import PromptLoader
from DeepResearch.src.tools.pyd_ai_tools import _build_agent as _build_core_agent
from DeepResearch.src.tools.pyd_ai_tools import _build_builtin_tools, _build_toolsets

if TYPE_CHECKING:
    from omegaconf import DictConfig


def _compose_agent_system(
    cfg: DictConfig,
    url_list: list[str] | None = None,
    bad_requests: list[str] | None = None,
    beast: bool = False,
) -> str:
    loader = PromptLoader(cfg)
    header = loader.get("agent", "header")
    actions_wrapper = loader.get("agent", "actions_wrapper")
    footer = loader.get("agent", "footer")

    sections: list[str] = [
        header.replace(
            "${current_date_utc}",
            (
                __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
            ).strftime("%a, %d %b %Y %H:%M:%S GMT"),
        )
    ]

    # Visit
    visit = loader.get("agent", "action_visit")
    if url_list:
        url_lines = "\n".join(
            [
                f'  - [idx={i + 1}] [weight=1.00] "{u}": "..."'
                for i, u in enumerate(url_list or [])
            ]
        )
        sections.append(visit.replace("${url_list}", url_lines))

    # Search
    search = loader.get("agent", "action_search")
    if search:
        bad = ""
        if bad_requests:
            bad = (
                "- Avoid those unsuccessful search requests and queries:\n<bad-requests>\n"
                + "\n".join(bad_requests)
                + "\n</bad-requests>"
            )
        sections.append(search.replace("${bad_requests}", bad))

    # Answer variants
    action_answer = loader.get("agent", "action_answer")
    action_beast = loader.get("agent", "action_beast")
    sections.append(action_beast if beast else action_answer)

    # Reflect
    reflect = loader.get("agent", "action_reflect")
    if reflect:
        sections.append(reflect)

    # Coding
    coding = loader.get("agent", "action_coding")
    if coding:
        sections.append(coding)

    # Wrapper + footer
    sections.append(
        actions_wrapper.replace("${action_sections}", "\n\n".join(list(sections[1:])))
    )
    sections.append(footer)
    return "\n\n".join(sections)


def _ensure_core_agent(cfg: DictConfig):
    builtin = _build_builtin_tools(dict(cfg) if cfg else {})
    toolsets = _build_toolsets(dict(cfg) if cfg else {})
    agent, _ = _build_core_agent(dict(cfg) if cfg else {}, builtin, toolsets)
    return agent


def _run_object(agent: Any, system: str, user: str) -> dict[str, Any]:
    # Minimal wrapper to a structured object; fallback to text and simple routing
    try:
        result = agent.run_sync({"system": system, "user": user})
        if hasattr(result, "object"):
            return result.object
        return {"action": "answer", "answer": getattr(result, "output", str(result))}
    except Exception:
        return {"action": "answer", "answer": ""}


def _build_user(question: str, knowledge: list[tuple[str, str]] | None = None) -> str:
    messages: list[str] = []
    for q, a in knowledge or []:
        messages.append(q)
        messages.append(a)
    messages.append(question.strip())
    return "\n\n".join(messages)


@dataclass
class ResearchAgent:
    cfg: DictConfig
    max_steps: int = 8

    def run(self, question: str) -> ResearchOutcome:
        agent = _ensure_core_agent(self.cfg)
        if agent is None:
            return ResearchOutcome(
                answer="", references=[], context={"error": "pydantic_ai missing"}
            )

        knowledge: list[tuple[str, str]] = []
        url_pool: list[str] = []
        bad_queries: list[str] = []
        visited: list[str] = []
        final_answer: str = ""
        refs: list[str] = []

        for step in range(1, self.max_steps + 1):
            system = _compose_agent_system(self.cfg, url_pool, bad_queries, beast=False)
            user = _build_user(question, knowledge)
            obj = _run_object(agent, system, user)
            action = str(obj.get("action", "answer"))

            if action == "search":
                queries = obj.get("searchRequests") or obj.get("queries") or []
                if isinstance(queries, str):
                    queries = [queries]
                bad_queries.extend(list(queries))
                continue

            if action == "visit":
                targets = obj.get("URLTargets") or []
                for u in targets:
                    if u and u not in visited:
                        visited.append(u)
                        url_pool.append(u)
                continue

            if action == "reflect":
                qs = obj.get("questionsToAnswer") or []
                for subq in qs:
                    knowledge.append((subq, ""))
                continue

            # default: answer
            ans = obj.get("answer") or obj.get("mdAnswer") or ""
            if not ans and step < self.max_steps:
                continue
            final_answer = str(ans)
            # references may be returned directly
            maybe_refs = obj.get("references") or []
            refs = [
                r.get("url") if isinstance(r, dict) else str(r)
                for r in (maybe_refs or [])
                if r
            ]
            break

        if not final_answer:
            # Beast mode
            system = _compose_agent_system(self.cfg, url_pool, bad_queries, beast=True)
            user = _build_user(question, knowledge)
            obj = _run_object(agent, system, user)
            final_answer = str(obj.get("answer", ""))
            maybe_refs = obj.get("references") or []
            refs = [
                r.get("url") if isinstance(r, dict) else str(r)
                for r in (maybe_refs or [])
                if r
            ]

        return ResearchOutcome(
            answer=final_answer,
            references=refs,
            context={
                "visited": visited,
                "urls": url_pool,
                "bad_queries": bad_queries,
            },
        )


def run(question: str, cfg: DictConfig) -> ResearchOutcome:
    ra = ResearchAgent(cfg)
    return ra.run(question)
