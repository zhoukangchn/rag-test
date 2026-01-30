from typing import Any
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from src.app.agents.state import AgentState
from src.app.core.config import settings
from src.app.core.logging import logger
from src.app.core.prompts import (
    CHECK_PROMPT_DEFAULT,
    CHECK_PROMPT_REFLECTION,
    GENERATE_SYSTEM_PROMPT_BASE,
    GENERATE_SYSTEM_PROMPT_KNOWLEDGE,
    GENERATE_SYSTEM_PROMPT_REFLECTION,
    REFINE_PROMPT,
    REFLECT_PROMPT,
)
from src.app.services.knowledge import knowledge_service
from src.app.services.llm import llm

def get_last_content(messages: list) -> str:
    """获取最后一条消息的内容"""
    if not messages:
        return ""
    content = messages[-1].content
    return str(content) if content is not None else ""

async def searcher_agent(state: AgentState) -> dict[str, Any]:
    """
    Searcher Agent: 专门负责判断是否需要检索并执行检索。
    """
    messages = state["messages"]
    last_message = get_last_content(messages)
    reflection = state.get("reflection", "")
    
    # 1. 判断是否需要检索
    if reflection:
        check_prompt = CHECK_PROMPT_REFLECTION.format(
            reflection=reflection, last_message=last_message
        )
    else:
        check_prompt = CHECK_PROMPT_DEFAULT.format(last_message=last_message)

    response = await llm.ainvoke([HumanMessage(content=check_prompt)])
    content = str(response.content)
    need_knowledge = "YES" in content.upper()
    
    # 2. 执行检索（如果需要）
    context = state.get("knowledge_context", "")
    if need_knowledge:
        query = last_message
        if reflection:
            refine_prompt = REFINE_PROMPT.format(query=query, reflection=reflection)
            response = await llm.ainvoke([HumanMessage(content=refine_prompt)])
            query = str(response.content).strip()
            logger.info(f"[Searcher] 优化查询: {query}")
        
        results = await knowledge_service.search(query)
        if results:
            new_context = "\n\n".join(
                [f"[来源: {r.get('source', '未知')}]\n{r.get('content', '')}" for r in results]
            )
            context = f"{context}\n\n--- 新检索结果 ---\n{new_context}" if context else new_context

    logger.info(f"[Searcher] 检索完成，need_knowledge: {need_knowledge}")
    return {
        "need_knowledge": need_knowledge, 
        "knowledge_context": context,
        "next_agent": "writer"
    }

async def writer_agent(state: AgentState) -> dict[str, Any]:
    """
    Writer Agent: 专门负责根据上下文生成高质量回答。
    """
    messages = state["messages"]
    knowledge_context = state.get("knowledge_context", "")
    reflection = state.get("reflection", "")
    iteration = state.get("iteration", 0)

    system_prompt = GENERATE_SYSTEM_PROMPT_BASE

    if knowledge_context:
        system_prompt += GENERATE_SYSTEM_PROMPT_KNOWLEDGE.format(
            knowledge_context=knowledge_context
        )

    if reflection and iteration > 0:
        system_prompt += GENERATE_SYSTEM_PROMPT_REFLECTION.format(reflection=reflection)

    all_messages = [SystemMessage(content=system_prompt)] + messages
    response = await llm.ainvoke(all_messages)

    logger.info(f"[Writer] 生成回答 (第 {iteration + 1} 轮)")
    return {
        "current_answer": str(response.content), 
        "iteration": iteration + 1,
        "next_agent": "reviewer"
    }

async def reviewer_agent(state: AgentState) -> dict[str, Any]:
    """
    Reviewer Agent: 专门负责评估回答质量并决定下一步。
    """
    messages = state["messages"]
    question = get_last_content(messages)
    answer = state.get("current_answer", "")
    knowledge_context = state.get("knowledge_context", "")
    iteration = state.get("iteration", 0)

    # 最大迭代次数检查
    if iteration >= settings.max_iterations:
        logger.info("[Reviewer] 达到最大迭代次数，满意结束")
        return {"is_satisfied": True, "reflection": "", "next_agent": "end"}

    reflect_prompt = REFLECT_PROMPT.format(
        question=question,
        answer=answer,
        knowledge_context=knowledge_context[:1000] if knowledge_context else "无外部知识",
    )

    response = await llm.ainvoke([HumanMessage(content=reflect_prompt)])
    response_text = str(response.content).strip()

    if "SATISFIED" in response_text.upper() and "NEEDS_IMPROVEMENT" not in response_text.upper():
        logger.info("[Reviewer] 评估结果: 满意")
        return {"is_satisfied": True, "reflection": "", "next_agent": "end"}
    else:
        reflection = response_text.replace("NEEDS_IMPROVEMENT", "").strip()
        logger.info(f"[Reviewer] 评估结果: 不满意 - {reflection[:30]}...")
        return {
            "is_satisfied": False, 
            "reflection": reflection, 
            "next_agent": "searcher"
        }
