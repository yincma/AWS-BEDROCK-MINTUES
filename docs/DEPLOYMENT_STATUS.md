# 部署状态说明

**更新时间**: 2025-10-01
**项目**: AWS Bedrock Minutes

## 🎯 核心问题解答

### Q1: AWS上的部署是如何实现的？

**答案**: ❌ **当前完全未实现AWS部署**

- 代码只能在本地运行（开发模式）
- README中的"AWS Lambda部署"只是**文档/规划**，非实际代码
- 没有任何IaC(基础设施即代码)

### Q2: 本地运行时API Gateway如何构建？

**答案**: ✅ **本地开发不需要API Gateway**

**理解误区澄清**:
- API Gateway是AWS的**托管服务**，不是本地构建的
- 本地开发直接使用**uvicorn运行FastAPI**
- FastAPI本身就是完整的Web服务器

---

## 📊 本地 vs AWS 架构对比

### 当前实现: 本地开发环境

```
┌─────────────────────────────────┐
│   本地开发 (已实现 ✅)          │
├─────────────────────────────────┤
│                                 │
│  浏览器/curl                    │
│       ↓                         │
│  http://localhost:8000          │
│       ↓                         │
│  uvicorn (ASGI服务器)           │
│       ↓                         │
│  FastAPI应用                    │
│  - src/api/main.py              │
│  - src/api/routes/              │
│       ↓                         │
│  业务逻辑层                     │
│  - src/services/                │
│       ↓                         │
│  AWS SDK (boto3)                │
│       ↓                         │
│  AWS云服务 (通过Internet)      │
│  - S3 (存储)                    │
│  - Bedrock (AI)                 │
│  - Transcribe (转录)            │
│                                 │
└─────────────────────────────────┘

运行方式:
$ uvicorn src.api.main:app --reload
```

### 规划中: AWS Lambda部署 (未实现 ❌)

```
┌─────────────────────────────────────────┐
│   AWS生产环境 (未实现 ❌)              │
├─────────────────────────────────────────┤
│                                         │
│  用户请求                               │
│       ↓                                 │
│  Internet Gateway                       │
│       ↓                                 │
│  ┌─────────────────────────┐           │
│  │  API Gateway (AWS托管)   │           │
│  │  - 路由管理              │           │
│  │  - 请求验证              │           │
│  │  - 限流/授权             │           │
│  └─────────────────────────┘           │
│       ↓                                 │
│  ┌─────────────────────────┐           │
│  │  Lambda函数 (AWS托管)    │           │
│  │  - Python 3.11运行时     │           │
│  │  - Mangum适配器          │  ← 缺失!
│  │  - FastAPI应用           │           │
│  │  - 15分钟超时限制        │           │
│  └─────────────────────────┘           │
│       ↓                                 │
│  VPC内网访问 (可选)                     │
│       ↓                                 │
│  ┌─────────────────────────┐           │
│  │  AWS服务 (同区域内网)    │           │
│  │  - S3                    │           │
│  │  - Bedrock               │           │
│  │  - Transcribe            │           │
│  └─────────────────────────┘           │
│                                         │
└─────────────────────────────────────────┘

需要的组件(全部缺失):
1. lambda_handler.py (Lambda入口)
2. mangum包装器
3. CloudFormation/CDK代码
4. 部署脚本
```

---

## 🔍 当前代码分析

### 已有的代码结构

**src/api/main.py** (FastAPI应用):
```python
from fastapi import FastAPI

app = FastAPI(
    title="AWS Bedrock Minutes API",
    version="1.0.0"
)

# 直接运行: uvicorn src.api.main:app
```

**问题**: 
- ❌ 没有Lambda handler
- ❌ 没有mangum适配器
- ✅ 只能本地运行

### 缺失的Lambda适配器

**需要但未实现**:
```python
# lambda_handler.py (不存在)
from mangum import Mangum
from src.api.main import app

# Lambda入口点
handler = Mangum(app, lifespan="off")
```

---

## 💡 本地开发如何工作 (当前实现)

