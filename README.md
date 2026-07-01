# Java Service Manager

通过 Web 界面远程管理多台服务器上的 Java 服务。

## 功能

- **服务器管理** — 添加/编辑/删除服务器,支持密码和 SSH 密钥认证,敏感信息加密存储
- **服务管理** — 扫描服务目录自动发现服务,支持 systemctl 和自定义脚本的启停/重启/状态查看
- **配置文件管理** — 远程查看和编辑 YAML/XML 配置文件,编辑前自动备份并校验语法
- **JAR 包管理** — 上传和删除服务的 JAR 依赖包,替换前自动备份
- **操作日志** — 记录所有操作历史,便于审计

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | FastAPI + SQLAlchemy 2.0 (异步) + Paramiko SSH |
| 前端 | Vue 3 + Vite + Pinia + Vue Router |
| 数据库 | SQLite (aiosqlite) |
| 部署 | Docker / Docker Compose |

## 快速开始

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

前端默认运行在 `http://localhost:5173`,后端 API 在 `http://localhost:8000`。

### Docker 部署

```bash
docker compose up -d
```

## 项目结构

```
├── backend/
│   └── app/
│       ├── main.py           # FastAPI 应用入口
│       ├── config.py         # 配置管理
│       ├── database.py       # 数据库连接
│       ├── models/           # 数据模型 (Server, Service, OperationLog)
│       ├── routers/          # API 路由
│       ├── schemas/          # 请求/响应模型
│       ├── services/         # 业务逻辑 (SSH 操作)
│       └── utils/            # 工具 (SSH 客户端,加密,错误处理)
├── frontend/
│   └── src/
│       ├── api/              # 后端 API 调用
│       ├── views/            # 页面组件
│       ├── stores/           # Pinia 状态管理
│       └── router/           # 路由配置
├── docker-compose.yml
└── Dockerfile
```

## API 概览

| 端点 | 说明 |
|------|------|
| `GET/POST /api/servers` | 服务器列表/创建 |
| `PUT/DELETE /api/servers/{id}` | 更新/删除服务器 |
| `POST /api/servers/{id}/test-connection` | 测试 SSH 连接 |
| `GET/POST /api/servers/{id}/services` | 服务列表/创建 |
| `POST /api/servers/{id}/services/scan` | 扫描发现服务 |
| `POST /api/services/{id}/start\|stop\|restart` | 服务启停 |
| `GET/PUT /api/services/{id}/configs/{file}` | 配置文件读写 |
| `POST/DELETE /api/services/{id}/jars/{file}` | JAR 包上传/删除 |
