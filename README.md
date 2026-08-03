
# Open Note -  Server

跨设备同步的便签应用后端服务，支持桌面端和移动端共用同一入口，根据 User-Agent 自动分发对应前端资源。

## 架构

```
SQLite (主存储)           txt 文件 (冷备)
     │                        │
notes.db              backup/<user>/n_<id>.txt
     │                        │
     └──────── 实时双向 ───────┘
              每写一条笔记自动同步备份
```

- **SQLite** 做主存，支持索引查询、分页、增量同步
- **txt 文件** 做冷备，每条笔记独立一个文件，单条损坏不影响其余数据
- **UA 检测** 中间件自动识别设备类型，桌面端和移动端共用同一 URL

## 项目结构

```
open-note-server/
├── server.py                  # 入口
├── config.py                  # 配置常量
├── app/
│   ├── __init__.py            # App 工厂、health 路由
│   ├── database.py            # SQLite 连接、会话管理、工具函数
│   ├── auth.py                # 认证路由
│   ├── notebooks.py           # 笔记本 CRUD
│   ├── notes.py               # 笔记 CRUD + 增量同步 + 回收站
│   ├── settings.py            # 分享设置
│   ├── backup.py              # txt 冷备模块
│   └── frontend.py            # UA 检测 + 双端静态资源分发
├── scripts/
│   ├── deploy.ps1             # 一键部署（Windows）
│   └── restore.py             # 冷备恢复工具
├── static/
│   ├── desktop/               # 桌面端前端构建产物
│   └── mobile/                # 移动端前端构建产物
├── data/
│   ├── accounts.db            # 用户表
│   └── notes.db               # 笔记 + 笔记本 + 分享设置
└── backup/                    # 冷备目录
    └── <username>/
        └── n_<id>.txt
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+（构建前端时需要）

### 1. 克隆项目

```bash
git clone https://github.com/3588044667HZ/open-note-server.git
cd open-note-server
```

### 2. 安装 Python 依赖

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 启动开发服务器

```bash
python server.py
```

服务运行在 `http://localhost:5000`。开发模式下仅提供 API 服务，前端由各自的 Vite dev server 独立运行。

## 部署教程

部署时需要将两端前端构建产物放入 `static/` 目录，使服务器能根据设备类型分发对应页面。

### 方式一：一键部署（Windows PowerShell）

```powershell
# 修改 scripts/deploy.ps1 中的前端项目路径为实际路径
# 然后运行：
.\scripts\deploy.ps1
```

### 方式二：手动部署

#### 1. 克隆并构建桌面端前端

```bash
git clone https://github.com/3588044667HZ/open-note-frontend.git
cd open-note-frontend
npm install
npm run build
```

构建产物在 `dist/` 目录。

#### 2. 克隆并构建移动端前端

```bash
git clone https://github.com/3588044667HZ/open-note-mobile.git
cd open-note-mobile
npm install
npm run build
```

构建产物在 `dist/` 目录。

#### 3. 复制构建产物

```bash
# 将桌面端 dist/ 复制到 mock-server/static/desktop/
cp -r open-note-frontend/dist/* open-note-server/static/desktop/

# 将移动端 dist/ 复制到 mock-server/static/mobile/
cp -r open-note-mobile/dist/* open-note-server/static/mobile/
```

#### 4. 安装依赖并启动

```bash
cd open-note-server
pip install -r requirements.txt
```

**开发模式：**

```bash
python server.py
```

**生产模式（使用 waitress）：**

```bash
python -c "from app import create_app; from waitress import serve; app=create_app(); serve(app, host='0.0.0.0', port=5000)"
```

#### 5. 访问

- 桌面浏览器访问 `http://<服务器IP>:5000` → 自动返回桌面端页面
- 手机浏览器访问同一地址 → 自动返回移动端页面
- 或直接访问 `http://<服务器IP>:5000/api/health` 检查服务状态

### 支持跨设备访问

服务监听 `0.0.0.0:5000`，同一局域网内的设备均可访问。启动时会打印局域网 IP：

```
 * Local:    http://127.0.0.1:5000
 * Network:  http://192.168.1.100:5000
 * API base: http://192.168.1.100:5000/api/
```

## 冷备恢复

如果 SQLite 数据库损坏，可以从 txt 备份恢复：

```bash
python scripts/restore.py
```

恢复逻辑：遍历 `backup/` 下所有用户的 `.txt` 文件，逐条写入 `notes.db`。

## API 文档

详见 [API.md](./API.md)

| 模块 | 端点 |
|------|------|
| 认证 | `POST /api/auth/register`, `/login`, `/refresh`, `GET /me`, `POST /logout` |
| 笔记本 | `GET/POST /api/notebooks`, `PUT/DELETE /api/notebooks/:id` |
| 笔记 | `GET/POST /api/notes`, `GET/PUT/DELETE /api/notes/:id` |
| 同步 | `GET /api/notes/sync?since=` |
| 回收站 | `GET /api/notes/trash`, `PUT /api/notes/:id/recover`, `DELETE /api/notes/:id/permanent` |
| 固定 | `PUT /api/notes/:id/pin` |
| 分享设置 | `GET/PUT /api/settings/share` |
| 健康检查 | `GET /api/health` |

所有笔记/笔记本接口需要 `Authorization: Bearer <token>` 认证头。

### 核心特性

- **分页**: `?page=1&size=20`，置顶笔记优先排序
- **增量同步**: `GET /api/notes/sync?since=<timestamp>` 仅返回变更数据
- **乐观锁**: `If-Match: <updatedAt>` 头防止并发编辑冲突（409）
- **版本号**: 每次写操作 `version` 自增，支持离线合并
- **Token 自动续期**: 401 时自动调用 `/auth/refresh`

## 前端项目

| 平台 | 仓库 |
|------|------|
| 桌面端 (Web) | [open-note-frontend](https://github.com/3588044667HZ/open-note-frontend) |
| 移动端 (Web) | [open-note-mobile](https://github.com/3588044667HZ/open-note-mobile) |

两端均基于 Vue 3 + Vite 构建，API 基路径为 `/api`，部署时无需修改前端代码。

## 技术栈

- **Web 框架**: Flask 3.x
- **数据库**: SQLite（WAL 模式）
- **生产服务器**: Waitress
- **跨域**: Flask-CORS
