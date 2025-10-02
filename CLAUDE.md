# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AWS Bedrock Minutes 是一个基于 AWS Bedrock Nova Pro 的 AI 会议记录生成系统,采用三阶段工作流(Draft-Review-Final)自动生成高质量会议记录。

**核心架构特点:**
- **三阶段工作流**: Draft(制作) → Review(审查) → Final(优化)
- **异步处理**: 基于 FastAPI 的异步 API,支持长时间转录和 AI 处理
- **状态机管理**: WorkflowService 编排状态转换(processing → reviewing → completed)
- **AWS 服务集成**: Bedrock (AI)、Transcribe (语音转文字)、S3 (存储)

## 关键架构理解

### 三阶段工作流状态机

```
创建会议 → Draft 阶段 → Review 阶段 → Final 阶段
   ↓           ↓            ↓             ↓
status:    processing   reviewing      completed
   ↓           ↓            ↓             ↓
input     转录+AI提取   用户标记反馈   AI优化输出
```

**重要**:
- `WorkflowService` 是核心编排器,所有阶段转换必须通过它
- `meeting.status` 和 `meeting.current_stage` 必须同步更新
- 每个阶段有独立的 `ProcessingStage` 或 `ReviewStage` 对象存储在 `meeting.stages` 字典中

### 分层架构

```
API Layer (src/api/routes/)
    ↓ 调用
Service Layer (src/services/)
    ↓ 调用
Repository Layer (src/storage/)
    ↓ 访问
AWS Services (S3, Bedrock, Transcribe)
```

**职责分离**:
- **Routes**: 请求验证、响应格式化
- **Services**: 业务逻辑编排 (如 WorkflowService 协调多个服务)
- **Repositories**: 数据持久化封装 (如 MeetingRepository 管理 S3 JSON 存储)
- **Models**: Pydantic 数据验证和序列化

### S3 存储架构

所有数据存储在 S3 中,按类型分目录:
- `audio/{meeting_id}.mp3` - 原始音频文件
- `transcripts/{meeting_id}.txt` - 转录文本
- `meetings/{meeting_id}.json` - 会议记录完整状态 (包含所有阶段数据)
- `templates/{template_id}.json` - 模板定义

**注意**: `MeetingMinute` 对象会频繁序列化/反序列化到 S3,修改模型时注意向后兼容。

## 常用开发命令

### 启动开发服务器
```bash
uvicorn src.api.main:app --reload
```

### 测试命令
```bash
# 运行所有测试
pytest

# 运行特定类型测试
pytest tests/unit/ -m unit
pytest tests/integration/ -m integration
pytest tests/contract/ -m contract
pytest tests/performance/ -m performance

# 生成覆盖率报告
pytest --cov=src --cov-report=html
open htmlcov/index.html

# 运行单个测试文件
pytest tests/unit/test_services.py -v

# 运行单个测试
pytest tests/unit/test_services.py::test_specific_function -v
```

### 代码质量检查
```bash
# Ruff 检查和格式化
ruff check src/ tests/
ruff format src/ tests/
```

### 初始化默认模板
```bash
# 首次部署时需要运行
python -m src.cli.init_defaults
```

## 关键开发注意事项

### 1. 异步编程规范
- 所有 Service 层方法必须是 `async def`
- Repository 层的 S3 操作必须是异步的 (`await s3_client.get_object()`)
- API Routes 中的依赖注入也必须是异步的

### 2. 错误处理
- Service 层抛出领域特定异常 (如 `WorkflowError`, `TranscriptionError`)
- API 层通过 `error_handler_middleware` 统一捕获并转换为 HTTP 响应
- 所有 AI 调用通过 `WorkflowService._call_ai_with_retry()` 实现指数退避重试

### 3. 状态管理
- **永远不要**直接修改 `meeting.status`,必须通过 WorkflowService 方法
- 状态转换顺序: `processing` → `reviewing` → `completed` (或 `failed`)
- 使用 `meeting.current_stage` 追踪当前所在阶段 (draft/review/final)

### 4. AI Prompt 管理
- Prompt 模板位于 `prompts/` 目录
- 使用 `PromptLoader` 加载 prompt 并插值变量
- Draft 和 Final 阶段使用不同的 prompt 模板

