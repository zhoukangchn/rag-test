from typing import Any, Annotated, List, Optional
from langchain_core.messages import add_messages
from src.app.agents.state import AgentState

class WarroomState(AgentState):
    """作战室 Agent 扩展状态"""
    
    # 故障基本信息
    incident_id: str
    incident_severity: str  # P0, P1, P2, etc.
    incident_status: str    # open, investigating, resolved
    
    # 团队协作
    assigned_team: str      # SRE, DBA, Middleware, etc.
    warroom_channel_id: str # Slack/Discord channel ID
    
    # 调查进展
    investigation_plan: List[str]
    root_cause: Optional[str]
    
    # 时间轴记录 (Historian 维护)
    timeline_logs: List[dict]  # {"timestamp": "", "event": "", "source": ""}
    
    # RAG 增强
    similar_past_incidents: List[str]
