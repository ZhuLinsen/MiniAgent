# TODO: MiniAgent HTTP Line-Based 控制面设计

## 背景

当前 `miniagent` 只能通过本地交互式 REPL 使用：

- 人类在终端里输入 `you: ...`
- CLI 在当前进程里驱动 `MiniAgent`
- 工具事件和最终回复只输出到当前终端

这对人类使用足够简单，但对“机器人驱动 MiniAgent”不够友好。

已经确认的实际问题：

- 外部机器人可以新起一个 PTY，会话内驱动 `miniagent`
- 但无法可靠附着到“用户已经打开的那个终端窗口”
- 也没有稳定 API 可以发送消息、读取工具事件、拿到最终回复

所以需要一个**可选的、极简的、默认关闭的 HTTP 控制面**。

核心目标不是把 MiniAgent 变成 Web 服务框架，而是给 CLI 暴露一个**最小远程操控接口**，让机器人/测试器/自动化脚本可以和当前 Agent 进程交互。

## 设计目标

1. 保持 MiniAgent 极简
   - 不引入 FastAPI / Flask / aiohttp 这类重依赖
   - 优先使用标准库 `http.server` + `threading` + `queue`

2. 明确是 CLI 的可选能力
   - 默认关闭
   - 只有显式传入 CLI 参数才启动控制面

3. 保持“过程透明”
   - HTTP 客户端不仅能拿最终回答
   - 还能看到工具开始、工具结束、流式 token、错误等事件

4. 协议简单到可以 `curl` 调试
   - 请求 JSON
   - 响应优先使用 line-based 流格式
   - 首选 `application/x-ndjson`

5. 和现有 REPL 共存
   - 本地终端依旧能用
   - HTTP 控制面是附加输入输出通道，不替代 CLI

## 非目标

- 不做多租户 Agent 服务
- 不做用户鉴权系统
- 不做 Web UI
- 不做任务队列/数据库
- 不做多个并发对话的复杂调度
- 不保证一个 Agent 进程同时安全处理多个活跃请求

## 用户侧体验

新增一个 CLI 选项：

```bash
miniagent --control-http 127.0.0.1:8765
```

或：

```bash
python -m miniagent --config examples/langfuse_security_pack/profile.json --control-http 8765
```

约定：

- `--control-http 8765` 等价于监听 `127.0.0.1:8765`
- `--control-http 0.0.0.0:8765` 允许局域网访问，但不推荐作为默认用法

建议通过环境变量提供一个简单 token：

```bash
export MINIAGENT_CONTROL_TOKEN="some-random-token"
```

请求时带：

```bash
Authorization: Bearer some-random-token
```

如果未设置 `MINIAGENT_CONTROL_TOKEN`：

- 默认只允许 `127.0.0.1` / `::1`
- 且在启动时打印明显 warning

## 为什么选 HTTP + NDJSON

相比“直接暴露 socket 自定义协议”，HTTP 更容易接入：

- `curl`
- shell 脚本
- 浏览器插件
- 测试脚本
- 外部机器人

相比 WebSocket：

- 标准库实现 HTTP 更简单
- 只做单向事件流时，chunked + NDJSON 更容易调试
- 对 MiniAgent 这种单请求串行工作流更贴切

相比 SSE：

- SSE 更偏浏览器
- NDJSON 对 CLI / Python / shell 更通用
- 事件结构仍然可以保持 JSON

## 协议草案

### 1. 健康检查

```http
GET /healthz
```

返回：

```json
{"ok": true}
```

### 2. 当前会话信息

```http
GET /v1/session
```

返回示例：

```json
{
  "ok": true,
  "model": "DeepSeek-R1",
  "profile": "langfuse_security_audit",
  "skill": "langfuse_security_analyst",
  "tools": [
    "read",
    "grep",
    "glob",
    "langfuse_fetch_logs",
    "tencent_cls_fetch_logs"
  ],
  "history_length": 6,
  "streaming_default": true,
  "control_http": "127.0.0.1:8765"
}
```

### 3. 发送一条用户消息

```http
POST /v1/message
Content-Type: application/json
Authorization: Bearer <token>
```

请求体：

```json
{
  "text": "compute 2+42",
  "stream": true,
  "mode": "text",
  "request_id": "req-001"
}
```

字段说明：

- `text`: 必填，等价于 REPL 中用户输入的一行文本
- `stream`: 是否流式返回事件，默认 `true`
- `mode`: 可选，`text` 或 `native`
- `request_id`: 可选，由客户端传入便于串联日志

### 4. 流式返回格式

当 `stream=true` 时，响应头：

```http
Content-Type: application/x-ndjson
Transfer-Encoding: chunked
```

每一行一个 JSON event：