### 本地运行原理

**不需要API Gateway**，因为：

1. **uvicorn = ASGI服务器** (替代API Gateway功能)
   ```bash
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```
   - uvicorn监听8000端口
   - 处理HTTP请求
   - 调用FastAPI应用
   - 返回HTTP响应

2. **FastAPI = Web框架** (处理业务逻辑)
   - 路由匹配
   - 参数验证
   - 调用业务代码
   - 生成响应

3. **本地访问**:
   ```
   http://localhost:8000/api/v1/meetings
   ↓
   uvicorn接收 → FastAPI处理 → 返回JSON
   ```

### 为什么不需要本地"构建"API Gateway?

**API Gateway是AWS的托管服务**，特点：
- 在AWS云端运行
- 不是本地软件
- 不需要"构建"
- 通过AWS控制台/CDK/CloudFormation创建

**本地开发替代方案**:
- uvicorn = 本地HTTP服务器
- 提供相同的HTTP API
- 开发/测试时完全够用

---

## 🛠️ 要部署到AWS需要什么？

### 方案1: Lambda + API Gateway (Serverless)

#### 需要添加的代码

**1. Lambda Handler** (新文件)
```python
# lambda_handler.py
from mangum import Mangum
from src.api.main import app

# Lambda入口点
handler = Mangum(app, lifespan="off")
```

**2. requirements.txt更新**
```
mangum==0.17.0  # FastAPI → Lambda适配器
```

**3. AWS CDK部署代码** (新目录)
```python
# infrastructure/cdk/app.py
from aws_cdk import (
    Stack, App,
    aws_lambda as lambda_,
    aws_apigateway as apigw,
    aws_s3 as s3,
    aws_iam as iam,
    Duration
)
from aws_cdk.aws_lambda_python_alpha import PythonFunction

class BedrockMinutesStack(Stack):
    def __init__(self, scope, construct_id):
        super().__init__(scope, construct_id)
        
        # 1. 创建S3 Bucket
        bucket = s3.Bucket(
            self, "MeetingsBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED
        )
        
        # 2. 创建Lambda函数
        lambda_fn = PythonFunction(
            self, "APIFunction",
            entry=".",  # 项目根目录
            runtime=lambda_.Runtime.PYTHON_3_11,
            index="lambda_handler.py",
            handler="handler",
            timeout=Duration.minutes(15),
            memory_size=1024,
            environment={
                "S3_BUCKET_NAME": bucket.bucket_name,
                "BEDROCK_MODEL_ID": "amazon.nova-pro-v1:0",
                "AWS_REGION": "us-east-1"
            }
        )
        
        # 3. 授予权限
        bucket.grant_read_write(lambda_fn)
        lambda_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "transcribe:StartTranscriptionJob",
                    "transcribe:GetTranscriptionJob"
                ],
                resources=["*"]
            )
        )
        
        # 4. 创建API Gateway
        api = apigw.LambdaRestApi(
            self, "API",
            handler=lambda_fn,
            proxy=True,
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=["*"],
                allow_methods=["*"]
            )
        )

app = App()
BedrockMinutesStack(app, "BedrockMinutesStack")
app.synth()
```

**4. 部署脚本**
```bash
# scripts/deploy_aws.sh
#!/bin/bash

# 安装CDK依赖
cd infrastructure/cdk
pip install -r requirements.txt

# 部署到AWS
cdk bootstrap  # 首次部署
cdk deploy

# 获取API Gateway URL
cdk output
```

#### 部署流程

```bash
# 1. 安装mangum
pip install mangum==0.17.0

# 2. 创建Lambda handler
cat > lambda_handler.py << 'EOF'
from mangum import Mangum
from src.api.main import app
handler = Mangum(app, lifespan="off")
EOF

# 3. 部署CDK
cd infrastructure/cdk
cdk deploy

# 4. 获取API URL
# 输出: https://xxxxx.execute-api.us-east-1.amazonaws.com/prod/
```

### 方案2: Docker + ECS (容器化)

#### 需要添加的代码

