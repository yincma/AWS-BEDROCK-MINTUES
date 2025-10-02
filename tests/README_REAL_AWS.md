# 使用真实AWS资源进行测试

本项目的测试现已配置为使用真实的AWS资源，而非mock。

## 前置条件

### 1. AWS凭证配置

确保你的AWS凭证已正确配置。可以通过以下方式之一：

**方法A: AWS CLI配置**
```bash
aws configure
```

**方法B: 环境变量**
```bash
export AWS_ACCESS_KEY_ID=你的access_key
export AWS_SECRET_ACCESS_KEY=你的secret_key
export AWS_REGION=us-east-1
```

**方法C: .env文件**
```env
AWS_ACCESS_KEY_ID=你的access_key
AWS_SECRET_ACCESS_KEY=你的secret_key
AWS_REGION=us-east-1
```

### 2. 测试S3 Bucket配置

设置测试专用的S3 bucket：

```bash
export TEST_S3_BUCKET=meeting-minutes-test
```

如果未设置，测试会尝试创建名为`meeting-minutes-test`的bucket。

### 3. Bedrock模型访问

确保你的AWS账户有权限访问以下Bedrock模型：
- `amazon.nova-pro-v1:0` (默认)

可以通过环境变量自定义：
```bash
export BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
```

### 4. AWS服务权限

你的AWS IAM角色/用户需要以下权限：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::meeting-minutes-test",
        "arn:aws:s3:::meeting-minutes-test/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "transcribe:StartTranscriptionJob",
        "transcribe:GetTranscriptionJob",
        "transcribe:DeleteTranscriptionJob"
      ],
      "Resource": "*"
    }
  ]
}
```

## 运行测试

### Contract测试
```bash
# 运行所有contract测试
export PYTHONPATH=. && pytest tests/contract/ -v

# 运行特定测试文件
export PYTHONPATH=. && pytest tests/contract/test_create_meeting.py -v
```

### 单元测试
```bash
# 运行所有单元测试
export PYTHONPATH=. && pytest tests/unit/ -v
```

### 集成测试
```bash
# 运行所有集成测试（使用真实AWS服务）
export PYTHONPATH=. && pytest tests/integration/ -v
```

## 成本考虑

⚠️ **重要提示**: 使用真实AWS资源会产生费用

### 预估测试成本（每次完整测试运行）

- **S3存储**: ~$0.001
- **Bedrock API调用**: ~$0.05 (取决于测试数量和token使用)
- **Transcribe**: ~$0.024/分钟 × 测试音频总时长

**预估总成本**: 约$0.10-0.50 每次完整测试运行

### 成本优化建议

1. **选择性运行测试**
   ```bash
   # 只运行单元测试（不调用Bedrock）
   pytest tests/unit/ -m unit
   ```

2. **使用测试标记**
   ```bash
   # 跳过expensive的测试
   pytest -m "not expensive"
   ```

3. **定期清理测试资源**
   ```bash
   # 清理S3测试bucket中的对象
   aws s3 rm s3://meeting-minutes-test/ --recursive
   ```

## 测试清理

### 自动清理

测试fixture会自动处理以下清理：
- 测试结束后删除创建的临时S3对象（可选）
- 不会删除S3 bucket本身（复用）

### 手动清理

如需完全清理测试环境：

```bash
# 删除所有测试数据
aws s3 rm s3://meeting-minutes-test/ --recursive

# 删除测试bucket（如果不再需要）
aws s3 rb s3://meeting-minutes-test
```

## 测试音频文件

测试会自动在`tests/fixtures/`目录下生成最小的有效MP3文件。如需使用真实的录音进行测试：

1. 将音频文件放置在`tests/fixtures/`目录
2. 命名为：
   - `test_short.mp3` - 短音频（< 1分钟）
   - `test_long.mp3` - 长音频（用于测试时长限制）

## 故障排查

### 问题：AWS凭证错误
```
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

**解决方案**: 确保AWS凭证已配置（见前置条件第1步）

### 问题：S3 Bucket访问被拒绝
```
botocore.exceptions.ClientError: An error occurred (AccessDenied)
```

**解决方案**:
1. 检查IAM权限是否包含S3操作
2. 确认bucket名称正确

### 问题：Bedrock模型访问被拒绝
```
botocore.exceptions.ClientError: An error occurred (AccessDeniedException) when calling the InvokeModel operation
```

**解决方案**:
1. 在AWS Bedrock控制台启用模型访问
2. 确认IAM角色有`bedrock:InvokeModel`权限
3. 检查region是否支持该模型

### 问题：测试超时
```
pytest.TimeoutError: Test timed out
```

**解决方案**: 真实AWS调用比mock慢，增加超时时间：
```bash
pytest --timeout=300  # 5分钟超时
```

## CI/CD集成

### GitHub Actions示例

```yaml
name: Tests with Real AWS
on: [push]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
      - name: Run tests
        run: |
          export TEST_S3_BUCKET=meeting-minutes-test-ci
          pytest tests/ -v
```

## 最佳实践

1. **使用专用测试账户**: 建议使用单独的AWS账户进行测试
2. **设置预算警报**: 在AWS Billing中设置预算警报，避免意外费用
3. **定期审查资源**: 定期检查并清理未使用的测试资源
4. **使用测试标记**: 区分快速测试和expensive测试
5. **本地开发时**: 考虑使用localstack等本地AWS模拟工具

## 参考文档

- [AWS SDK for Python (Boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS Bedrock定价](https://aws.amazon.com/bedrock/pricing/)
- [AWS S3定价](https://aws.amazon.com/s3/pricing/)
- [AWS Transcribe定价](https://aws.amazon.com/transcribe/pricing/)
