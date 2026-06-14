# Meme Tagger Web - Code Wiki

## 目录

- [项目概述](#项目概述)
- [技术架构](#技术架构)
- [目录结构](#目录结构)
- [核心模块详解](#核心模块详解)
- [数据模型](#数据模型)
- [API 接口文档](#api-接口文档)
- [前端架构](#前端架构)
- [运行指南](#运行指南)
- [配置说明](#配置说明)
- [依赖关系](#依赖关系)

---

## 项目概述

**Meme Tagger Web** 是一个基于 Flask 的表情包 AI 自动标签生成工具。用户可以扫描本地图片目录，系统会通过大语言模型（LLM）API 对表情包进行视觉分析，自动生成分类标签并存储到 SQLite 数据库中。

### 核心功能

-  **目录扫描**：递归扫描指定目录，识别符合白名单的图片文件
-  **AI 标签生成**：调用 LLM API 分析图片内容，自动生成 3-8 个标签（包含置信度）
-  **异步任务处理**：使用线程池并发处理图片，支持实时进度推送（SSE）
-  **数据持久化**：SQLite 数据库存储图片元数据和标签信息
-  **现代化 UI**：深色主题单页应用，支持图片预览、筛选、搜索、批量操作
-  **数据导出**：一键导出 SQLite 数据库文件

### 使用场景

- 表情包收藏管理和分类
- 图片资源的自动化标签标注
- 本地图片库的元数据管理

---

## 技术架构

### 后端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Flask** | ≥3.0, <4.0 | Web 框架 |
| **Flask-SQLAlchemy** | ≥3.1, <4.0 | ORM 数据库操作 |
| **httpx** | ≥0.27, <1.0 | HTTP 客户端（调用 LLM API） |
| **SQLite** | - | 轻量级关系型数据库 |

### 前端技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| **Bootstrap** | 5.3.3 | UI 组件库 |
| **原生 JavaScript** | ES6+ | 交互逻辑 |
| **Server-Sent Events (SSE)** | - | 实时进度推送 |

### AI 服务

- **LLM API**：Open AI 兼容模式
- **视觉分析**：通过 Chat Completions API 发送 Base64 编码图片，获取结构化 JSON 标签

### 架构模式

```
┌─────────────────────────────────────────────────────────┐
│                      前端 SPA                           │
│  (Bootstrap + JavaScript + SSE Client)                 │
└────────────────┬────────────────────────────────────────┘
                 │ HTTP / SSE
┌────────────────▼────────────────────────────────────────┐
│                   Flask 应用层                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Main Route  │  │  API Routes  │  │ Export Route │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                   业务服务层                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ File Service │  │  AI Service  │  │  DB Service  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└────────────────┬────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────┐
│                   数据持久层                            │
│  ┌──────────────┐  ┌──────────────┐                    │
│  │   SQLite DB  │  │ Task Manager │                    │
│  └──────────────┘  └──────────────┘                    │
└─────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
meme_tagger For Web/
├── run.py                      # 应用入口文件，启动 Flask 开发服务器
├── config.py                   # 应用配置类，集中管理所有配置项
├── requirements.txt            # Python 依赖列表
├── .gitignore                  # Git 忽略规则
│
├── app/                        # 主应用目录
│   ├── __init__.py            # 应用工厂函数，创建并配置 Flask 实例
│   ├── models.py              # 数据库模型定义（Meme, Tag）
│   │
│   ├── routes/                # 路由蓝图模块
│   │   ├── __init__.py
│   │   ├── main.py           # 主页面路由（渲染 index.html）
│   │   ├── api.py            # RESTful API 接口（扫描、打标签、查询、删除等）
│   │   └── export.py         # 数据库导出功能
│   │
│   ├── services/              # 业务服务层
│   │   ├── __init__.py
│   │   ├── file_service.py   # 文件工具服务（扫描图片、计算 MD5）
│   │   ├── ai_service.py     # AI 标签分析服务（调用 LLM API）
│   │   └── db_service.py     # 数据库操作服务（CRUD、统计查询）
│   │
│   ├── tasks/                 # 后台任务模块
│   │   ├── __init__.py
│   │   └── worker.py         # 任务管理器（线程池、进度推送）
│   │
│   ├── templates/             # HTML 模板
│   │   └── index.html        # 单页应用主页面
│   │
│   └── static/                # 静态资源
│       ├── css/
│       │   └── app.css       # 应用样式表（深色主题）
│       └── js/
│           └── app.js        # 前端主脚本（交互逻辑）
│
└── instance/                  # 运行时数据目录（自动创建）
    └── meme_tagger.db        # SQLite 数据库文件
```

---

## 核心模块详解

### 1. 应用工厂 (`app/__init__.py`)

**职责**：创建并配置 Flask 应用实例

**核心函数**：

```python
def create_app(config_class=Config) -> Flask
```

**工作流程**：
1. 创建 Flask 应用实例并加载配置
2. 确保数据库目录存在
3. 初始化 SQLAlchemy 数据库扩展
4. 注册三个蓝图：`main_bp`、`api_bp`、`export_bp`
5. 在应用上下文中创建数据库表（如果不存在）
6. 返回配置完成的应用实例

---

### 2. 配置管理 (`config.py`)

**职责**：集中管理所有应用配置项

**配置类**：`Config`

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `SECRET_KEY` | str | `"dev-secret-key-change-in-production"` | Flask session 加密密钥 |
| `SQLALCHEMY_DATABASE_URI` | str | `sqlite:///instance/meme_tagger.db` | 数据库连接 URI |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | bool | `False` | 关闭 SQLAlchemy 事件追踪 |
| `LLM_API_KEY` | str | `"sk-your-api-key"` | LLM API 密钥 |
| `LLM_API_BASE` | str | `"https://api.openai.com/v1"` | LLM API 基础 URL |
| `LLM_MODEL` | str | `"gpt-4o"` | 使用的 LLM 模型名称 |
| `MAX_WORKERS` | int | `3` | 并发处理线程数 |
| `ALLOWED_EXTENSIONS` | set | `{".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}` | 允许的图片扩展名 |

**环境变量支持**：所有配置项均可通过同名环境变量覆盖

---

### 3. 数据模型 (`app/models.py`)

**职责**：定义数据库表结构和 ORM 模型

#### 3.1 Meme 模型

**表名**：`memes`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | 主键 | 自增 ID |
| `file_path` | String(1024) | 唯一索引 | 文件绝对路径 |
| `file_name` | String(512) | 非空 | 原始文件名 |
| `md5_hash` | String(32) | 非空 | 文件 MD5 哈希值 |
| `status` | String(20) | 非空，默认 `"pending"`，索引 | 处理状态 |
| `error_message` | Text | 可空 | 错误信息 |
| `created_at` | DateTime | 默认 UTC 当前时间 | 创建时间 |
| `updated_at` | DateTime | 自动更新 | 最后更新时间 |

**关系**：一对多关联 `Tag` 模型（`cascade="all, delete-orphan"`）

**状态枚举**：
- `pending`：待处理
- `processing`：处理中
- `completed`：已完成
- `error`：错误

**序列化方法**：`to_dict()` → 返回包含所有字段和关联标签的字典

#### 3.2 Tag 模型

**表名**：`tags`

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | Integer | 主键 | 自增 ID |
| `name` | String(256) | 非空 | 标签名称 |
| `confidence` | Float | 非空，默认 `0.0` | 置信度（0.0-1.0） |
| `meme_id` | Integer | 外键，非空 | 关联的 Meme ID |

**关系**：多对一反向关联 `Meme` 模型

**序列化方法**：`to_dict()` → 返回标签信息的字典

---

### 4. 路由蓝图

#### 4.1 主页面路由 (`app/routes/main.py`)

**蓝图名称**：`main`  
**URL 前缀**：无

| 路由 | 方法 | 函数 | 说明 |
|------|------|------|------|
| `/` | GET | `index()` | 渲染前端单页应用主页 |

---

#### 4.2 API 接口路由 (`app/routes/api.py`)

**蓝图名称**：`api`  
**URL 前缀**：`/api`

##### 4.2.1 扫描目录

**端点**：`POST /api/scan`

**请求体**：
```json
{
  "directory": "C:\\Users\\me\\Pictures\\memes"
}
```

**响应**：
```json
{
  "directory": "C:\\Users\\me\\Pictures\\memes",
  "count": 42,
  "files": [
    "C:\\Users\\me\\Pictures\\memes\\funny_cat.jpg",
    "C:\\Users\\me\\Pictures\\memes\\doge.png"
  ]
}
```

**错误码**：
- `400`：目录路径为空
- `404`：目录不存在

---

##### 4.2.2 启动打标签任务

**端点**：`POST /api/tag`

**请求体**：
```json
{
  "files": [
    "C:\\Users\\me\\Pictures\\memes\\funny_cat.jpg",
    "C:\\Users\\me\\Pictures\\memes\\doge.png"
  ]
}
```

**响应**：
```json
{
  "task_id": "a1b2c3d4e5f6",
  "total": 2
}
```

**错误码**：
- `400`：文件列表为空或无有效文件

---

##### 4.2.3 SSE 进度推送

**端点**：`GET /api/progress_stream/<task_id>`

**响应类型**：`text/event-stream`

**事件数据示例**：
```json
{
  "task_id": "a1b2c3d4e5f6",
  "status": "running",
  "total": 10,
  "completed": 3,
  "current_file": "C:\\Users\\me\\Pictures\\memes\\cat.jpg",
  "errors": [],
  "created_at": 1718345678.123
}
```

**特殊事件**：
- `{"type": "heartbeat"}`：心跳包（30秒无数据时发送）
- `null`：任务结束信号

**错误码**：
- `404`：任务不存在
- `400`：任务流不可用

---

##### 4.2.4 查询图片列表

**端点**：`GET /api/memes`

**查询参数**：
- `page`：页码（默认 1）
- `per_page`：每页数量（默认 20）
- `status`：状态筛选（可选）
- `search`：关键词搜索（可选，匹配文件名或标签名）

**响应**：
```json
{
  "memes": [
    {
      "id": 1,
      "file_path": "C:\\memes\\cat.jpg",
      "file_name": "cat.jpg",
      "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
      "status": "completed",
      "error_message": null,
      "tags": [
        {"id": 1, "name": "搞笑", "confidence": 0.95, "meme_id": 1},
        {"id": 2, "name": "猫咪", "confidence": 0.88, "meme_id": 1}
      ],
      "created_at": "2026-06-14T10:30:00",
      "updated_at": "2026-06-14T10:31:00"
    }
  ],
  "total": 100,
  "page": 1,
  "per_page": 20,
  "pages": 5
}
```

---

##### 4.2.5 删除图片

**端点**：`DELETE /api/memes/<meme_id>`

**响应**：
```json
{
  "message": "Meme deleted"
}
```

**错误码**：
- `404`：图片不存在

---

##### 4.2.6 获取统计数据

**端点**：`GET /api/stats`

**响应**：
```json
{
  "pending": 5,
  "processing": 2,
  "completed": 90,
  "error": 3
}
```

---

##### 4.2.7 图片预览

**端点**：`GET /api/file_preview`

**查询参数**：
- `path`：图片文件绝对路径

**响应**：图片二进制数据（`Content-Type` 自动推断）

**错误码**：
- `400`：路径参数缺失
- `404`：文件不存在

---

#### 4.3 导出路由 (`app/routes/export.py`)

**蓝图名称**：`export`  
**URL 前缀**：`/api`

##### 4.3.1 导出数据库

**端点**：`GET /api/export`

**响应**：SQLite 数据库文件（`application/octet-stream`）

**文件名**：`meme_tagger_export.db`

**工作流程**：
1. 以只读模式打开源数据库
2. 备份到临时文件
3. 发送临时文件给客户端
4. 请求完成后自动清理临时文件

**错误码**：
- `404`：数据库文件不存在
- `500`：导出失败

---

### 5. 业务服务层

#### 5.1 文件服务 (`app/services/file_service.py`)

##### 5.1.1 扫描图片文件

```python
def get_image_files(directory: str) -> list[Path]
```

**功能**：递归扫描目录，返回所有符合 `ALLOWED_EXTENSIONS` 白名单的图片文件路径

**参数**：
- `directory`：目录路径字符串

**返回**：排序后的 `Path` 对象列表

**特点**：
- 使用 `Path.rglob("*")` 递归扫描
- 扩展名匹配不区分大小写
- 返回结果已排序

---

##### 5.1.2 计算 MD5 哈希

```python
def compute_md5(file_path: Path) -> Optional[str]
```

**功能**：计算文件的 MD5 哈希值，用于去重校验

**参数**：
- `file_path`：文件 `Path` 对象

**返回**：32 位十六进制 MD5 字符串，读取失败返回 `None`

**特点**：
- 分块读取（8192 字节），支持大文件
- 异常处理：`OSError` 时返回 `None`

---

#### 5.2 AI 服务 (`app/services/ai_service.py`)

##### 5.2.1 核心函数：分析图片

```python
def analyze_image(file_path: Path) -> list[dict[str, Any]]
```

**功能**：调用 LLM API 分析图片并返回标签列表

**参数**：
- `file_path`：图片文件 `Path` 对象

**返回**：标签字典列表，格式为 `[{"name": "tag_name", "confidence": 0.95}, ...]`

**工作流程**：
1. 编码图片为 Base64
2. 构建 LLM API 请求体
3. 调用 API（最多重试 3 次）
4. 解析响应中的 JSON 标签
5. 校验并返回标签列表

**异常处理**：
- `RuntimeError`：`LLM_API_KEY` 未配置
- `httpx.TimeoutException`：API 超时
- `httpx.HTTPStatusError`：HTTP 错误
- `httpx.RequestError`：请求错误

---

##### 5.2.2 辅助函数

**编码图片**：
```python
def _encode_image(file_path: Path) -> str
```
将图片文件读取并编码为 Base64 字符串

---

**构建请求体**：
```python
def _build_payload(image_base64: str, file_name: str) -> dict[str, Any]
```
构建 LLM Chat Completions API 请求体，包含系统提示词和图片数据

**系统提示词**：
```
你是一个表情包分类专家。分析给定的图片并识别表情包特征。
只返回符合以下结构的有效 JSON 对象：
{
  "tags": [
    {"name": "tag_name", "confidence": 0.95}
  ]
}
包含 3-8 个标签，涵盖：表情包格式/模板名称、情绪、风格、主题以及如果可见的文字内容。
置信度必须是介于 0.0 和 1.0 之间的浮点数。
```

---

**推断 MIME 类型**：
```python
def _guess_mime(file_name: str) -> str
```
根据文件扩展名推断 MIME 类型子类型（如 `jpeg`、`png`、`gif`）

---

**解析响应**：
```python
def _parse_response(text: str) -> list[dict[str, Any]]
```
从 LLM 返回的文本中提取 JSON 对象，解析出标签列表并校验格式

**特点**：
- 使用正则表达式提取 JSON 对象
- 校验置信度范围（0.0-1.0）
- 过滤空标签名

---

#### 5.3 数据库服务 (`app/services/db_service.py`)

##### 5.3.1 获取或创建 Meme

```python
def get_or_create_meme(file_path: Path, md5_hash: str) -> Meme
```

**功能**：根据文件路径查找已有 Meme 记录，不存在则创建新的 `pending` 状态记录

**参数**：
- `file_path`：文件路径
- `md5_hash`：文件 MD5 哈希值

**返回**：`Meme` 模型实例

---

##### 5.3.2 更新 Meme 状态

```python
def update_meme_status(
    meme_id: int, status: str, error_message: Optional[str] = None
) -> None
```

**功能**：更新指定 Meme 的处理状态，可选附带错误信息

**参数**：
- `meme_id`：Meme ID
- `status`：新状态（`pending`/`processing`/`completed`/`error`）
- `error_message`：错误信息（可选）

---

##### 5.3.3 添加标签

```python
def add_tags_to_meme(meme_id: int, tags: list[dict[str, Any]]) -> None
```

**功能**：为指定 Meme 批量写入标签（先清除旧标签再写入新标签，实现覆盖更新）

**参数**：
- `meme_id`：Meme ID
- `tags`：标签字典列表，格式为 `[{"name": "tag_name", "confidence": 0.95}, ...]`

---

##### 5.3.4 分页查询

```python
def get_all_memes(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]
```

**功能**：分页查询 Meme 列表，支持按状态筛选和文件名/标签名模糊搜索

**参数**：
- `page`：页码（默认 1）
- `per_page`：每页数量（默认 20）
- `status_filter`：状态筛选（可选）
- `search`：关键词搜索（可选，匹配文件名或标签名）

**返回**：包含分页信息的字典：
```python
{
    "memes": [...],  # Meme 对象列表
    "total": 100,    # 总记录数
    "page": 1,       # 当前页码
    "per_page": 20,  # 每页数量
    "pages": 5       # 总页数
}
```

**排序**：按 `updated_at` 降序

---

##### 5.3.5 删除 Meme

```python
def delete_meme(meme_id: int) -> bool
```

**功能**：删除指定 Meme 记录及其关联的 Tag 记录（级联删除）

**参数**：
- `meme_id`：Meme ID

**返回**：是否删除成功

---

##### 5.3.6 状态统计

```python
def get_meme_count_by_status() -> dict[str, int]
```

**功能**：按处理状态分组统计 Meme 数量

**返回**：`{status: count}` 字典，例如：
```python
{
    "pending": 5,
    "processing": 2,
    "completed": 90,
    "error": 3
}
```

---

### 6. 后台任务管理 (`app/tasks/worker.py`)

**职责**：管理后台打标签任务的生命周期，支持并发处理和实时进度推送

#### 6.1 TaskStatus 常量类

```python
class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
```

---

#### 6.2 TaskManager 类

**核心属性**：
- `_executor`：`ThreadPoolExecutor` 线程池（`max_workers=Config.MAX_WORKERS`）
- `_tasks`：所有任务的状态数据字典
- `_lock`：`threading.Lock` 保护共享状态的并发访问
- `_progress_queues`：每个任务的进度消息队列

---

##### 6.2.1 创建任务

```python
def create_task(self, file_paths: list[Path], app: Flask) -> str
```

**功能**：创建新的打标签任务，提交到线程池执行

**参数**：
- `file_paths`：文件路径列表
- `app`：Flask 应用实例（用于在子线程中访问应用上下文）

**返回**：任务 ID（12 位 UUID 十六进制字符串）

**工作流程**：
1. 生成任务 ID
2. 初始化任务状态数据
3. 创建进度消息队列
4. 提交任务到线程池
5. 返回任务 ID

---

##### 6.2.2 任务执行主体

```python
def _run_task(self, task_id: str, file_paths: list[Path], app: Flask) -> None
```

**功能**：遍历文件列表，逐个调用 AI 分析并保存结果

**工作流程**：
1. 更新任务状态为 `RUNNING`
2. 推送初始进度
3. 遍历文件列表：
   - 更新当前处理文件
   - 推送进度
   - 调用 `_process_single_file` 处理单个文件
   - 捕获异常并记录到错误列表
   - 更新已完成计数
   - 推送进度
4. 更新任务状态为 `COMPLETED`
5. 推送最终进度
6. 推送结束信号

---

##### 6.2.3 处理单个文件

```python
def _process_single_file(self, file_path: Path, task_id: str, app: Flask) -> None
```

**功能**：处理单个文件的完整流程

**工作流程**：
1. 计算文件 MD5 哈希值
2. 在应用上下文中：
   - 获取或创建 Meme 记录
   - 更新状态为 `processing`
3. 调用 `analyze_image` 进行 AI 分析
4. 在应用上下文中：
   - 添加标签到 Meme
   - 更新状态为 `completed`
5. 异常处理：更新状态为 `error` 并记录错误信息

**事务管理**：
- 使用 `db.session.commit()` 提交事务
- 异常时调用 `db.session.rollback()` 回滚

---

##### 6.2.4 进度推送

```python
def _push_progress(self, task_id: str, task_data: dict[str, Any]) -> None
```

**功能**：将任务进度数据推送到对应的 SSE 消息队列

**数据结构**：
```python
{
    "task_id": "a1b2c3d4e5f6",
    "status": "running",
    "total": 10,
    "completed": 3,
    "current_file": "C:\\memes\\cat.jpg",
    "errors": [],
    "created_at": 1718345678.123
}
```

---

```python
def _push_done(self, task_id: str) -> None
```

**功能**：向队列推送 `None` 信号，通知 SSE 客户端任务已结束

---

##### 6.2.5 任务状态查询

```python
def get_task_status(self, task_id: str) -> dict[str, Any] | None
```

**功能**：获取指定任务的当前状态快照（线程安全）

**返回**：任务状态字典，不存在返回 `None`

---

##### 6.2.6 进度订阅管理

```python
def subscribe_progress(self, task_id: str) -> queue.Queue[dict[str, Any]] | None
```

**功能**：订阅指定任务的进度消息队列，供 SSE 端点消费

**返回**：进度消息队列，不存在返回 `None`

---

```python
def unsubscribe_progress(self, task_id: str) -> None
```

**功能**：取消订阅进度队列，SSE 连接断开时调用

---

##### 6.2.7 关闭任务管理器

```python
def shutdown(self) -> None
```

**功能**：关闭线程池，等待所有正在执行的任务完成

---

#### 6.3 全局单例

```python
task_manager = TaskManager()
```

**用途**：供路由模块导入使用，管理所有后台任务

---

## 数据模型

### 数据库表结构

#### memes 表

```sql
CREATE TABLE memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path VARCHAR(1024) UNIQUE NOT NULL,
    file_name VARCHAR(512) NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_memes_file_path ON memes (file_path);
CREATE INDEX ix_memes_status ON memes (status);
```

#### tags 表

```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(256) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    meme_id INTEGER NOT NULL,
    FOREIGN KEY (meme_id) REFERENCES memes (id) ON DELETE CASCADE
);
```

### 关系图

```
┌─────────────────┐
│     memes       │
├─────────────────┤
│ id (PK)         │
│ file_path       │◄───────┐
│ file_name       │        │
│ md5_hash        │        │
│ status          │        │
│ error_message   │        │
│ created_at      │        │
│ updated_at      │        │
└─────────────────┘        │
                           │
                           │ 1:N
                           │
┌─────────────────┐        │
│     tags        │        │
├─────────────────┤        │
│ id (PK)         │        │
│ name            │        │
│ confidence      │        │
│ meme_id (FK)    │────────┘
└─────────────────┘
```

---

## 前端架构

### 单页应用结构

**入口文件**：`app/templates/index.html`

**主要区域**：
1. **顶部导航栏**：品牌名 + 统计摘要
2. **操作区**：目录输入、扫描、打标签、导出按钮
3. **统计栏**：各状态计数（总计、已完成、处理中、待处理、错误）
4. **进度区**：打标签任务实时进度条
5. **图片列表区**：卡片网格 + 筛选/搜索 + 批量删除
6. **分页导航**
7. **Toast 通知容器**
8. **回到顶部按钮**

---

### 核心 JavaScript 模块 (`app/static/js/app.js`)

#### 全局状态

```javascript
let scannedFiles = [];        // 当前扫描到的文件路径列表
let currentPage = 1;          // 图片列表当前页码
let activeEventSource = null; // 当前活跃的 SSE 连接实例
let selectedMemes = new Set(); // 批量删除选中的 meme ID 集合
let autoRefreshTimer = null;  // 自动刷新定时器 ID
```

---

#### 通用工具函数

##### Toast 通知

```javascript
function toast(message, type = "info", duration = 4000)
```

**功能**：显示 Toast 通知消息

**参数**：
- `message`：提示内容
- `type`：类型（`success`/`error`/`warning`/`info`）
- `duration`：显示时长（毫秒，默认 4000）

---

##### HTML 转义

```javascript
function escapeHtml(str)
```

**功能**：防止 XSS 注入

---

##### 防抖函数

```javascript
function debounce(fn, delay)
```

**功能**：延迟执行，避免高频触发（如搜索输入）

---

##### 确认对话框

```javascript
function showConfirm(title, message)
```

**功能**：显示确认对话框（替代原生 `confirm`）

**返回**：`Promise<boolean>`，用户确认返回 `true`，取消返回 `false`

---

##### Lightbox 预览

```javascript
function openLightbox(filePath)
```

**功能**：打开图片全屏预览

---

#### 核心业务功能

##### 扫描目录

```javascript
function scanDirectory()
```

**功能**：向后端发送目录路径，获取其中的图片文件列表

**工作流程**：
1. 获取目录输入框值
2. 发送 `POST /api/scan` 请求
3. 更新扫描结果显示
4. 存储文件列表到 `scannedFiles`
5. 启用"全部打标签"按钮
6. 刷新图片列表和统计

---

##### 启动打标签任务

```javascript
function startTagging()
```

**功能**：将扫描到的文件列表提交给后端，触发 AI 分析

**工作流程**：
1. 检查 `scannedFiles` 是否为空
2. 发送 `POST /api/tag` 请求
3. 获取任务 ID
4. 调用 `subscribeProgress` 订阅进度

---

##### SSE 进度订阅

```javascript
function subscribeProgress(taskId)
```

**功能**：建立 EventSource 连接，实时接收任务进度更新

**工作流程**：
1. 关闭现有 SSE 连接（如果有）
2. 显示进度区
3. 创建 `EventSource` 连接到 `/api/progress_stream/<taskId>`
4. 监听 `onmessage` 事件：
   - 解析 JSON 数据
   - 忽略心跳包
   - 更新进度 UI
   - 显示错误信息
   - 任务完成时关闭连接并刷新列表
5. 监听 `onerror` 事件：关闭连接并提示错误

---

##### 更新进度 UI

```javascript
function updateProgressUI(data)
```

**功能**：更新进度条、文本、当前文件显示

---

##### 导出数据库

```javascript
function exportDatabase()
```

**功能**：下载当前 SQLite 数据库文件

**工作流程**：
1. 发送 `GET /api/export` 请求
2. 获取 Blob 数据
3. 创建临时 URL
4. 触发下载
5. 清理临时 URL

---

##### 加载图片列表

```javascript
function loadMemes(page = 1)
```

**功能**：请求后端分页数据并渲染

**工作流程**：
1. 显示骨架屏加载占位符
2. 构建查询参数（页码、每页数量、状态筛选、搜索关键词）
3. 发送 `GET /api/memes` 请求
4. 调用 `renderMemes` 渲染图片卡片
5. 调用 `renderPagination` 渲染分页导航

---

##### 渲染图片卡片

```javascript
function renderMemes(memes)
```

**功能**：将 meme 数据生成 HTML 卡片并插入 DOM

**卡片内容**：
- 图片预览（点击打开 Lightbox）
- 文件名
- 状态徽章
- 错误信息（如果有）
- 标签列表（显示置信度）
- 预览按钮
- 删除按钮
- 批量选择复选框

---

##### 批量删除

```javascript
async function batchDelete()
```

**功能**：批量删除选中的图片记录

**工作流程**：
1. 显示确认对话框
2. 遍历选中的 ID，逐个发送 `DELETE /api/memes/<id>` 请求
3. 统计成功和失败数量
4. 清空选择
5. 刷新列表和统计

---

##### 渲染分页导航

```javascript
function renderPagination(data)
```

**功能**：渲染分页导航组件

**特点**：
- 显示当前页前后各 2 页
- 首页和末页始终显示
- 使用省略号表示跳过的页码

---

##### 删除单条图片

```javascript
async function deleteMeme(id)
```

**功能**：删除单条图片记录（带确认弹窗）

---

#### 统计与自动刷新

##### 加载统计数据

```javascript
function loadStats()
```

**功能**：请求后端统计数据并更新统计栏和导航栏

---

##### 渲染统计栏

```javascript
function renderStatsBar(counts)
```

**功能**：显示总计、已完成、处理中、待处理、错误数量

---

##### 渲染导航栏统计

```javascript
function renderNavStats(counts)
```

**功能**：在导航栏显示完成进度和处理中数量

---

##### 自动刷新

```javascript
function startAutoRefresh()
function stopAutoRefresh()
```

**功能**：当有处理中的任务时，每 5 秒轮询更新列表和统计

---

#### 初始化

```javascript
document.addEventListener("DOMContentLoaded", () => {
    loadMemes();
    loadStats();
    startAutoRefresh();

    document.getElementById("search-input").addEventListener("input", debouncedSearch);

    window.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("beforeunload", () => {
        stopAutoRefresh();
        if (activeEventSource) activeEventSource.close();
    });
});
```

**工作流程**：
1. 加载图片列表
2. 加载统计数据
3. 启动自动刷新
4. 绑定搜索输入事件（防抖 300ms）
5. 绑定滚动事件（控制回到顶部按钮显示）
6. 绑定页面卸载事件（清理定时器和 SSE 连接）

---

### 样式设计 (`app/static/css/app.css`)

#### 主题色变量

```css
:root {
  --surface-0: #0d1117;      /* 主背景色 */
  --surface-1: #161b22;      /* 次背景色（导航栏、输入框） */
  --surface-2: #21262d;      /* 卡片背景色 */
  --surface-3: #30363d;      /* 边框色、悬停背景 */
  --border: #30363d;         /* 边框色 */
  --text-primary: #e6edf3;   /* 主文本色 */
  --text-secondary: #8b949e; /* 次文本色 */
  --text-muted: #6e7681;     /* 弱化文本色 */
  --accent: #58a6ff;         /* 强调色（蓝色） */
  --accent-hover: #79c0ff;   /* 强调色悬停 */
  --success: #3fb950;        /* 成功色（绿色） */
  --danger: #f85149;         /* 危险色（红色） */
  --warning: #d29922;        /* 警告色（黄色） */
  --radius: 8px;             /* 圆角半径 */
  --radius-lg: 12px;         /* 大圆角半径 */
  --transition: 200ms ease;  /* 过渡时间 */
}
```

#### 设计特点

- **深色主题**：GitHub Dark 风格
- **毛玻璃效果**：导航栏使用 `backdrop-filter: blur(12px)`
- **卡片悬停效果**：上浮 2px + 阴影增强
- **渐变进度条**：蓝色到紫色渐变
- **骨架屏加载**：闪烁动画占位符
- **Toast 动画**：右侧滑入/滑出
- **Lightbox 预览**：全屏遮罩 + 缩放动画
- **响应式适配**：小屏幕下调整卡片高度和统计栏布局

---

## 运行指南

### 环境要求

- **Python**：3.10+
- **操作系统**：Windows / macOS / Linux
- **网络**：需要访问 LLM API（阿里云 DashScope）

---

### 安装步骤

#### 1. 克隆或下载项目

```bash
cd "meme_tagger For Web"
```

#### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

**依赖列表**：
```
Flask>=3.0,<4.0
Flask-SQLAlchemy>=3.1,<4.0
httpx>=0.27,<1.0
```

#### 4. 配置环境变量（可选）

**Windows (PowerShell)**：
```powershell
$env:LLM_API_KEY="your-api-key-here"
$env:LLM_API_BASE="https://api.openai.com/v1"
$env:LLM_MODEL="gpt-4o"
$env:MAX_WORKERS="3"
$env:SECRET_KEY="your-secret-key-here"
```

**macOS/Linux**：
```bash
export LLM_API_KEY="your-api-key-here"
export LLM_API_BASE="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o"
export MAX_WORKERS="3"
export SECRET_KEY="your-secret-key-here"
```

---

### 启动应用

```bash
python run.py
```

**启动信息**：
```
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

**访问地址**：http://127.0.0.1:5000

---

### 使用流程

#### 1. 扫描目录

1. 在"扫描目录"输入框中输入图片文件夹路径
   - 示例：`C:\Users\me\Pictures\memes`
2. 点击"扫描"按钮
3. 系统会递归扫描目录，识别所有符合白名单的图片文件
4. 显示扫描结果（文件数量）

#### 2. 启动打标签任务

1. 扫描完成后，"全部打标签"按钮会自动启用
2. 点击"全部打标签"按钮
3. 系统会创建后台任务，开始逐张图片进行 AI 分析
4. 进度条会实时显示处理进度

#### 3. 查看结果

1. 处理完成后，图片列表会自动刷新
2. 每张图片会显示生成的标签（包含置信度）
3. 可以通过状态筛选器查看不同状态的图片
4. 可以使用搜索框按文件名或标签名搜索

#### 4. 管理图片

- **预览图片**：点击图片或预览按钮打开 Lightbox
- **删除单张**：点击卡片上的"删除"按钮
- **批量删除**：勾选多张图片后，点击"删除选中"按钮
- **刷新列表**：点击"刷新"按钮

#### 5. 导出数据

- 点击"导出数据库"按钮，下载 SQLite 数据库文件
- 导出的数据库包含所有图片元数据和标签信息

---

### 开发模式

应用默认以开发模式启动（`debug=True`），支持：
- **自动重载**：代码修改后自动重启服务器
- **调试器**：错误时显示交互式调试器
- **详细日志**：输出详细的请求和处理日志

---

### 生产部署

**注意事项**：

1. **修改 SECRET_KEY**：
   ```bash
   export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   ```

2. **关闭 Debug 模式**：
   修改 `run.py`：
   ```python
   app.run(debug=False, host="0.0.0.0", port=5000)
   ```

3. **使用生产级 WSGI 服务器**：
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
   ```

4. **配置反向代理**（Nginx 示例）：
   ```nginx
   server {
       listen 80;
       server_name example.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

5. **数据库备份**：定期备份 `instance/meme_tagger.db` 文件

---

## 配置说明

### 配置项详解

#### SECRET_KEY

**用途**：Flask session 加密密钥

**默认值**：`"dev-secret-key-change-in-production"`

**生产环境**：必须通过环境变量设置随机值

**生成方法**：
```python
import secrets
print(secrets.token_hex(32))
```

---

#### SQLALCHEMY_DATABASE_URI

**用途**：数据库连接 URI

**默认值**：`sqlite:///instance/meme_tagger.db`

**格式**：
- SQLite：`sqlite:///path/to/database.db`
- PostgreSQL：`postgresql://user:password@host:port/dbname`
- MySQL：`mysql://user:password@host:port/dbname`

**注意**：SQLite 使用相对路径时，相对于项目根目录

---

#### LLM_API_KEY

**用途**：LLM API 密钥

**默认值**：`"sk-your-api-key"`（示例密钥，需替换）

---

#### LLM_API_BASE

**用途**：LLM API 基础 URL

**默认值**：`"https://api.openai.com/v1"`

**其他示例**：
- 阿里云：`"https://dashscope.aliyuncs.com/compatible-mode/v1"`
- 本地 Ollama：`"http://localhost:11434/v1"`

---

#### LLM_MODEL

**用途**：使用的 LLM 模型名称

**默认值**：`"gpt-4o"`

---

#### MAX_WORKERS

**用途**：并发处理线程数

**默认值**：`3`

**建议值**：
- 低配置机器：`2`
- 中配置机器：`3-5`
- 高配置机器：`5-8`

**注意**：过高的并发可能导致 LLM API 限流

---

#### ALLOWED_EXTENSIONS

**用途**：允许扫描的图片文件扩展名白名单

**默认值**：
```python
{".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}
```

**修改方法**：直接编辑 `config.py` 中的集合

---

### 配置文件位置

**主配置文件**：`config.py`

**数据库文件**：`instance/meme_tagger.db`（自动创建）

**日志配置**：在 `app/__init__.py` 中定义

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
```

---

## 依赖关系

### Python 依赖

| 包名 | 版本要求 | 用途 | 依赖链 |
|------|----------|------|--------|
| **Flask** | ≥3.0, <4.0 | Web 框架 | - |
| **Flask-SQLAlchemy** | ≥3.1, <4.0 | ORM 数据库操作 | Flask |
| **httpx** | ≥0.27, <1.0 | HTTP 客户端 | - |

**间接依赖**（由 Flask 和 Flask-SQLAlchemy 自动安装）：
- Werkzeug
- Jinja2
- itsdangerous
- click
- blinker
- SQLAlchemy

---

### 前端依赖（CDN）

| 资源 | 版本 | URL |
|------|------|-----|
| **Bootstrap CSS** | 5.3.3 | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css` |
| **Bootstrap JS** | 5.3.3 | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js` |

---

### 外部服务依赖

| 服务 | 用途 | 必需性 |
|------|------|--------|
| **LLM API** | 图片标签分析 | 必需（核心功能） |

**支持的 API**：
- 所有OpenAI兼容接口

---

### 模块依赖关系图

```
run.py
  └── app/__init__.py (create_app)
        ├── config.py (Config)
        ├── app/models.py (db, Meme, Tag)
        ├── app/routes/main.py (main_bp)
        ├── app/routes/api.py (api_bp)
        │     ├── app/services/db_service.py
        │     ├── app/services/file_service.py
        │     └── app/tasks/worker.py (task_manager)
        │           ├── app/services/ai_service.py
        │           ├── app/services/db_service.py
        │           └── app/services/file_service.py
        └── app/routes/export.py (export_bp)
```