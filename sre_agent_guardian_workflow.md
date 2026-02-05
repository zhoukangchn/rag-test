# SRE Agent Guardian Workflow: The Defense Architecture

**Created**: 2026-02-05
**Context**: Best practices for preventing "death spirals" in automated deployments.

## 1. The Core Philosophy (核心理念)
The SRE Agent is not just an executor; it is a **Guardian**. It must possess the authority to **reject unsafe user commands** and **enforce system stability** over deployment velocity.

## 2. The Guardian Workflow (防御流程图)

```mermaid
graph TD
    User((User Command)) --> Agent[SRE Agent]
    
    %% Phase 1: Pre-flight Check
    subgraph Phase 1: Pre-flight Check
        Agent -->|Parse Intent| Intent{Intent?}
        Intent -->|Deploy/Change| CheckState[Check System State]
        Intent -->|Rollback/Fix| Emergency[Emergency Lane]
        
        CheckState -->|Check Last Batch| LastBatch{Last Batch Status?}
        LastBatch -->|Failed/Unknown| Block[🚫 Circuit Breaker Block]
        LastBatch -->|Success| CheckDrift{Config Drift?}
        
        CheckDrift -->|Drift Detected| WarnDrift[⚠️ Warning: Drift Detected]
        CheckDrift -->|Clean| Ready[✅ Ready to Deploy]
    end

    %% Phase 2: Execution & Monitoring
    subgraph Phase 2: Execution & Monitoring
        Ready --> Exec[Execute Batch N]
        Exec --> Monitor[Real-time Monitoring]
        
        Monitor -->|Healthy| Success[🎉 Success]
        Monitor -->|Error/Timeout| Failure[💥 Failure]
    end

    %% Phase 3: Incident Response
    subgraph Phase 3: Incident Response
        Failure --> AutoLock[🔒 Global Lock Active\n(Next Batch Blocked)]
        AutoLock --> Suggest[💡 Suggestion: Rollback]
        
        User -->|Attempts Force Continue| Intercept{🛡️ Agent Intercept}
        Intercept -->|REJECT| Block
        
        User -->|Confirms Rollback| Rollback[Execute Rollback]
        
        Rollback -->|Lock Conflict| ForceUnlock[🔨 Auto-Kill Zombie Tasks]
        ForceUnlock --> RetryRollback[Retry Rollback]
        RetryRollback -->|Success| Restore[🔄 Config Restored]
        Restore --> Unlock[🔓 Release Global Lock]
    end

    %% Styles
    classDef danger fill:#f96,stroke:#333,stroke-width:2px;
    classDef safe fill:#9f9,stroke:#333,stroke-width:2px;
    classDef guard fill:#ff9,stroke:#f66,stroke-width:4px;
    
    class Block,Failure,AutoLock danger;
    class Success,Restore,Ready safe;
    class Intercept,ForceUnlock guard;
```

## 3. Implementation Logic (实现逻辑)

### A. Pre-flight Circuit Breaker (起飞前熔断)
Before executing any write operation, the Agent must query the global state:
```python
if last_operation.status == "FAILED" and current_intent != "ROLLBACK":
    return REJECT("System is in FAILED state. Rollback required first.")
```

### B. Intent Interception (意图拦截)
If a user tries to "Skip Error" or "Force Continue" after a failure:
1.  **Pause**: Do not execute immediately.
2.  **Analyze**: Calculate the Blast Radius (e.g., "If batch 2 fails, 50% of traffic is lost").
3.  **Challenge**: Require explicit confirmation of risks (e.g., "Type 'CONFIRM_RISK' to proceed").

### C. Auto-Cleanup for Rollbacks (回滚自动清障)
Rollbacks must succeed. If a rollback is blocked by a lock or a zombie task:
1.  **Identify**: Find the blocking resource (e.g., a timed-out canary job).
2.  **Kill**: Terminate the blocking resource (Force Release).
3.  **Proceed**: Execute the restoration of the previous configuration.

## 4. Universality (通用性)
This workflow is platform-agnostic:
*   **Kubernetes**: "Locks" are Deployment status or Leases. "Drift" is Diff against GitOps repo.
*   **Database**: "Locks" are Metadata locks. "Drift" is Schema mismatch.
*   **Legacy**: "Locks" are PID files. "Drift" is Config file hash mismatch.

The principle remains: **Never build on top of a broken foundation.**