```json
{"type":"request.accepted","request_id":"req-001"}
{"type":"assistant.thinking","iteration":1}
{"type":"tool.start","name":"calculator","arguments":{"expression":"2 + 42"}}
{"type":"tool.end","name":"calculator","result":{"expression":"2 + 42","result":44}}
{"type":"assistant.delta","delta":"The result is "}
{"type":"assistant.delta","delta":"44."}
{"type":"assistant.final","content":"The result is 44."}
{"type":"request.complete","ok":true}
```

### 5. 非流式返回格式

当 `stream=false` 时，等待一次请求结束，返回：

```json
{
  "ok": true,
  "request_id": "req-001",
  "content": "The result is 44.",
  "events": [
    {"type":"tool.start","name":"calculator","arguments":{"expression":"2 + 42"}},
    {"type":"tool.end","name":"calculator","result":{"expression":"2 + 42","result":44}}
  ]
}
```

### 6. 查询历史

```http
GET /v1/history?limit=20
```

返回：

```json
{
  "ok": true,
  "messages": [
    {"role":"user","content":"compute 2+42"},
    {"role":"assistant","content":"The result is 44."}
  ]
}
```

### 7. 中断当前请求

```http
POST /v1/interrupt
```

第一版可以先只返回：

```json
{"ok": false, "error": "not_implemented_yet"}
```

原因：

- 当前 `MiniAgent` 运行循环没有真正的 cooperative cancellation 机制
- 如果强行中断，很容易把状态搞乱

这个接口应该先占位，后续再实现

## 内部事件模型

为了复用 CLI 现有输出逻辑，建议先抽一个统一事件结构：

```python
{
  "type": "tool.start",
  "ts": 1710000000.123,
  "payload": {...}
}
```

建议最小事件集：

- `request.accepted`
- `assistant.thinking`
- `assistant.delta`
- `assistant.final`
- `tool.start`
- `tool.end`
- `warning`
- `error`
- `request.complete`

这些事件既可以：

- 打到本地 CLI
- 也可以送到 HTTP 流

## 代码结构建议

不建议把 HTTP 逻辑塞进 `cli.py` 主循环里。

建议新增一个小模块：

```text
miniagent/
├── control_server.py   # 标准库 HTTP 控制面
└── cli.py              # 只负责参数解析与启动
```

### `control_server.py` 建议职责

- 解析监听地址
- 启动 `ThreadingHTTPServer`
- 做简单 token 校验
- 把 HTTP 请求转成“给 agent 发一条消息”
- 把 agent 运行事件转成 NDJSON

### `cli.py` 建议职责

- 新增 `--control-http`
- 启动时如果传入该参数，则初始化控制服务
- REPL 输入和 HTTP 输入共用一套会话状态

## 会话与并发模型

第一版必须刻意简单。

### 单进程单会话

一个 `miniagent` 进程只维护一个对话历史：

- REPL 输入共享这份历史
- HTTP 输入也共享这份历史

这符合现有 CLI 心智模型，不引入多 session 抽象。

### 单活跃请求

同一时刻只允许一个请求运行。

如果已有请求在执行中，新的 `/v1/message` 直接返回：

```json
{
  "ok": false,
  "error": "agent_busy"
}
```

原因：

- 当前 `history`、`memory.push()`、`console.status()` 都不是并发安全设计
- 强行支持并发会让这个项目迅速复杂化

## 与当前 CLI 的衔接方案

当前 `cli.py` 里已经有现成的几个回调：

- `_tool_callback`
- `_status_callback`
- `_stream_callback`

但它们偏向“直接打印到终端”。

建议重构方向：

1. 先定义一个 `EventSink` 概念
   - `emit(event: dict) -> None`

2. CLI 输出层做一个 sink
   - 把事件渲染成 Rich 文本

3. HTTP 输出层做一个 sink
   - 把事件写成 NDJSON 行

4. Agent 执行时接受一个组合 sink
   - 同时喂给 CLI 和 HTTP

这样可以避免把终端打印逻辑硬编码进 agent 回调。

## HTTP 安全边界

默认安全策略：

1. 默认只监听 loopback
   - `127.0.0.1`
   - `::1`

2. 若监听非 loopback 地址
   - 必须显式设置 `MINIAGENT_CONTROL_TOKEN`
   - 否则直接拒绝启动

3. 返回内容不做额外脱敏
   - HTTP 控制面只是传递当前 CLI 已有能力
   - 敏感信息治理仍应在工具层完成

4. 不实现跨域支持
   - 第一版主要面向机器人/脚本，不面向浏览器前端

## 错误语义

统一 JSON 错误格式：

```json
{
  "ok": false,
  "error": "invalid_request",
  "message": "field 'text' is required"
}
```

