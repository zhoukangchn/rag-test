"""Diagnoser Agent 节点逻辑

负责查询知识库、分析指标与日志的关联性，并生成根因假设。
"""

from typing import Any, Dict
import os
import httpx
from src.app.core.logging import logger
from src.sre.agents.shared.state import DiagnoserState

async def query_knowledge_node(state: DiagnoserState) -> Dict[str, Any]:
    """通过外部诊断服务获取分析建议"""
    logger.info(f"[Diagnoser] 正在为事件 {state['incident_id']} 调用外部诊断服务...")
    
    service_url = os.getenv("DIAGNOSIS_SERVICE_URL")
    context = ""

    if service_url:
        try:
            async with httpx.AsyncClient() as client:
                # 将当前的监控数据发给外部诊断服务
                payload = {
                    "incident_id": state["incident_id"],
                    "metrics": state.get("metrics_data"),
                    "logs": state.get("log_entries")
                }
                response = await client.post(f"{service_url}/analyze", json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    context = data.get("suggestion", "外部服务未提供具体建议")
                    logger.info(f"[Diagnoser] 成功获取外部诊断建议: {context[:50]}...")
                else:
                    logger.error(f"[Diagnoser] 外部服务返回异常: {response.status_code}")
        except Exception as e:
            logger.error(f"[Diagnoser] 调用外部诊断服务失败: {e}")

    # 如果没有配置 URL 或调用失败，使用 Mock 数据
    if not context:
        logger.info("[Diagnoser] 使用 Mock 诊断建议 (外部服务未配置)")
        
        metrics = state.get("metrics_data", {})
        cpu_usage = metrics.get("cpu_usage", 0)
        cpu_iowait = metrics.get("cpu_iowait", 0)
        
        if cpu_usage > 0.8:
            if cpu_iowait > 0.15:
                context = "根据 Mock 专家库建议：检测到极高的 I/O 等待。这通常意味着数据库磁盘性能达到瓶颈或存在大量未索引的全表扫描。"
            else:
                context = "根据 Mock 专家库建议：用户态 CPU 占用过高。建议检查最近的部署记录中是否存在算法复杂度过高或死循环的代码改动。"
        else:
            context = "根据 Mock 专家库建议：当前资源指标尚在可控范围，建议观察连接数变化。"
    
    return {"knowledge_context": context}

async def analyze_correlation_node(state: DiagnoserState) -> Dict[str, Any]:
    """分析指标与日志的关联性，提供更深度的 CPU 诊断"""
    logger.info(f"[Diagnoser] 正在分析指标与日志的关联性...")
    
    metrics = state.get("metrics_data", {})
    cpu_usage = metrics.get("cpu_usage", 0)
    cpu_iowait = metrics.get("cpu_iowait", 0)
    cpu_system = metrics.get("cpu_system", 0)
    
    analysis = f"指标显示总 CPU 使用率达 {cpu_usage*100:.1f}%。"
    
    if cpu_usage > 0.8:
        if cpu_iowait > 0.2:
            analysis += " 发现显著的 I/O 等待，可能存在磁盘瓶颈或数据库慢查询导致同步阻塞。"
        elif cpu_system > 0.3:
            analysis += " 内核态 CPU 占比异常，可能存在频繁的中断、上下文切换或系统调用瓶颈。"
        else:
            analysis += " CPU 主要消耗在用户态，推测为业务逻辑死循环、复杂的计算任务或突发高流量。"
            
    return {"reflection": analysis}

async def generate_hypothesis_node(state: DiagnoserState) -> Dict[str, Any]:
    """根据分析结果生成更精确的根因假设"""
    logger.info(f"[Diagnoser] 正在生成根因假设...")
    reflection = state.get("reflection", "")
    
    hypotheses = []
    if "I/O 等待" in reflection:
        hypotheses.append({"hypothesis": "磁盘或数据库 I/O 阻塞", "confidence": 0.9, "evidence": ["High cpu_iowait"]})
    elif "内核态" in reflection:
        hypotheses.append({"hypothesis": "系统资源争抢或内核瓶颈", "confidence": 0.8, "evidence": ["High cpu_system"]})
    elif "用户态" in reflection:
        hypotheses.append({"hypothesis": "业务逻辑死循环或算力不足", "confidence": 0.85, "evidence": ["High user-space CPU consumption"]})
    else:
        # 兜底
        hypotheses = [
            {"hypothesis": "数据库连接池配置过小", "confidence": 0.8, "evidence": ["Connection pool exhausted logs"]},
            {"hypothesis": "下游服务响应慢导致连接积压", "confidence": 0.5, "evidence": ["Increased request latency"]}
        ]
    
    from src.sre.agents.shared.state import IncidentStatus
    return {
        "current_hypotheses": hypotheses,
        "is_satisfied": True,
        "status": IncidentStatus.EXECUTING
    }