**1. Dockerfile**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY src/ ./src/
COPY prompts/ ./prompts/

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**2. docker-compose.yml** (本地测试)
```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AWS_REGION=us-east-1
      - S3_BUCKET_NAME=meeting-minutes-dev
      - BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
    env_file:
      - .env
    volumes:
      - ./src:/app/src
      - ./prompts:/app/prompts
```

**3. ECS部署 (CDK)**
```python
# infrastructure/cdk/ecs_stack.py
from aws_cdk import (
    aws_ecs as ecs,
    aws_ecs_patterns as ecs_patterns,
    aws_ecr_assets as ecr_assets
)

# 创建Fargate服务
ecs_patterns.ApplicationLoadBalancedFargateService(
    self, "Service",
    task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
        image=ecs.ContainerImage.from_asset("../.."),
        container_port=8000,
        environment={...}
    ),
    public_load_balancer=True
)
```

### 方案3: EC2 + Nginx (传统部署)

#### 需要添加的代码

**1. systemd服务文件**
```bash
# /etc/systemd/system/bedrock-minutes.service
[Unit]
Description=AWS Bedrock Minutes API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/bedrock-minutes
Environment="PATH=/opt/bedrock-minutes/venv/bin"
EnvironmentFile=/opt/bedrock-minutes/.env
ExecStart=/opt/bedrock-minutes/venv/bin/uvicorn src.api.main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**2. Nginx反向代理**
```nginx
# /etc/nginx/sites-available/bedrock-minutes
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**3. 部署脚本**
```bash
# scripts/deploy_ec2.sh
#!/bin/bash

# 1. 克隆代码
git clone <repo> /opt/bedrock-minutes

# 2. 安装依赖
cd /opt/bedrock-minutes
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env

# 4. 初始化数据
python -m src.cli.init_defaults

# 5. 配置systemd
sudo cp bedrock-minutes.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable bedrock-minutes
sudo systemctl start bedrock-minutes

# 6. 配置Nginx
sudo cp nginx.conf /etc/nginx/sites-available/bedrock-minutes
sudo ln -s /etc/nginx/sites-available/bedrock-minutes /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🚀 当前可用的运行方式

### 方式1: 本地开发模式 (已实现 ✅)

```bash
# 工作目录
cd /Users/umatoratatsu/Documents/AWS/AWS-Handson/AWS-Bedrock-Mintues

# 激活虚拟环境
source venv/bin/activate  # 或 .venv/bin/activate

# 配置AWS凭证
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-east-1

# 创建S3 bucket (首次)
aws s3 mb s3://meeting-minutes-dev

# 配置环境变量
cp .env.example .env
# 编辑.env

# 初始化默认模板
python -m src.cli.init_defaults

# 启动API服务器
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# 访问
# - API文档: http://localhost:8000/docs
# - ReDoc: http://localhost:8000/redoc
# - 健康检查: http://localhost:8000/health
```

**架构**:
```
你的电脑 (localhost:8000)
    ↓
  FastAPI应用
    ↓
  boto3 (通过Internet)
    ↓
  AWS云服务 (S3, Bedrock, Transcribe)
