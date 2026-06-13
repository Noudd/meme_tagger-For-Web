# -*- coding: utf-8 -*-
"""
Flask 应用工厂模块
负责创建和配置 Flask 应用实例，初始化数据库、注册蓝图
"""
import logging
from pathlib import Path

from flask import Flask

from config import Config

# 配置全局日志格式：时间 + 级别 + 模块名 + 消息
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app(config_class=Config) -> Flask:
    """应用工厂函数：创建并配置完整的 Flask 应用"""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 确保数据库所在目录存在（SQLite 需要目录已创建）
    instance_path = Path(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "")).parent
    instance_path.mkdir(parents=True, exist_ok=True)

    # 初始化 SQLAlchemy 数据库扩展
    from app.models import db
    db.init_app(app)

    # 注册各功能蓝图：主页、API 接口、数据导出
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.export import export_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(export_bp)

    # 在应用上下文中创建所有数据库表（如果尚不存在）
    with app.app_context():
        db.create_all()

    return app
