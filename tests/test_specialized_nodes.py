from unittest.mock import AsyncMock, patch
import pytest
from src.app.agents.specialized_nodes import searcher_agent, writer_agent, reviewer_agent
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.asyncio
async def test_searcher_agent_no_knowledge(mock_llm):
    """测试 Searcher Agent: 不需要检索的情况"""
    state = {
        "messages": [HumanMessage(content="你好")],
        "knowledge_context": "",
        "iteration": 0
    }
    # Mock LLM 返回 NO
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="NO"))
    
    result = await searcher_agent(state)
    assert result["need_knowledge"] is False
    assert result["next_agent"] == "writer"

@pytest.mark.asyncio
async def test_writer_agent_basic(mock_llm):
    """测试 Writer Agent: 基础生成"""
    state = {
        "messages": [HumanMessage(content="你是谁")],
        "knowledge_context": "我是龙虾",
        "iteration": 0
    }
    # 确保 mock_llm 的 ainvoke 返回我们期望的内容
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="我是一只龙虾助手"))
    
    result = await writer_agent(state)
    assert "我是一只龙虾" in result["current_answer"]
    assert result["iteration"] == 1
    assert result["next_agent"] == "reviewer"

@pytest.mark.asyncio
async def test_reviewer_agent_satisfied(mock_llm):
    """测试 Reviewer Agent: 满意的情况"""
    state = {
        "messages": [HumanMessage(content="1+1=?")],
        "current_answer": "1+1=2",
        "knowledge_context": "",
        "iteration": 1
    }
    mock_llm.ainvoke = AsyncMock(return_value=AIMessage(content="SATISFIED"))
    
    result = await reviewer_agent(state)
    assert result["is_satisfied"] is True
    assert result["next_agent"] == "end"
