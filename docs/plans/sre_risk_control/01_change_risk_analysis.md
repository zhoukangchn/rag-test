# 🛡️ 基于华为云变更场景的 SRE Agent 风控体系深度分析

## 1. 核心案例定义：云服务控制面配置变更

为了让分析具象化，我们锁定一个华为云最高频且高危的场景：

**案例：修改某核心服务（如 ECS 创建服务）的全局流控（Rate Limit）配置。**

- **背景**：为了应对大促，SRE 需要将 API 的限流阈值从 10,000 QPS 调整为 50,000 QPS。
- **潜在风险**：配置格式错误（YAML 缩进）、下发范围错误（灰度变成了全网）、配置生效导致下游数据库被打挂。

---

## 2. 基础设施映射：Agent 的"感官"与"大脑"

要构建 Agent，首先要盘点我们手里有什么（Input）。

| 维度 | 具体内容 (华为云场景) | Agent 如何使用 |
| :--- | :--- | :--- |
| **数据 (Data)** | **CMDB 拓扑**：服务依赖关系、部署架构（Region/AZ/Cell）。<br>**Metrics**：接口成功率、时延、CPU、连接数。<br>**Logs**：错误日志堆栈、配置变更日志。<br>**Tracing**：全链路调用链。 | **感知**：Agent 实时读取 Metrics 判断变更是否"流血"；读取 CMDB 计算"爆炸半径"。 |
| **知识 (Knowledge)** | **变更红线**：三板斧（可灰度、可监控、可回滚）、封网时间窗口。<br>**历史故障库**：过去类似变更导致的事故复盘报告（Post-mortem）。<br>**专家经验**：比如"修改 JVM 参数必须重启"。 | **推理**：Agent 拿当前变更去匹配历史故障，计算风险概率；利用红线规则进行"一票否决"。 |
| **工具 (Tools)** | **流水线 (CloudPipeline)**：执行变更动作。<br>**监控系统 (CloudEye)**：获取数据。<br>**配置中心 (CSE/Nacos)**：下发配置。<br>**混沌工程平台**：变更前验证。 | **执行**：Agent 调用监控查询接口；调用流水线暂停/回滚接口。 |

---

## 3. Agent 核心能力构建：风控分析与决策逻辑

我们将 Agent 的介入分为三个阶段：**变更前（Pre-Check）、变更中（In-Process）、变更后（Post-Check）**。

### 3.1 第一阶段：变更前风险分析 (Pre-Check Agent)

**目标**：把烂变更拦截在发布之前。

- **输入**：变更工单（RFC）、变更内容（Diff）、CMDB。
- **分析逻辑**：

#### 3.1.1 语义与格式检查
- *Agent 动作*：如果是 JSON/YAML 配置，校验语法合法性；如果是 SQL，校验是否有 `DROP TABLE` 或全表扫描风险。

#### 3.1.2 爆炸半径计算 (Blast Radius Calculation)
- *Agent 动作*：读取变更的 Scope（范围）。
- *判定*：
  - 如果 Scope = Global（全网），直接触发**高危告警**，要求必须有 VP 级审批。
  - 如果 Scope = One AZ（单可用区），符合灰度规范，风险分降低。

#### 3.1.3 冲突检测
- *Agent 动作*：查询 CMDB 和变更日历。
- *判定*：检测当前服务是否有正在进行的变更？其下游依赖（如 RDS）是否正在变更？如果有，提示**变更撞车风险**。

#### 3.1.4 历史故障关联
- *Agent 动作*：RAG 检索故障知识库，Query = "配置变更 AND 流控 AND 数据库"。
- *输出*："警告：半年前类似变更导致了 RDS CPU 飙升，建议预先检查数据库容量。"

### 3.2 第二阶段：变更中灰度决策 (Gray Release Guardian)

**目标**：在故障扩散前自动止损。

- **输入**：实时监控数据（秒级）、灰度策略。
- **场景推演**：配置下发到了 **Region A - AZ 1 (灰度区)**。

#### 决策逻辑 (Decision Model)

1. **静默期检测**：配置下发后，Agent 强制锁定 5 分钟（观察期）。

2. **多维健康度对比 (Canary Analysis)**：
   - *Baseline*：未变更的 AZ 2 成功率 99.99%。
   - *Canary*：变更的 AZ 1 成功率 98.5%。
   - *Agent 判定*：`Canary < Baseline - Threshold`，判定为**异常**。

3. **关键错误捕捉**：
   - Agent 实时 Grep 日志，发现出现了 `ClassCastException` 或 `YAML parsing error`。
   - *决策*：**立即阻断**。

### 3.3 第三阶段：决策与止损 (The Executor)

**目标**：机器决策，唯快不破。

#### 决策树

