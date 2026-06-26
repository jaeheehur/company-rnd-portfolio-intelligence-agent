"""LangGraph StateGraph 빌드.

토폴로지:
  resolver → confirm (interrupt) → keywords
  keywords → news  ┐
  keywords → ip    ├─ fan-out (병렬)
  keywords → finance┘
  [news, ip, finance] → cross  ← fan-in (3개 완료 후)
  cross → report → summary → END
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from graph.state import IntelState
from graph.nodes.resolver import company_resolver, human_confirm
from graph.nodes.keywords import keyword_generator
from graph.nodes.news_agent import news_agent
from graph.nodes.ip_agent import ip_agent
from graph.nodes.finance_agent import finance_agent
from graph.nodes.cross_validate import cross_validator
from graph.nodes.reporter import chapter_writer, executive_summary


def build_graph() -> StateGraph:
    g = StateGraph(IntelState)

    g.add_node("resolver", company_resolver)
    g.add_node("confirm", human_confirm)
    g.add_node("keywords", keyword_generator)
    g.add_node("news", news_agent)
    g.add_node("ip", ip_agent)
    g.add_node("finance", finance_agent)
    g.add_node("cross", cross_validator)
    g.add_node("report", chapter_writer)
    g.add_node("summary", executive_summary)

    g.set_entry_point("resolver")
    g.add_edge("resolver", "confirm")
    g.add_edge("confirm", "keywords")

    # fan-out: keywords → 3 에이전트 병렬 실행
    g.add_edge("keywords", "news")
    g.add_edge("keywords", "ip")
    g.add_edge("keywords", "finance")

    # fan-in: 3 에이전트 모두 완료 → cross
    g.add_edge(["news", "ip", "finance"], "cross")

    g.add_edge("cross", "report")
    g.add_edge("report", "summary")
    g.add_edge("summary", END)

    return g.compile(checkpointer=MemorySaver())


graph = build_graph()
