import pytest
from app.engine import MockLLMExecutor

@pytest.mark.asyncio
async def test_mock_llm_executor():
    executor = MockLLMExecutor()
    result = await executor.execute_agent({"name": "TestAgent"}, {"user_query": "Hello"})
    
    assert "Mocked response" in result["response"]
    assert result["cost"]["tokens_in"] == 150
    assert result["cost"]["tokens_out"] == 45
    assert result["cost"]["cost_usd"] == 0.002