| 触发条件 | 动作 |
| :--- | :--- |
| **红线触发**：错误率 > 0.1% 或 核心 API 5xx > 10 个/秒 | **Action: 自动回滚 (Auto-Rollback)** |
| **黄线触发**：时延上涨 20%，但无错误 | **Action: 暂停变更 (Suspend)，呼叫 SRE 人工介入** |
| **绿线通过**：各项指标正常 | **Action: 自动推进到下一个灰度批次 (Promote to Next Batch)** |

---

## 4. 典型变更场景分析

### 4.1 配置变更 (Configuration Change)

- **场景**：开发把数据库连接超时从 `30s` 改成了 `30ms`。
- **现象**：服务启动正常，但流量一来，所有 DB 请求全部报错（Connection Timeout）。
- **Agent 考验**：能否识别是配置导致的错误率飙升？能否自动执行回滚？

### 4.2 代码发布 (Code Deployment)

- **场景**：新上线的代码里有个死循环或内存泄漏。
- **现象**：
  - *死循环*：CPU 飙升到 100%，请求响应极慢（Latency High）。
  - *内存泄漏*：内存缓慢上涨，几小时后 OOM 重启。
- **Agent 考验**：
  - Monitor 能否发现 CPU/Memory 异常趋势？
  - Diagnoser 能否关联到最近的一次 Deploy 事件？

### 4.3 IAM 权限变更 (IAM Policy Change)

- **场景**：运维人员为了安全，收缩了某个服务账号的 OBS 访问权限。
- **故障**：收缩过度，导致服务无法读取存放在 OBS 上的镜像或日志，服务启动失败或功能受损。
- **穿刺点**：修改 IAM Policy，Deny 掉关键资源的 Access。
- **Agent 考验**：Monitor 发现 `403 Forbidden` 错误激增，Diagnoser 能否建议"检查 IAM 权限变更"？

### 4.4 网络安全组/ACL 变更 (Security Group/ACL Change)

- **场景**：为了合规，修改了 ELB 或 VPC 的安全组规则。
- **故障**：误封了数据库端口（3306）或内部通信端口。
- **穿刺点**：模拟安全组规则变更，阻断特定 IP 段的访问。
- **Agent 考验**：能否区分是"服务挂了"还是"网络不通"？

### 4.5 灰度发布"带毒" (Canary Release Poisoning)

- **场景**：某个云服务（比如 ECS 控制面）发版。按照规范，先在"灰度 AZ"发布。
- **故障**：新版本包含一个逻辑 Bug，导致该 AZ 内的 CreateInstance 接口成功率跌零。
- **穿刺点**：模拟灰度发布过程，只让 5% 的流量（或特定租户）命中错误逻辑。
- **Agent 考验**：
  - **Monitor**：能否发现**分维度**（按 Region/AZ/Version）的成功率下跌？
  - **Diagnoser**：能否迅速定位到"是灰度版本的问题"？
  - **Executor**：能否自动触发**切流**或**停止发布**？

---

## 5. 架构落地：RAG + Function Calling

要实现上述分析，需要构建如下的 Agent 架构：

### 5.1 Knowledge Base (RAG)

存入以下知识：
- 华为云《SRE 变更红线规范》
- 《历史故障案例库》
- 《服务依赖拓扑图》

### 5.2 ToolKit (Function Calling)

```python
def query_metrics(service: str, region: str, metric_name: str) -> dict:
    """查询监控指标"""
    pass

def check_change_calendar(service_id: str) -> dict:
    """查询封网日历和变更冲突"""
    pass

def simulate_blast_radius(change_scope: str) -> dict:
    """计算变更影响面"""
    pass

def execute_rollback(change_id: str) -> bool:
    """执行回滚操作"""
    pass
```

### 5.3 Prompt Engineering (Role Play)

```
System Prompt:
你是一名华为云 SRE 变更守门员。你的职责是基于数据极其严苛地审查变更。
宁可错杀（回滚），不可放过（带病上线）。
```

---

## 6. Agent 对变更流程的重构

引入 Agent 后，变更流程将从 **"人治"** 转变为 **"人机协同"**：

### 传统流程
提单 -> 人眼看 Diff -> 人点发布 -> 人盯着监控 -> 出事了人去回滚（通常慢半拍）

### Agent 辅助流程
- **提单时**：Agent 直接告诉你"这个配置大概率会挂，因为历史上……"
- **发布时**：Agent 接管灰度，它盯着几百个指标，人只需要喝咖啡。
- **出事时**：在你收到短信之前，Agent 已经把服务回滚完了。

---

## 7. 下一步行动计划

1. **实现 Pre-Check Agent**（变更前风控）- 风险最小，收益最明显
2. **构建知识库**：整理华为云变更规范和历史故障案例
3. **定义 Tool 接口**：对接 CloudEye、CMDB 等系统
4. **穿刺验证**：用模拟故障测试 Agent 的判断准确性
