# AWS Bedrock Minutes API 文档

**版本**: 1.0.0
**基础URL**: `http://localhost:8000/api/v1`
**日期**: 2025-10-01

## 概述

AWS Bedrock Minutes提供RESTful API用于创建、管理和导出AI生成的会议记录。API采用三阶段工作流(制作-审查-优化)确保输出质量。

## 认证

当前版本暂不需要认证。生产环境建议使用API Key或JWT认证。

## 限流

当前版本暂无限流。生产环境建议配置:
- 每分钟100次请求/IP
- 每小时1000次请求/IP

## 通用响应格式

### 成功响应

```json
{
  "data": {},
  "message": "Success"
}
```

### 错误响应

```json
{
  "detail": "错误描述信息"
}
```

## API端点

### 1. 会议记录管理

#### 1.1 创建会议记录

创建新的会议记录并启动制作阶段。

**端点**: `POST /meetings`

**请求类型**: `multipart/form-data`

**请求参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| input_type | string | 是 | 输入类型: "audio" 或 "text" |
| audio_file | file | 条件 | 音频文件(input_type=audio时必需) |
| text_content | string | 条件 | 文字内容(input_type=text时必需) |
| template_id | string | 否 | 模板ID，默认"default" |

**支持的音频格式**: MP3, WAV, MP4

**文件大小限制**: 最大100MB

**音频时长限制**: 最大2小时(7200秒)

**请求示例**:

```bash
# 音频输入
curl -X POST http://localhost:8000/api/v1/meetings \
  -F "input_type=audio" \
  -F "audio_file=@meeting.mp3" \
  -F "template_id=default"

# 文字输入
curl -X POST http://localhost:8000/api/v1/meetings \
  -F "input_type=text" \
  -F "text_content=今天会议讨论了产品路线图..."
```

**成功响应** (202 Accepted):

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "draft",
  "created_at": "2025-10-01T10:00:00Z",
  "estimated_completion_time": 180
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 会议记录UUID |
| status | string | 当前状态: draft/reviewing/optimizing/completed |
| created_at | string | 创建时间(ISO 8601) |
| estimated_completion_time | integer | 预估完成时间(秒) |

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 400 | 参数错误(如input_type无效、缺少必需参数) |
| 413 | 文件过大(超过100MB) |
| 422 | 音频时长超限(超过2小时) |
| 500 | 服务器内部错误 |

**错误示例**:

```json
// 400 Bad Request
{
  "detail": "input_type必须是audio或text"
}

// 413 Payload Too Large
{
  "detail": "文件大小超过100MB限制"
}

// 422 Unprocessable Entity
{
  "detail": "音频时长超过7200秒限制"
}
```

---

#### 1.2 获取会议记录详情

获取指定会议记录的完整信息，包括所有阶段的内容和状态。

**端点**: `GET /meetings/{meeting_id}`

**路径参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议记录UUID |

**请求示例**:

```bash
curl http://localhost:8000/api/v1/meetings/123e4567-e89b-12d3-a456-426614174000
```

