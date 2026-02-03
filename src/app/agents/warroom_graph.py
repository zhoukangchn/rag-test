"""Warroom Agent Graph 构建"""

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.app.agents.warroom_nodes import (
    sentinel_node,
    strategist_node,
    investigator_node,
    historian_node,
)
from src.app.agents.state import WarroomState


def route_next(state: WarroomState) -> str:
    """通用的动态路由：根据 state 中的 next_agent 决定下一步"""
    next_agent = state.get("next_agent", "end")
    if next_agent == "end":
        return END
    return next_agent


def build_warroom_graph() -> CompiledStateGraph:
    """
    构建作战室 (Warroom) 多智能体协同流程图。
    流程：Sentinel -> Strategist -> [Investigator <-> Strategist] -> Historian -> END
    """
    workflow = StateGraph(WarroomState)

    # 1. 添加节点
    workflow.add_node("sentinel", sentinel_node)
    workflow.add_node("strategist", strategist_node)
    workflow.add_node("investigator", investigator_node)
    workflow.add_node("historian", historian_node)

    # 2. 设置入口
    workflow.set_entry_point("sentinel")

    # 3. 设置边和路由
    # Sentinel 处理完后通常去 Strategist
    workflow.add_conditional_edges(
        "sentinel",
        route_next,
        {"strategist": "strategist", "end": END}
    )

    # Strategist 可以决定去调查 (Investigator) 或者结束调查生成报告 (Historian)
    workflow.add_conditional_edges(
        "strategist",
        route_next,
        {
            "investigator": "investigator",
            "historian": "historian",
            "end": END
        }
    )

    # Investigator 诊断完后返回 Strategist 汇报或直接去 Historian
    workflow.add_conditional_edges(
        "investigator",
        route_next,
        {
            "strategist": "strategist",
            "historian": "historian",
            "end": END
        }
    )

    # Historian 完成报告后结束
    workflow.add_conditional_edges(
        "historian",
        route_next,
        {"end": END}
    )

    return workflow.compile()


# 作战室 Agent 实例
warroom_agent = build_warroom_graph()