建议错误码：

- `invalid_request`
- `unauthorized`
- `forbidden`
- `not_found`
- `method_not_allowed`
- `agent_busy`
- `internal_error`
- `not_implemented_yet`

## 兼容性要求

1. 不开启 `--control-http` 时，现有 CLI 行为完全不变
2. `python -m miniagent` 和 `miniagent` 命令行为一致
3. 现有 tool callback、streaming、native/text mode 都能继续工作
4. 不能要求用户安装额外 Web 框架

## 建议的 CLI 选项定义

第一版只新增一个显式参数：

```bash
--control-http [HOST:]PORT
```

示例：

```bash
miniagent --control-http 8765
miniagent --control-http 127.0.0.1:8765
miniagent --control-http 0.0.0.0:8765
```

解析规则：

- 纯数字：视为 `127.0.0.1:<port>`
- `host:port`：按原样解析

认证、超时等先通过环境变量控制，避免第一版 CLI 参数膨胀：

- `MINIAGENT_CONTROL_TOKEN`
- `MINIAGENT_CONTROL_READ_TIMEOUT`
- `MINIAGENT_CONTROL_WRITE_TIMEOUT`

## 实现分阶段 TODO

### Phase 1: 文档与接口骨架

- [ ] 在 `cli.py` 中新增 `--control-http` 参数
- [ ] 新增 `miniagent/control_server.py`
- [ ] 定义请求/响应 JSON 结构
- [ ] 定义统一事件结构

### Phase 2: 最小可用 HTTP 控制面

- [ ] `GET /healthz`
- [ ] `GET /v1/session`
- [ ] `POST /v1/message` 非流式模式
- [ ] 单活跃请求锁
- [ ] token 校验

### Phase 3: NDJSON 流式事件

- [ ] `POST /v1/message` 流式模式
- [ ] `assistant.delta` 事件
- [ ] `tool.start` / `tool.end` 事件
- [ ] `request.complete` 事件

### Phase 4: CLI/HTTP 共用事件总线

- [ ] 抽 `EventSink`
- [ ] 让 CLI 输出改为消费事件
- [ ] 让 HTTP 输出改为消费同一事件流

### Phase 5: 可中断与测试

- [ ] `POST /v1/interrupt` 占位接口
- [ ] cooperative cancellation 设计
- [ ] CLI + HTTP 同时在线场景测试
- [ ] busy / auth / malformed request 测试

## 测试计划

建议新增测试文件：

```text
tests/test_control_server.py
tests/test_control_protocol.py
```

至少覆盖：

- 启动参数解析
- loopback 默认监听
- token 校验
- `/healthz` 返回
- `/v1/session` 返回
- `/v1/message` 非流式成功
- `/v1/message` busy 冲突
- NDJSON 流包含 `tool.start` / `tool.end`
- 不开启 `--control-http` 时现有 CLI 行为不变

## 示例交互

启动：

```bash
export MINIAGENT_CONTROL_TOKEN="dev-token"
python -m miniagent --config examples/langfuse_security_pack/profile.json --control-http 127.0.0.1:8765
```

发送消息：

```bash
curl -N \
  -H "Authorization: Bearer dev-token" \
  -H "Content-Type: application/json" \
  -d '{"text":"compute 2+42","stream":true,"mode":"text"}' \
  http://127.0.0.1:8765/v1/message
```

预期 NDJSON：

```json
{"type":"request.accepted"}
{"type":"tool.start","name":"calculator","arguments":{"expression":"2 + 42"}}
{"type":"tool.end","name":"calculator","result":{"expression":"2 + 42","result":44}}
{"type":"assistant.final","content":"The result is 44."}
{"type":"request.complete","ok":true}
```

## 开放问题

1. HTTP 输入和本地 REPL 是否允许同时写入历史？
   - 当前建议：允许，但通过单活跃请求锁串行化

2. `/v1/history` 是否需要暴露完整消息，还是只暴露最近 N 条？
   - 当前建议：只暴露最近 N 条，默认 `20`

3. `native` 模式下如果供应商返回部分工具 token、部分 tool_calls，事件语义如何统一？
   - 当前建议：统一对外发 `tool.start` / `tool.end`，隐藏内部差异

4. 是否需要“只读观察模式”接口？
   - 第一版不需要

## 结论

这个功能应该被实现为：

- **一个新的 CLI 可选参数**
- **一个标准库实现的极简 HTTP 控制面**
- **一个基于 NDJSON 的 line-based 事件流**
- **一个单进程、单会话、单活跃请求的保守模型**

这样既能解决“机器人无法稳定操控当前 MiniAgent 进程”的问题，也不会把项目带偏成重型服务框架。
