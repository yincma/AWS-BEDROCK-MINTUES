# Python Pro Agent - AWS Bedrock Minutes

## 任务概览
- 配置Python 3.11+项目
- 实现Pydantic数据模型
- 遵循TDD和SOLID原则
- 确保异步代码质量

## 关键技术要求
- Python 3.11+
- FastAPI 0.104+
- Pydantic V2
- 异步编程 (async/await)

## 约定与规范
- 文件命名: snake_case
- 类命名: PascalCase
- 绝对导入: `from src.xxx import yyy`
- 零硬编码
- 所有I/O操作必须异步

## 依赖清单
- fastapi==0.104.1
- pydantic==2.5.0
- boto3==1.29.0
- uvicorn[standard]==0.24.0

## 关键任务
1. T002: 初始化Python项目
2. T013-T015: 实现Pydantic模型
3. T028: FastAPI应用配置

## 成功标准
✅ 代码完全类型提示
✅ 所有异步操作正确实现
✅ 遵守项目宪法原则