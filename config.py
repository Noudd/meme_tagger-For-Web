# -*- coding: utf-8 -*-
"""
应用配置文件
集中管理所有配置项，支持通过环境变量覆盖默认值
"""
import os
from pathlib import Path

# 项目根目录，用于构建数据库文件等绝对路径
BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Flask 应用主配置类"""

    # Flask session 加密密钥（生产环境务必通过环境变量设置随机值）
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # SQLite 数据库 URI，默认存储在 instance/meme_tagger.db
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'meme_tagger.db'}"
    )
    # 关闭 SQLAlchemy 事件追踪，减少内存开销
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 大语言模型 API 配置（用于图片标签分析）
    LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
    LLM_API_BASE = os.environ.get("LLM_API_BASE", "")
    LLM_MODEL = os.environ.get("LLM_MODEL", "")

    # 并发处理图片的工作线程数
    MAX_WORKERS = int(os.environ.get("MAX_WORKERS", "3"))

    # 允许扫描的图片文件扩展名白名单
    ALLOWED_EXTENSIONS = {
        ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"
    }
