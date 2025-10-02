<!--
Sync Impact Report:
Version: 0.0.0 → 1.0.0
Change Type: Initial Constitution Creation
Modified Principles: N/A (Initial creation)
Added Sections:
  - Core Principles (5 principles)
  - Development Standards
  - Quality Assurance
  - Governance
Templates Status:
  ✅ plan-template.md - Constitution Check section compatible
  ✅ spec-template.md - Requirement standards aligned
  ✅ tasks-template.md - TDD workflow aligned
Follow-up TODOs: None
-->

# AWS Bedrock Minutes Constitution

## Core Principles

### I. Simplicity First (KISS)
- 每个功能 MUST 采用最简单的可行方案
- 禁止过度设计和不必要的抽象层
- 代码 MUST 易读、易维护
- 复杂性 MUST 有明确的业务价值支撑

**理由**: 简单的系统更易于理解、测试和维护,降低长期维护成本

### II. Need-Driven Development (YAGNI)
- 仅实现当前需求,禁止预测性开发
- 功能 MUST 有明确的用户需求或业务价值
- 避免"可能会用到"的代码和基础设施
- 每个依赖 MUST 经过充分评估

**理由**: 防止代码膨胀,降低维护开销,保持系统精简

### III. Test-First Development (NON-NEGOTIABLE)
- TDD 流程强制执行: 测试编写 → 用户确认 → 测试失败 → 实现代码
- 禁止在测试失败前编写实现代码
- 严格遵循 Red-Green-Refactor 循环
- 每个功能 MUST 有相应的自动化测试

**理由**: 确保代码质量,防止回归,提供可靠的重构安全网

### IV. Zero Technical Debt
- 禁止硬编码:所有配置 MUST 外部化
- 禁止魔法数字:所有常量 MUST 命名和文档化
- 禁止临时方案:所有实现 MUST 是生产就绪的
- 代码 MUST 遵循 SOLID 原则
- 每次提交 MUST 保持代码库健康

**理由**: 技术债务会累积并显著降低开发速度,零容忍政策确保长期可维护性

### V. SOTA (State-of-the-Art) Implementation
- 采用当前最佳实践和模式
- 使用稳定的最新版本依赖
- 遵循语言和框架的惯用法
- 持续关注安全更新和性能优化
- 设计 MUST 支持可扩展性和可测试性

**理由**: 保持技术栈现代化,利用社区最佳实践,提升系统质量

## Development Standards

### Configuration Management
- 所有配置 MUST 使用环境变量或配置文件
- 敏感信息 MUST 通过 AWS Secrets Manager 或类似服务管理
- 禁止在代码中硬编码 URL、密钥、阈值等
- 配置 MUST 有清晰的文档和验证机制

### Code Organization
- 遵循单一职责原则 (SRP)
- 保持函数和类的小型化和专注
- 使用清晰的命名约定
- 代码 MUST 自文档化,复杂逻辑需要注释说明意图

### AWS Best Practices
- 使用 Infrastructure as Code (CDK/CloudFormation)
- 遵循 Well-Architected Framework 原则
- 实现适当的错误处理和重试逻辑
- 优化成本和性能
- 确保高可用性和容错能力

### AI/ML Specific Standards
- Prompt 模板 MUST 外部化和版本控制
- 模型调用 MUST 有超时和错误处理
- 实现适当的输入验证和输出清理
- 记录模型版本和配置以支持可重现性
- 监控 AI 服务的使用量和成本

## Quality Assurance

### Testing Requirements
- **Contract Tests**: 每个 API 端点 MUST 有 contract 测试
- **Integration Tests**: 每个用户场景 MUST 有集成测试
- **Unit Tests**: 关键业务逻辑 MUST 有单元测试
- 测试 MUST 快速、可靠、独立运行
- 测试覆盖率目标: 核心逻辑 ≥ 80%

### Code Review Standards
- 每个 PR MUST 经过代码审查
- 审查 MUST 验证宪法合规性
- 审查 MUST 检查测试覆盖和质量
- 拒绝包含技术债务的 PR

### Performance Standards
- API 响应时间 MUST < 3 秒 (p95)
- 批量操作 MUST 支持分页和流式处理
- 资源使用 MUST 经过监控和优化
- 性能回归 MUST 在 CI/CD 中检测

## Governance

### Amendment Process
1. 提出修订提案,包含理由和影响分析
2. 评估对现有代码和工作流的影响
3. 更新所有依赖文档和模板
4. 记录版本变更和迁移计划
5. 团队审查和批准

### Compliance
- 所有 PR/审查 MUST 验证宪法合规性
- 复杂性 MUST 有明确的业务理由
- 偏离原则 MUST 在 Complexity Tracking 中记录
- 定期审查宪法的适用性和有效性

### Version Control
- 遵循语义化版本: MAJOR.MINOR.PATCH
- MAJOR: 不兼容的治理/原则变更
- MINOR: 新增原则或重大扩展
- PATCH: 澄清、措辞优化、非语义改进

**Version**: 1.0.0 | **Ratified**: 2025-10-01 | **Last Amended**: 2025-10-01