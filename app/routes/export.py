# -*- coding: utf-8 -*-
"""
数据库导出蓝图
提供 SQLite 数据库文件的安全导出下载功能
"""
import logging
import sqlite3
import tempfile
from pathlib import Path

from flask import Blueprint, after_this_request, current_app, send_file

logger = logging.getLogger(__name__)

# 导出蓝图，挂在 /api 前缀下
export_bp = Blueprint("export", __name__, url_prefix="/api")


@export_bp.route("/export", methods=["GET"])
def export_database():
    """
    导出当前 SQLite 数据库文件：
    1. 以只读模式打开源数据库，备份到临时文件
    2. 将临时文件作为附件发送给客户端
    3. 响应完成后自动清理临时文件
    """
    db_path = Path(current_app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", ""))

    if not db_path.exists():
        return {"error": "Database file not found"}, 404

    # 创建临时文件用于存放数据库备份副本
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp_path = Path(tmp.name)
    tmp.close()

    try:
        source = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            dest = sqlite3.connect(str(tmp_path))
            try:
                source.backup(dest)
            finally:
                dest.close()
        finally:
            source.close()

        @after_this_request
        def cleanup(response):
            """请求结束后删除临时备份文件，释放磁盘空间"""
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass
            return response

        return send_file(
            str(tmp_path),
            mimetype="application/octet-stream",
            as_attachment=True,
            download_name="meme_tagger_export.db",
        )

    except sqlite3.Error as e:
        logger.error("Database export failed: %s", e)
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass
        return {"error": f"Export failed: {e}"}, 500
