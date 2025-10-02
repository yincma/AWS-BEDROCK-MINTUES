# AWS Bedrock Minutes - Frontend

基于 Vue 3 + Vite + Tailwind CSS 的现代化前端界面。

## 技术栈

- **框架**: Vue 3 (Composition API)
- **构建工具**: Vite
- **UI 框架**: Tailwind CSS
- **路由**: Vue Router 4
- **HTTP 客户端**: Axios
- **Markdown 渲染**: markdown-it

## 快速开始

### 安装依赖
```bash
cd frontend
npm install
```

### 开发模式
```bash
npm run dev
```
访问 http://localhost:5173

### 生产构建
```bash
npm run build
```

## 功能特性

- ✅ 文字/音频输入创建会议
- ✅ 实时进度追踪（三阶段可视化）
- ✅ 审查反馈提交
- ✅ Draft/Final 版本对比
- ✅ Markdown 下载和复制

## 环境变量

创建 `.env` 文件：
```env
VITE_API_BASE_URL=http://localhost:8000
```

## 项目结构

```
frontend/
├── src/
│   ├── api/              # API 调用
│   ├── views/            # 页面组件
│   ├── router/           # 路由配置
│   └── style.css         # Tailwind 样式
├── .env                  # 环境变量
└── package.json
```

详细文档请参考项目主 README。
