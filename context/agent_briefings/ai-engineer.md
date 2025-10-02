# AI Engineer Agent - AWS Bedrock Minutes

## AI服务选择
- 模型: AWS Bedrock Nova Pro
- 多模态能力
- 长文本理解
- 成本效率高

## Prompt工程策略
- 外部化Prompt模板
- 使用Jinja2模板引擎
- Few-shot示例
- 结构化输出

## 关键任务
1. T020: AI服务实现
2. T022: 模板引擎
3. T023: 工作流编排
4. T024: Prompt模板管理

## Nova Pro Prompt最佳实践
```
<role>专业会议记录助手</role>
<task>
根据模板提取会议关键信息:
{meeting_transcript}
</task>
```

## 处理能力
- 输入处理: 10k tokens
- 输出生成: 5k tokens
- 平均处理时间: 音频时长的0.5-1倍

## 成功标准
✅ 结构化Markdown输出
✅ 关键信息准确提取
✅ 支持多种模板
✅ 高质量AI生成