```

### 方式2: Docker本地运行 (需要实现)

**缺失**: Dockerfile, docker-compose.yml

**实现后**:
```bash
docker-compose up
# 访问 http://localhost:8000
```

### 方式3: AWS Lambda部署 (需要实现)

**缺失**: 
- lambda_handler.py
- mangum包
- CloudFormation/CDK代码
- 部署脚本

---

## 📋 部署实现清单

### 已实现 ✅
- [x] FastAPI应用代码
- [x] 本地开发环境配置
- [x] .env.example环境变量模板
- [x] CLI初始化工具

### 未实现 ❌ (需要新增)

#### Lambda部署所需
- [ ] lambda_handler.py (Lambda入口点)
- [ ] mangum依赖 (FastAPI→Lambda适配器)
- [ ] infrastructure/cdk/ (IaC代码)
- [ ] scripts/deploy_lambda.sh (部署脚本)
- [ ] .github/workflows/deploy.yml (CI/CD)

#### Docker部署所需
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] .dockerignore
- [ ] scripts/build_docker.sh

#### EC2部署所需
- [ ] systemd服务文件
- [ ] nginx配置文件
- [ ] scripts/deploy_ec2.sh
- [ ] 健康检查脚本

---

## 🎯 API Gateway的真相

### 误区 ❌

> "本地需要构建API Gateway"

### 真相 ✅

**本地开发**: 
- 不需要API Gateway
- uvicorn就是HTTP服务器
- FastAPI处理路由和请求

**AWS部署**:
- API Gateway是**AWS托管服务**
- 通过CDK/CloudFormation**创建**(非构建)
- 代码示例:
  ```python
  # AWS CDK代码 (在AWS云端创建资源)
  api = apigw.LambdaRestApi(
      self, "API",
      handler=lambda_fn,
      proxy=True
  )
  ```

### API Gateway的作用 (仅AWS部署时)

```
客户端请求
    ↓
API Gateway (AWS托管)
    ├─ 路由: /api/v1/meetings → Lambda
    ├─ 认证: API Key/IAM (可选)
    ├─ 限流: 1000 req/s (可配置)
    ├─ 缓存: 响应缓存 (可选)
    └─ 监控: CloudWatch集成
    ↓
Lambda函数 (你的FastAPI代码)
    ↓
业务逻辑
```

---

## 🔧 快速实现AWS部署

如果需要部署到AWS，最快的方案：

### 最小步骤 (约30分钟)

**步骤1**: 添加Lambda handler
```bash
cat > lambda_handler.py << 'EOF'
from mangum import Mangum
from src.api.main import app
handler = Mangum(app, lifespan="off")
EOF
```

**步骤2**: 安装mangum
```bash
echo "mangum==0.17.0" >> requirements.txt
pip install mangum==0.17.0
```

**步骤3**: 打包部署
```bash
# 创建部署包
pip install -r requirements.txt -t package/
cp -r src package/
cp -r prompts package/
cp lambda_handler.py package/
cd package && zip -r ../lambda.zip . && cd ..

# 创建Lambda函数
aws lambda create-function \
  --function-name bedrock-minutes \
  --runtime python3.11 \
  --handler lambda_handler.handler \
  --zip-file fileb://lambda.zip \
  --role arn:aws:iam::YOUR_ACCOUNT:role/lambda-exec-role \
  --timeout 900 \
  --memory-size 1024 \
  --environment Variables="{S3_BUCKET_NAME=your-bucket,BEDROCK_MODEL_ID=amazon.nova-pro-v1:0}"

# 创建API Gateway
aws apigatewayv2 create-api \
  --name bedrock-minutes-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:us-east-1:YOUR_ACCOUNT:function:bedrock-minutes
```

**步骤4**: 获取API URL
```bash
aws apigatewayv2 get-apis --query 'Items[?Name==`bedrock-minutes-api`].ApiEndpoint'
# 输出: https://xxxxx.execute-api.us-east-1.amazonaws.com
```

---

## 总结

### 当前状态

| 环境 | 状态 | 说明 |
|------|------|------|
| **本地开发** | ✅ 完全可用 | uvicorn直接运行,访问localhost:8000 |
| **Docker本地** | ❌ 未实现 | 需要Dockerfile |
| **AWS Lambda** | ❌ 未实现 | 需要handler+CDK+mangum |
| **EC2部署** | ❌ 未实现 | 需要systemd+nginx+脚本 |

### 核心理解

1. **本地开发不需要API Gateway** - uvicorn就是HTTP服务器
2. **API Gateway是AWS云服务** - 部署到AWS时才需要
3. **当前可用** - 本地开发环境完全就绪
4. **生产部署** - 需要额外30分钟-5小时的基础设施代码

### 是否需要AWS部署？

**如果只是开发/测试**: 当前本地环境完全够用
**如果需要生产环境**: 我可以帮您实现Lambda+API Gateway部署方案