**成功响应** (200 OK):

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-10-01T10:00:00Z",
  "updated_at": "2025-10-01T10:05:00Z",
  "status": "reviewing",
  "input_type": "audio",
  "template_id": "default",
  "current_stage": "draft",
  "audio_key": "audio/123e4567-e89b-12d3-a456-426614174000.mp3",
  "audio_duration_seconds": 1800,
  "original_text": null,
  "stages": {
    "draft": {
      "stage_name": "draft",
      "status": "completed",
      "started_at": "2025-10-01T10:00:05Z",
      "completed_at": "2025-10-01T10:04:30Z",
      "content": "# 会议记录\n\n## 会议基本信息\n...",
      "metadata": {
        "model_id": "amazon.nova-pro-v1:0",
        "tokens_used": 5234
      }
    }
  }
}
```

**响应字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 会议记录UUID |
| created_at | string | 创建时间(ISO 8601) |
| updated_at | string | 最后更新时间(ISO 8601) |
| status | string | 当前状态: draft/reviewing/optimizing/completed/failed |
| input_type | string | 输入类型: audio/text |
| template_id | string | 使用的模板ID |
| current_stage | string | 当前所在阶段: draft/review/final |
| audio_key | string | S3中的音频文件路径(仅audio类型) |
| audio_duration_seconds | integer | 音频时长(秒，仅audio类型) |
| original_text | string | 原始文本内容(仅text类型) |
| stages | object | 各阶段详细信息 |

**stages对象结构**:

```json
{
  "draft": {
    "stage_name": "draft",
    "status": "completed",
    "started_at": "2025-10-01T10:00:05Z",
    "completed_at": "2025-10-01T10:04:30Z",
    "content": "Markdown格式的会议记录内容",
    "metadata": {
      "model_id": "amazon.nova-pro-v1:0",
      "tokens_used": 5234
    }
  },
  "review": {
    "stage_name": "review",
    "status": "completed",
    "started_at": "2025-10-01T10:05:00Z",
    "feedbacks": [
      {
        "feedback_type": "inaccurate",
        "location": "section:决策事项,line:1",
        "comment": "应该是优先开发推荐功能",
        "created_at": "2025-10-01T10:06:00Z"
      }
    ]
  },
  "final": {
    "stage_name": "final",
    "status": "completed",
    "started_at": "2025-10-01T10:06:30Z",
    "completed_at": "2025-10-01T10:08:00Z",
    "content": "优化后的Markdown格式会议记录",
    "metadata": {
      "model_id": "amazon.nova-pro-v1:0",
      "tokens_used": 6100,
      "optimizations_applied": 3
    }
  }
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 会议记录不存在 |

---

#### 1.3 提交审查反馈

在审查阶段提交用户反馈，触发优化阶段。

**端点**: `POST /meetings/{meeting_id}/feedback`

**路径参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议记录UUID |

**请求类型**: `application/json`

**请求体**:

```json
{
  "feedbacks": [
    {
      "feedback_type": "inaccurate",
      "location": "section:决策事项,line:1",
      "comment": "应该是优先开发推荐功能,不是AI功能"
    },
    {
      "feedback_type": "missing",
      "location": "section:行动项",
      "comment": "缺少王五的行动项: 评估技术债务"
    },
    {
      "feedback_type": "improvement",
      "location": "section:讨论议题",
      "comment": "建议添加更多讨论细节"
    }
  ]
}
```

**反馈类型**:

| 类型 | 说明 |
|------|------|
| inaccurate | 内容不准确，需要修正 |
| missing | 缺失重要信息 |
| improvement | 内容可以改进 |
| formatting | 格式问题 |

**location格式**:

- `section:{章节名称}`: 指向整个章节
- `section:{章节名称},line:{行号}`: 指向具体行
- `global`: 全局反馈

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/meetings/123e4567-e89b-12d3-a456-426614174000/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "feedbacks": [
      {
        "feedback_type": "inaccurate",
        "location": "section:决策事项,line:1",
        "comment": "应该是优先开发推荐功能,不是AI功能"
      }
    ]
  }'
