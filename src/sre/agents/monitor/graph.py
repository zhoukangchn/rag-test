"""Monitor Agent 工作流定义"""

from langgraph.graph import END, START, StateGraph

from src.sre.agents.monitor.nodes import (
    analyze_logs_node,
    fetch_metrics_node,
    gather_context_node,
)
from src.sre.agents.shared.state import MonitorState


def build_monitor_graph():
    """构建 Monitor Agent 的内部工作流"""
    builder = StateGraph(MonitorState)

    # 添加节点
    builder.add_node("fetch_metrics", fetch_metrics_node)
    builder.add_node("analyze_logs", analyze_logs_node)
    builder.add_node("gather_context", gather_context_node)

    # 定义执行顺序：并行收集信息
    # 在这个简单的版本中，我们按顺序执行，或者可以设计为并行
    builder.add_edge(START, "fetch_metrics")
    builder.add_edge("fetch_metrics", "analyze_logs")
    builder.add_edge("analyze_logs", "gather_context")
    builder.add_edge("gather_context", END)

    return builder.compile()


# 导出编译后的 Graph
monitor_agent = build_monitor_graph()
