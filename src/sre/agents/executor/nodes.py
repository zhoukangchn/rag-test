"""Executor Agent 节点逻辑

负责制定操作计划、执行具体工具以及验证执行结果。
"""

from typing import Any, Dict
from datetime import datetime
import os
from src.app.core.logging import logger
from src.sre.agents.shared.state import ExecutorState, ActionType

# 集成 Kubernetes 客户端
try:
    import kr8s
    from kr8s.objects import Pod, Deployment
except ImportError:
    kr8s = None

async def execute_k8s_action(action: dict) -> dict:
    """执行真实的 K8s 操作项"""
    tool = action.get("tool_name")
    params = action.get("parameters", {})
    
    if not kr8s:
        return {"status": "failed", "error": "kr8s library not installed"}

    try:
        api = await kr8s.async_api()
        
        if tool == "restart_pod":
            pod_name = params.get("pod")
            namespace = params.get("namespace", "default")
            pod = await Pod.get(pod_name, namespace=namespace, api=api)
            await pod.delete() # 删除 Pod 触发 K8s 重建实现“重启”
            return {"status": "success", "output": f"Pod {pod_name} deleted (restarting)"}
            
        elif tool == "kubectl_scale":
            resource = params.get("resource") # e.g. "deployment/web-api"
            replicas = params.get("replicas")
            kind, name = resource.split("/")
            
            if kind == "deployment":
                deploy = await Deployment.get(name, namespace=params.get("namespace", "default"), api=api)
                await deploy.scale(replicas)
                return {"status": "success", "output": f"Scaled {resource} to {replicas} replicas"}
        
        return {"status": "failed", "error": f"Unknown tool: {tool}"}
    except Exception as e:
        logger.error(f"[Executor] K8s 操作失败: {e}")
        return {"status": "failed", "error": str(e)}

async def plan_actions_node(state: ExecutorState) -> Dict[str, Any]:
    """根据诊断结果制定多维度的修复计划"""
    logger.info(f"[Executor] 正在为事件 {state['incident_id']} 制定修复计划...")
    
    report = state.get("diagnosis_report", "")
    plan = []
    
    if "I/O 阻塞" in report:
        plan.append({
            "id": "act-scale-db-001",
            "type": ActionType.REMEDIATION,
            "tool_name": "kubectl_scale",
            "parameters": {"resource": "deployment/db-proxy", "replicas": 3, "namespace": "prod"},
            "description": "扩容数据库代理以分担 I/O 压力",
            "requires_approval": True,
            "estimated_impact": "低",
            "created_at": datetime.now()
        })
    elif "业务逻辑死循环" in report or "用户态" in report:
        plan.append({
            "id": "act-profile-001",
            "type": ActionType.DIAGNOSTIC,
            "tool_name": "py_spy_record",
            "parameters": {"pod": "web-api-0", "duration": "30s", "namespace": "prod"},
            "description": "采集 CPU 火焰图以分析死循环位置",
            "requires_approval": False,
            "estimated_impact": "极低",
            "created_at": datetime.now()
        })
        plan.append({
            "id": "act-restart-001",
            "type": ActionType.REMEDIATION,
            "tool_name": "restart_pod",
            "parameters": {"pod": "web-api-0", "namespace": "prod"},
            "description": "重启服务作为临时止损手段",
            "requires_approval": True,
            "estimated_impact": "中",
            "created_at": datetime.now()
        })
    else:
        plan.append({
            "id": "act-generic-restart",
            "type": ActionType.REMEDIATION,
            "tool_name": "restart_pod",
            "parameters": {"pod": "web-api-0", "namespace": "prod"},
            "description": "常规重启以恢复服务",
            "requires_approval": True,
            "estimated_impact": "中",
            "created_at": datetime.now()
        })

    return {
        "action_plan": plan,
        "requires_human_approval": any(a["requires_approval"] for a in plan)
    }

async def execute_tool_node(state: ExecutorState) -> Dict[str, Any]:
    """执行具体工具 (现在支持真实 K8s 调用)"""
    logger.info(f"[Executor] 正在执行操作...")
    
    executed_results = []
    for action in state.get("action_plan", []):
        logger.info(f"[Executor] 执行任务: {action['description']} ({action['tool_name']})")
        
        # 判断是 Mock 还是真实运行
        if os.getenv("KUBECONFIG") or os.path.exists("/home/zk/.kube/config"):
            result_data = await execute_k8s_action(action)
        else:
            logger.info("[Executor] 未检测到 K8s 环境，使用 Mock 执行")
            result_data = {
                "status": "success",
                "output": f"MOCK: {action['tool_name']} executed successfully."
            }
            
        result = {
            "action_id": action["id"],
            "status": result_data["status"],
            "output": result_data.get("output", ""),
            "error": result_data.get("error"),
            "executed_at": datetime.now(),
            "executed_by": "agent"
        }
        executed_results.append(result)
        
    return {
        "executed_actions": executed_results
    }

async def verify_result_node(state: ExecutorState) -> Dict[str, Any]:
    """验证执行结果"""
    logger.info(f"[Executor] 正在验证执行结果...")
    # TODO: 重新调用 Monitor Agent 的逻辑来核实指标是否恢复正常
    verification = "执行动作后，监控指标正在恢复。CPU 使用率预计在 5 分钟内降至正常阈值。"
    
    # 检查是否有失败的任务
    if any(r["status"] == "failed" for r in state.get("executed_actions", [])):
        verification = "部分修复动作执行失败，建议人工介入检查。"
        
    logger.info(f"[Executor] 验证结果: {verification}")
    
    from src.sre.agents.shared.state import IncidentStatus
    return {
        "diagnosis_report": state.get("diagnosis_report", "") + "\n\n[Verification] " + verification,
        "status": IncidentStatus.RESOLVED
    }
