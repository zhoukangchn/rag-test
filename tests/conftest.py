"""测试配置"""

import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture
def mock_llm():
    """Mock DeepSeek LLM"""
    with patch("app.agent.llm") as mock:
        mock.ainvoke = AsyncMock(return_value=AsyncMock(content="NO"))
        yield mock


@pytest.fixture
def mock_tavily():
    """Mock Tavily 搜索"""
    with patch("app.knowledge.AsyncTavilyClient") as mock:
        client = AsyncMock()
        client.search = AsyncMock(return_value={
            "answer": "这是测试答案",
            "results": [
                {"content": "测试内容", "url": "https://example.com", "score": 0.9}
            ]
        })
        mock.return_value = client
        yield mock