```

**成功响应** (202 Accepted):

```json
{
  "message": "反馈已提交,优化中...",
  "meeting_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 会议记录不存在 |
| 409 | 会议状态不允许提交反馈(必须是reviewing状态) |
| 422 | 反馈数据验证失败 |

**错误示例**:

```json
// 409 Conflict
{
  "detail": "会议状态draft不允许提交反馈"
}
```

---

#### 1.4 导出会议记录

导出指定阶段的会议记录为Markdown格式。

**端点**: `GET /meetings/{meeting_id}/export`

**路径参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| meeting_id | string | 是 | 会议记录UUID |

**查询参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| stage | string | 否 | 导出阶段: draft/final，默认final |

**请求示例**:

```bash
# 导出最终版本
curl http://localhost:8000/api/v1/meetings/123e4567-e89b-12d3-a456-426614174000/export?stage=final \
  -o meeting_minutes_final.md

# 导出初稿版本
curl http://localhost:8000/api/v1/meetings/123e4567-e89b-12d3-a456-426614174000/export?stage=draft \
  -o meeting_minutes_draft.md
```

**成功响应** (200 OK):

```
Content-Type: text/markdown

# 会议记录

## 会议基本信息
- 会议主题: 产品路线图讨论
- 会议日期: 2025-10-01
- 参与者: 张三, 李四, 王五

## 讨论议题
1. Q4功能规划
2. 用户反馈分析
3. 技术债务优先级

## 决策事项
- 决策1: 优先开发推荐功能
- 决策2: 延后移动端适配

## 行动项
- [ ] 张三: 完成推荐功能PRD (截止日期: 10-08)
- [ ] 李四: 分析用户反馈数据 (截止日期: 10-05)
- [ ] 王五: 评估技术债务 (截止日期: 10-10)
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 会议记录不存在或指定阶段不存在 |

---

### 2. 模板管理

#### 2.1 获取所有模板

获取所有可用的会议记录模板。

**端点**: `GET /templates`

**请求示例**:

```bash
curl http://localhost:8000/api/v1/templates
```

**成功响应** (200 OK):

```json
[
  {
    "id": "default",
    "name": "默认会议记录模板",
    "description": "适用于大多数会议的通用模板",
    "is_default": true,
    "structure": {
      "sections": [
        {
          "name": "会议基本信息",
          "fields": [
            {"key": "title", "label": "会议主题", "required": true},
            {"key": "date", "label": "会议日期", "required": true},
            {"key": "participants", "label": "参与者", "required": true}
          ]
        },
        {
          "name": "讨论议题",
          "fields": [
            {"key": "topics", "label": "议题列表", "required": true}
          ]
        },
        {
          "name": "决策事项",
          "fields": [
            {"key": "decisions", "label": "决策列表", "required": true}
          ]
        },
        {
          "name": "行动项",
          "fields": [
            {"key": "action_items", "label": "行动项列表", "required": true}
          ]
        }
      ]
    },
    "created_at": "2025-10-01T00:00:00Z"
  },
  {
    "id": "tech-review-001",
    "name": "技术评审模板",
    "description": "用于技术评审会议",
    "is_default": false,
    "structure": {
      "sections": [
        {
          "name": "评审信息",
          "fields": [
            {"key": "title", "label": "评审主题", "required": true},
            {"key": "reviewer", "label": "评审人", "required": true}
          ]
        },
        {
          "name": "评审内容",
          "fields": [
            {"key": "findings", "label": "发现问题", "required": true},
            {"key": "recommendations", "label": "改进建议", "required": true}
          ]
        }
      ]
    },
    "created_at": "2025-10-01T08:00:00Z"
  }
]
```

---

#### 2.2 获取单个模板

获取指定模板的详细信息。

**端点**: `GET /templates/{template_id}`

**路径参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| template_id | string | 是 | 模板ID |

**请求示例**:

```bash
curl http://localhost:8000/api/v1/templates/default
```

**成功响应** (200 OK):

```json
{
  "id": "default",
  "name": "默认会议记录模板",
  "description": "适用于大多数会议的通用模板",
  "is_default": true,
  "structure": {
    "sections": [
      {
        "name": "会议基本信息",
        "fields": [
          {"key": "title", "label": "会议主题", "required": true},
          {"key": "date", "label": "会议日期", "required": true},
          {"key": "participants", "label": "参与者", "required": true}
        ]
      }
    ]
  },
  "created_at": "2025-10-01T00:00:00Z"
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |

---

#### 2.3 创建自定义模板

创建新的自定义会议记录模板。

**端点**: `POST /templates`

**请求类型**: `application/json`

**请求体**:

```json
{
  "name": "技术评审模板",
  "description": "用于技术评审会议",
  "structure": {
    "sections": [
      {
        "name": "评审信息",
        "fields": [
          {"key": "title", "label": "评审主题", "required": true},
          {"key": "reviewer", "label": "评审人", "required": true}
        ]
      },
      {
        "name": "评审内容",
        "fields": [
          {"key": "findings", "label": "发现问题", "required": true},
          {"key": "recommendations", "label": "改进建议", "required": true}
        ]
      }
    ]
  }
}
```

**请求示例**:

```bash
curl -X POST http://localhost:8000/api/v1/templates \
  -H "Content-Type: application/json" \
  -d '{
    "name": "技术评审模板",
    "description": "用于技术评审会议",
    "structure": {
      "sections": [
        {
          "name": "评审信息",
          "fields": [
            {"key": "title", "label": "评审主题", "required": true}
          ]
        }
      ]
    }
  }'
```

**成功响应** (201 Created):

```json
{
  "id": "tech-review-001",
  "name": "技术评审模板",
  "description": "用于技术评审会议",
  "is_default": false,
  "structure": {
    "sections": [
      {
        "name": "评审信息",
        "fields": [
          {"key": "title", "label": "评审主题", "required": true}
        ]
      }
    ]
  },
  "created_at": "2025-10-01T10:15:00Z"
}
```

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 400 | 请求数据验证失败 |
| 409 | 模板名称已存在 |

---

#### 2.4 删除模板

删除自定义模板(默认模板不可删除)。

**端点**: `DELETE /templates/{template_id}`

**路径参数**:

| 参数 | 类型 | 必需 | 说明 |
|------|------|------|------|
| template_id | string | 是 | 模板ID |

**请求示例**:

```bash
curl -X DELETE http://localhost:8000/api/v1/templates/tech-review-001
```

**成功响应** (204 No Content)

**错误响应**:

| 状态码 | 说明 |
|--------|------|
| 404 | 模板不存在 |
| 409 | 尝试删除默认模板 |

---

### 3. 健康检查

#### 3.1 健康检查端点

检查API服务是否正常运行。

**端点**: `GET /health`

**请求示例**:

```bash
curl http://localhost:8000/health
```

**成功响应** (200 OK):

```json
{
  "status": "healthy"
}
```

---

## 状态码汇总

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 201 | 资源创建成功 |
| 202 | 请求已接受，正在处理 |
| 204 | 请求成功，无返回内容 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 资源冲突(如状态不允许操作) |
| 413 | 请求体过大 |
| 422 | 请求数据验证失败 |
| 500 | 服务器内部错误 |

---

## 工作流状态机

### 会议记录状态转换

```
draft → reviewing → optimizing → completed
  ↓         ↓           ↓
failed    failed      failed
```

**状态说明**:

| 状态 | 说明 | 可执行操作 |
|------|------|-----------|
| draft | 制作阶段，AI正在生成初稿 | GET /meetings/{id} |
| reviewing | 审查阶段，等待用户反馈 | GET /meetings/{id}, POST /meetings/{id}/feedback |
| optimizing | 优化阶段，AI根据反馈优化 | GET /meetings/{id} |
| completed | 已完成所有阶段 | GET /meetings/{id}, GET /meetings/{id}/export |
| failed | 处理失败 | GET /meetings/{id} |

---

## 最佳实践

### 1. 轮询状态建议

由于AI处理需要时间，建议采用指数退避策略轮询:

```bash
#!/bin/bash
meeting_id="123e4567-e89b-12d3-a456-426614174000"
interval=5  # 初始间隔5秒

while true; do
  status=$(curl -s http://localhost:8000/api/v1/meetings/$meeting_id | jq -r '.status')
  echo "Status: $status"

  if [ "$status" = "completed" ] || [ "$status" = "failed" ]; then
    break
  fi

  sleep $interval
  interval=$((interval * 2))  # 指数增长

  if [ $interval -gt 60 ]; then
    interval=60  # 最大60秒
  fi
done
```

### 2. 错误处理

始终检查HTTP状态码并处理错误:

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/meetings",
    files={"audio_file": open("meeting.mp3", "rb")},
    data={"input_type": "audio"}
)

if response.status_code == 202:
    meeting = response.json()
    print(f"会议创建成功: {meeting['id']}")
elif response.status_code == 413:
    print("错误: 文件过大")
elif response.status_code == 422:
    print("错误: 音频时长超限")
else:
    print(f"错误: {response.json()['detail']}")
```

### 3. 大文件上传

对于大音频文件，考虑分段处理或预处理:

```python
# 压缩音频到64kbps
from pydub import AudioSegment

audio = AudioSegment.from_mp3("large_meeting.mp3")
audio.export("compressed_meeting.mp3", format="mp3", bitrate="64k")
```

---

## 示例代码

### Python客户端示例

```python
import requests
import time
from typing import Optional

class BedrockMinutesClient:
    def __init__(self, base_url: str = "http://localhost:8000/api/v1"):
        self.base_url = base_url

    def create_meeting_from_audio(self, audio_path: str, template_id: str = "default") -> dict:
        """从音频文件创建会议记录"""
        with open(audio_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/meetings",
                files={"audio_file": f},
                data={"input_type": "audio", "template_id": template_id}
            )
        response.raise_for_status()
        return response.json()

    def create_meeting_from_text(self, text: str, template_id: str = "default") -> dict:
        """从文字创建会议记录"""
        response = requests.post(
            f"{self.base_url}/meetings",
            data={"input_type": "text", "text_content": text, "template_id": template_id}
        )
        response.raise_for_status()
        return response.json()

    def get_meeting(self, meeting_id: str) -> dict:
        """获取会议记录详情"""
        response = requests.get(f"{self.base_url}/meetings/{meeting_id}")
        response.raise_for_status()
        return response.json()

    def submit_feedback(self, meeting_id: str, feedbacks: list) -> dict:
        """提交审查反馈"""
        response = requests.post(
            f"{self.base_url}/meetings/{meeting_id}/feedback",
            json={"feedbacks": feedbacks}
        )
        response.raise_for_status()
        return response.json()

    def export_meeting(self, meeting_id: str, stage: str = "final") -> str:
        """导出会议记录"""
        response = requests.get(
            f"{self.base_url}/meetings/{meeting_id}/export",
            params={"stage": stage}
        )
        response.raise_for_status()
        return response.text

    def wait_for_status(self, meeting_id: str, target_status: str, timeout: int = 600) -> dict:
        """等待会议达到指定状态"""
        start_time = time.time()
        interval = 5

        while time.time() - start_time < timeout:
            meeting = self.get_meeting(meeting_id)
            if meeting["status"] == target_status or meeting["status"] == "failed":
                return meeting
            time.sleep(interval)
            interval = min(interval * 1.5, 60)  # 指数退避，最大60秒

        raise TimeoutError(f"等待状态{target_status}超时")

# 使用示例
client = BedrockMinutesClient()

# 创建会议
meeting = client.create_meeting_from_audio("meeting.mp3")
print(f"会议ID: {meeting['id']}")

# 等待完成
meeting = client.wait_for_status(meeting["id"], "reviewing")
print("初稿已完成，进入审查阶段")

# 提交反馈
feedbacks = [
    {
        "feedback_type": "inaccurate",
        "location": "section:决策事项,line:1",
        "comment": "需要修正决策描述"
    }
]
client.submit_feedback(meeting["id"], feedbacks)

# 等待优化完成
meeting = client.wait_for_status(meeting["id"], "completed")
print("优化已完成")

# 导出最终版本
markdown = client.export_meeting(meeting["id"], stage="final")
with open("meeting_minutes.md", "w") as f:
    f.write(markdown)
print("会议记录已导出")
```

---

## 交互式文档

FastAPI自动生成交互式API文档:

- **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI Schema**: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

---

## 更新日志

### v1.0.0 (2025-10-01)

- 初始版本发布
- 支持音频和文字输入
- 三阶段工作流(制作-审查-优化)
- 模板管理功能
- Markdown导出功能

---

## 支持

- 问题反馈: [GitHub Issues](https://github.com/your-org/AWS-Bedrock-Mintues/issues)
- 详细规范: `/specs/001-ai/`
- 示例代码: `/examples/`

---

生成时间: 2025-10-01 | 版本: 1.0.0
