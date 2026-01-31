"""测试 Monitor Agent 工作流"""

import pytest
from src.sre.agents.monitor.graph import monitor_agent

@pytest.mark.asyncio
async def test_monitor_flow():
    """测试 Monitor Agent 完整运行一遍流程"""
    initial_state = {
        "incident_id": "TEST-INC-001",
        "resource_info": {"service": "web-api"},
        "metrics_data": {},
        "log_entries": [],
        "time_context": {},
        "max_age_minutes": 30
    }
    
    # 运行 Graph
    result = await monitor_agent.ainvoke(initial_state)
    
    # 验证数据是否被填充
    assert "metrics_data" in result
    assert result["metrics_data"]["cpu_usage"] > 0
    assert len(result["log_entries"]) > 0
    assert "recent_deployments" in result["time_context"]
    assert result["incident_id"] == "TEST-INC-001"
