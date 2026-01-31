"""测试 Supervisor指挥官工作流"""

import pytest
from src.sre.agents.supervisor.graph import sre_supervisor
from src.sre.agents.shared.state import Severity, IncidentStatus

@pytest.mark.asyncio
async def test_supervisor_orchestration():
    """测试 Supervisor 自动调度所有子 Agent 完成修复"""
    
    # 模拟一个原始告警输入
    initial_state = {
        "incident_id": "SUPER-INC-001",
        "alert_source": "manual",
        "severity": Severity.CRITICAL,
        "title": "Production Outage: Payment Service",
        "description": "Payment service is returning 500 errors",
        "status": IncidentStatus.MONITORING,
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
        "iteration": 0,
        "max_iterations": 5,
        "is_satisfied": False  # 用于 Diagnoser
    }
    
    # 执行总指挥 Graph
    # 注意：LangGraph 会自动处理 Sub-graph 的调用
    result = await sre_supervisor.ainvoke(initial_state)
    
    # 验证最终报告是否生成
    assert "final_report" in result
    assert "SRE 事件闭环报告" in result["final_report"]
    
    # 验证子 Agent 的成果是否汇总到了主 State
    assert "metrics_data" in result
    assert len(result["executed_actions"]) > 0
    print("\n[Supervisor Test] 自动调度闭环测试成功！🦞")