### 5. 模板系统
- 默认模板在 `src/models/template.py` 中定义 (`DEFAULT_TEMPLATE`)
- Template 包含 `structure` (sections定义) 和 `format_rules` (格式规则)
- Template 变更需要同时更新 prompt 模板以匹配新结构

### 6. 测试策略
本项目严格遵循 TDD:
- **Contract Tests** (`tests/contract/`): API 契约测试,验证请求/响应格式
- **Unit Tests** (`tests/unit/`): 单元测试,mock 外部依赖
- **Integration Tests** (`tests/integration/`): 集成测试,使用 moto mock AWS 服务
- **Performance Tests** (`tests/performance/`): 性能测试,验证并发和响应时间

**编写新功能时顺序**: Contract Test → Unit Test → 实现 → Integration Test

### 7. 日志配置
- 日志级别通过环境变量 `LOG_LEVEL` 控制 (默认 INFO)
- 日志格式通过 `LOG_FORMAT` 控制 (standard 或 json)
- 生产环境建议使用 json 格式便于日志聚合

### 8. 环境变量
必需的环境变量 (参考 `.env.example`):
- `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- `S3_BUCKET_NAME` - S3 存储桶必须提前创建
- `BEDROCK_MODEL_ID` - 默认 `amazon.nova-pro-v1:0`
- `TRANSCRIBE_LANGUAGE_CODE` - 默认 `zh-CN`

## 部署注意事项

### Lambda 部署
- 注意 Lambda 超时限制,转录和 AI 处理可能需要 15 分钟+
- 建议使用 Step Functions 编排长时间工作流
- 确保 Lambda 角色有 Bedrock、Transcribe、S3 权限

### EC2/容器部署
- 使用 systemd 或 supervisord 管理 uvicorn 进程
- 建议使用 nginx 反向代理并配置 SSL
- 监控 `/health` 端点确保服务健康

### AWS 权限最小化
IAM 策略应包含:
```json
{
  "Effect": "Allow",
  "Action": [
    "bedrock:InvokeModel",
    "transcribe:StartTranscriptionJob",
    "transcribe:GetTranscriptionJob",
    "s3:PutObject",
    "s3:GetObject"
  ],
  "Resource": "*"
}
```

## API 端点快速参考

- `POST /api/v1/meetings` - 创建会议 (上传音频或文本)
- `GET /api/v1/meetings/{id}` - 查询会议状态
- `POST /api/v1/meetings/{id}/feedback` - 提交审查反馈
- `GET /api/v1/meetings/{id}/export` - 导出会议记录 (可指定 stage)
- `GET /api/v1/templates` - 列出所有模板
- `GET /api/v1/templates/{id}` - 获取模板详情

完整 API 文档: http://localhost:8000/docs

## 常见问题排查

### 问题: 转录一直处于 processing 状态
- 检查 AWS Transcribe 作业状态: `aws transcribe get-transcription-job --transcription-job-name <job_id>`
- 检查音频文件是否成功上传到 S3
- 确认 `TRANSCRIBE_LANGUAGE_CODE` 与音频语言匹配

### 问题: AI 调用返回空结果
- 检查 Bedrock 模型访问权限: `aws bedrock list-foundation-models`
- 查看日志中的 AI 响应内容,可能是 prompt 解析失败
- 确认 `BEDROCK_MODEL_ID` 正确且在当前 region 可用

### 问题: S3 权限错误
- 确认 S3 bucket 已创建: `aws s3 ls s3://<bucket-name>`
- 验证 IAM 角色/用户有 PutObject 和 GetObject 权限
- 检查 bucket 策略是否允许当前账号访问

## 项目宪法 (编码原则)

本项目严格遵循以下原则:
- **KISS**: 避免过度设计,保持代码简洁
- **YAGNI**: 只实现当前需要的功能
- **SOLID**: 面向对象设计原则
- **零技术债务**: 不允许硬编码、TODO 注释、临时方案
- **TDD**: 测试驱动开发,覆盖率 >90%

**重要**: 修改代码时必须同时更新测试,且所有测试必须通过后才能提交。
