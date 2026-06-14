# Meme Tagger For Web

基于 Flask 的表情包 AI 自动标签生成工具。通过大语言模型（LLM）对表情包进行视觉分析，自动生成分类标签并存储到 SQLite 数据库。

配合命令面板插件[memeSeacher](https://github.com/Noudd/memeSearcher)(仓库暂未公开),可快速查找表情包并复制到剪切板中

## 功能特性

-  **目录扫描**：递归扫描指定目录，识别图片文件
-  **AI 标签生成**：调用 LLM API 分析图片，自动生成 3-8 个标签
-  **异步处理**：线程池并发处理，支持实时进度推送（SSE）
-  **数据持久化**：SQLite 数据库存储图片元数据和标签
-  **现代化 UI**：深色主题单页应用，支持预览、筛选、搜索、批量操作
-  **数据导出**：一键导出 SQLite 数据库文件

## 技术栈

**后端**：
- Flask ≥3.0
- Flask-SQLAlchemy ≥3.1
- httpx ≥0.27
- SQLite

**前端**：
- Bootstrap 5.3.3
- 原生 JavaScript (ES6+)
- Server-Sent Events (SSE)

**AI 服务**：
- OpenAI 兼容 API

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（可选）

```bash
# Windows PowerShell
$env:LLM_API_KEY="your-api-key"
$env:LLM_API_BASE="https://api.openai.com/v1"
$env:LLM_MODEL="gpt-4o"

# macOS/Linux
export LLM_API_KEY="your-api-key"
export LLM_API_BASE="https://api.openai.com/v1"
export LLM_MODEL="gpt-4o"
```

### 3. 启动应用

```bash
python run.py
```

访问 http://127.0.0.1:5000

## 使用说明

1. **扫描目录**：输入图片文件夹路径，点击"扫描"
2. **打标签**：点击"全部打标签"，系统自动分析并生成标签
3. **查看结果**：在图片列表中查看生成的标签
4. **管理图片**：支持预览、筛选、搜索、删除
5. **导出数据**：点击"导出数据库"下载 SQLite 文件

## 项目结构

```
meme_tagger For Web/
├── app/
│   ├── routes/          # 路由蓝图
│   ├── services/        # 业务服务层
│   ├── tasks/           # 后台任务
│   ├── templates/       # HTML 模板
│   └── static/          # 静态资源
├── instance/            # 运行时数据（自动创建）
├── config.py           # 配置文件
└── run.py              # 应用入口
```

## 配置说明

主要配置项（可通过环境变量覆盖）：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `LLM_API_KEY` | `sk-your-api-key` | LLM API 密钥 |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API 基础 URL |
| `LLM_MODEL` | `gpt-4o` | 模型名称 |
| `MAX_WORKERS` | `3` | 并发线程数 |

## 开发

```bash
# 开发模式（自动重载）
python run.py

# 生产部署（使用 gunicorn）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:create_app()"
```

## 声明

更多信息请查看[CODE_WIKI.md](CODE_WIKI.md)
本项目仅供学习和研究使用。

