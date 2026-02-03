"""Supervisor Graph 集成测试

验证 SRE Supervisor 能否根据状态路由正确调度子 Agent。
"""

import pytest

from src.sre.agents.shared.state import IncidentStatus, Severity
from src.sre.agents.supervisor.graph import sre_supervisor


@pytest.mark.asyncio
async def test_supervisor_full_loop():
    """测试 Supervisor 的完整调度循环"""

    # 初始化状态
    initial_state = {
        "incident_id": "SUP-TEST-001",
        "alert_source": "prometheus",
        "severity": Severity.MEDIUM,
        "title": "Latency Spike",
        "description": "API latency is higher than 500ms",
        "messages": [],
        "metrics_data": {},
        "log_entries": [],
        "resource_info": {},
        "time_context": {},
        "knowledge_context": "",
        "diagnosis_report": "",
        "root_cause_hypotheses": [],
        "selected_hypothesis": None,
        "confidence_score": 0.0,
        "action_plan": [],
        "pending_approval": [],
        "executed_actions": [],
        "rejected_actions": [],
        "status": IncidentStatus.MONITORING,
        "iteration": 0,
        "max_iterations": 5,
    }

    # 运行图
    print("\n[Supervisor Test] 启动完整编排循环...")
    final_state = await sre_supervisor.ainvoke(initial_state)

    # 验证状态流转
    # 在我们的新逻辑中：
    # 1. initialize (status: monitoring) -> router -> monitor_agent
    # 2. monitor_agent completes -> status: diagnosing -> returns to initialize
    # 3. initialize -> router -> diagnoser_agent
    # 4. diagnoser_agent completes -> status: executing -> returns to initialize
    # 5. initialize -> router -> executor_agent
    # 6. executor_agent completes -> status: resolved -> returns to initialize
    # 7. initialize -> router -> finalize -> END

    assert final_state["status"] == IncidentStatus.RESOLVED
    assert "final_report" in final_state
    assert "[Verification]" in final_state["diagnosis_report"]

    print("[Supervisor Test] 流程验证成功: MONITORING -> DIAGNOSING -> EXECUTING -> RESOLVED")
    print(f"[Supervisor Test] 最终报告内容摘要: {final_state['final_report'][:100]}...")
