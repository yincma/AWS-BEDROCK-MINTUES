# CLI工具使用演示

## T036: 初始化默认数据CLI工具

### 文件结构

```
src/cli/
├── __init__.py           # CLI包初始化
├── init_defaults.py      # 初始化默认数据工具
└── README.md             # CLI文档
```

### 功能特性

✅ **已实现**:
- 检查并创建默认会议记录模板
- 避免重复创建(智能检测)
- 友好的命令行界面
- 详细的错误提示和调试信息
- 支持多种运行方式
- 完整的错误处理
- 单元测试覆盖

### 使用方法

#### 1. 作为Python模块运行(推荐)

```bash
# 激活虚拟环境
source venv/bin/activate

# 显示帮助
python -m src.cli.init_defaults --help

# 运行初始化
python -m src.cli.init_defaults
```

#### 2. 直接运行脚本

```bash
# 激活虚拟环境
source venv/bin/activate

# 显示帮助
python src/cli/init_defaults.py -h

# 运行初始化
python src/cli/init_defaults.py
```

### 环境配置

需要在`.env`文件或环境变量中配置:

```bash
# AWS配置
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key_id
AWS_SECRET_ACCESS_KEY=your_secret_access_key

# S3存储桶
S3_BUCKET_NAME=meeting-minutes-dev
```

### 输出示例

#### 场景1: 首次运行(创建默认模板)

```
============================================================
AWS Bedrock Minutes - 初始化默认数据
============================================================

✓ 已创建默认模板: 标准会议记录模板
  ID: default
  章节数: 2

============================================================
✓ 初始化完成
============================================================
```

#### 场景2: 再次运行(模板已存在)

```
============================================================
AWS Bedrock Minutes - 初始化默认数据
============================================================

✓ 默认模板已存在
  ID: default
  名称: 标准会议记录模板
  创建时间: 2025-10-01 00:00:00

============================================================
✓ 初始化完成
============================================================
```

#### 场景3: 错误情况

```
============================================================
AWS Bedrock Minutes - 初始化默认数据
============================================================

============================================================
✗ 错误: Could not connect to the endpoint URL
============================================================

请检查:
  1. AWS凭证是否正确配置
  2. S3存储桶是否存在且有访问权限
  3. 网络连接是否正常

详细错误信息:
[完整的错误堆栈信息]
```

### 默认模板结构

工具会创建以下默认模板:

```json
{
  "id": "default",
  "name": "标准会议记录模板",
  "is_default": true,
  "created_at": "2025-10-01T00:00:00",
  "creator_identifier": null,
  "structure": {
    "sections": [
      {
        "name": "会议基本信息",
        "fields": [
          {"key": "title", "label": "会议主题", "required": true},
          {"key": "date", "label": "会议日期", "required": true},
          {"key": "participants", "label": "参与者", "required": false}
        ]
      },
      {
        "name": "会议内容",
        "fields": [
          {"key": "topics", "label": "讨论议题", "required": true},
          {"key": "decisions", "label": "决策事项", "required": false},
          {"key": "action_items", "label": "行动项", "required": false}
        ]
      }
    ]
  }
}
```

### 测试

运行单元测试:

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
python -m pytest tests/unit/test_cli_init_defaults.py -v

# 运行测试并查看覆盖率
python -m pytest tests/unit/test_cli_init_defaults.py -v --cov=src.cli.init_defaults
```

### 测试覆盖

✅ 测试用例:
1. `test_init_default_template_creates_new` - 创建新模板
2. `test_init_default_template_already_exists` - 模板已存在
3. `test_init_default_template_s3_error` - S3错误处理
4. `test_default_template_structure` - 验证模板结构

### 错误处理

工具会自动处理以下错误:

1. **AWS凭证错误**
   - 检查AWS_ACCESS_KEY_ID和AWS_SECRET_ACCESS_KEY

2. **S3权限错误**
   - 确保有s3:GetObject和s3:PutObject权限

3. **网络连接错误**
   - 检查网络连接和AWS区域设置

4. **配置错误**
   - 检查.env文件或环境变量

5. **用户中断**
   - Ctrl+C优雅退出

### 退出代码

- `0`: 成功
- `1`: 错误
- `130`: 用户中断(Ctrl+C)

### 技术实现要点

1. **异步支持**: 使用`asyncio.run()`运行异步初始化函数
2. **路径处理**: 支持直接运行和模块运行两种方式
3. **错误处理**: 完善的异常捕获和友好提示
4. **幂等性**: 多次运行不会重复创建
5. **类型注解**: 完整的类型提示支持
6. **文档字符串**: 详细的docstring文档

### 注意事项

1. ⚠️ 必须先激活虚拟环境
2. ⚠️ 需要正确配置AWS凭证
3. ⚠️ S3存储桶必须存在
4. ⚠️ 需要对S3存储桶有读写权限
5. ✅ 工具是幂等的,可以安全地重复运行
6. ✅ 不会覆盖已存在的默认模板

### 扩展可能性

未来可以扩展更多CLI命令:

```python
# 可选的扩展命令
- init-defaults    # 当前已实现
- list-templates   # 列出所有模板
- list-meetings    # 列出所有会议记录
- show-meeting     # 显示指定会议记录
- export-meeting   # 导出会议记录
- cleanup          # 清理旧数据
```

### 总结

✅ 任务T036已完成:
- ✓ 创建CLI工具`src/cli/init_defaults.py`
- ✓ 支持两种运行方式(模块/直接运行)
- ✓ 完整的错误处理和用户提示
- ✓ 单元测试覆盖(4个测试用例全部通过)
- ✓ 详细的使用文档
- ✓ 幂等性保证
- ✓ 友好的CLI界面
