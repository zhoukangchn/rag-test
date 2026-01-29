"""Agent 单元测试"""

import pytest
from app.agent import should_retrieve, retrieve_knowledge, generate_response, reflect_on_answer


class TestShouldRetrieve:
    """测试知识检索判断"""

    @pytest.mark.asyncio
    async def test_simple_greeting_no_retrieve(self, mock_llm):
        """简单问候不需要检索"""
        mock_llm.ainvoke.return_value.content = "NO"

        state = {
            "messages": [type("Msg", (), {"content": "你好"})()],
            "knowledge_context": "",
            "need_knowledge": False,
            "reflection": "",
        }

        result = await should_retrieve(state)
        assert result["need_knowledge"] is False

    @pytest.mark.asyncio
    async def test_factual_question_needs_retrieve(self, mock_llm):
        """事实性问题需要检索"""
        mock_llm.ainvoke.return_value.content = "YES"

        state = {
            "messages": [type("Msg", (), {"content": "2024年诺贝尔物理学奖是谁"})()],
            "knowledge_context": "",
            "need_knowledge": False,
            "reflection": "",
        }

        result = await should_retrieve(state)
        assert result["need_knowledge"] is True


class TestRetrieveKnowledge:
    """测试知识检索"""

    @pytest.mark.asyncio
    async def test_retrieve_when_needed(self, mock_tavily):
        """需要检索时调用 Tavily"""
        state = {
            "messages": [type("Msg", (), {"content": "测试问题"})()],
            "knowledge_context": "",
            "need_knowledge": True,
            "reflection": "",
        }

        # 需要设置 TAVILY_API_KEY
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.knowledge.TAVILY_API_KEY", "test-key")
            result = await retrieve_knowledge(state)

        assert "knowledge_context" in result

    @pytest.mark.asyncio
    async def test_skip_when_not_needed(self):
        """不需要检索时跳过"""
        state = {
            "messages": [type("Msg", (), {"content": "你好"})()],
            "knowledge_context": "",
            "need_knowledge": False,
            "reflection": "",
        }

        result = await retrieve_knowledge(state)
        assert result["knowledge_context"] == ""
