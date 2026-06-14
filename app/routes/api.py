# -*- coding: utf-8 -*-
"""
API 接口蓝图
提供扫描目录、启动打标签任务、SSE 进度推送、图片 CRUD 和统计等 RESTful 接口
"""
import json
import logging
import queue
import time
from pathlib import Path

from flask import Blueprint, Response, current_app, jsonify, request, send_file, stream_with_context

from app.services.db_service import delete_meme, get_all_memes, get_meme_count_by_status
from app.services.file_service import get_image_files
from app.tasks.worker import task_manager

logger = logging.getLogger(__name__)

# API 蓝图，统一前缀 /api
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/scan", methods=["POST"])
def scan_directory():
    """扫描指定目录，返回其中符合白名单扩展名的图片文件列表"""
    data = request.get_json(silent=True) or {}
    directory = data.get("directory", "").strip()

    if not directory:
        return jsonify({"error": "Directory path is required"}), 400

    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        return jsonify({"error": f"Directory not found: {directory}"}), 404

    image_files = get_image_files(directory)
    return jsonify(
        {
            "directory": str(dir_path.resolve()),
            "count": len(image_files),
            "files": [str(f) for f in image_files],
        }
    )


@api_bp.route("/tag", methods=["POST"])
def tag_files():
    """接收文件路径列表，创建后台打标签任务，返回任务 ID"""
    data = request.get_json(silent=True) or {}
    files = data.get("files", [])

    if not files:
        return jsonify({"error": "No files provided"}), 400

    file_paths = [Path(f) for f in files]
    existing = [fp for fp in file_paths if fp.is_file()]
    if not existing:
        return jsonify({"error": "No valid files found"}), 400

    task_id = task_manager.create_task(existing, current_app._get_current_object())
    return jsonify({"task_id": task_id, "total": len(existing)})


@api_bp.route("/progress_stream/<task_id>")
def progress_stream(task_id: str):
    """SSE 端点：实时推送打标签任务的进度信息给前端"""
    progress_queue = task_manager.subscribe_progress(task_id)
    if progress_queue is None:
        task_status = task_manager.get_task_status(task_id)
        if task_status is None:
            return jsonify({"error": "Task not found"}), 404
        if task_status["status"] in ("completed", "error"):
            return Response(
                f"data: {json.dumps(task_status)}\n\n",
                mimetype="text/event-stream",
            )
        return jsonify({"error": "Task stream not available"}), 400

    def generate():
        """SSE 事件生成器：持续从队列读取进度数据并推送给客户端"""
        try:
            while True:
                try:
                    data = progress_queue.get(timeout=30)
                except queue.Empty:
                    yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
                    continue

                if data is None:
                    break

                yield f"data: {json.dumps(data)}\n\n"
        except GeneratorExit:
            pass
        finally:
            task_manager.unsubscribe_progress(task_id)

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@api_bp.route("/memes", methods=["GET"])
def list_memes():
    """分页查询表情包列表，支持按状态筛选和关键词搜索"""
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status_filter = request.args.get("status", None, type=str)
    search = request.args.get("search", None, type=str)

    result = get_all_memes(
        page=page,
        per_page=per_page,
        status_filter=status_filter,
        search=search,
    )
    return jsonify(result)


@api_bp.route("/memes/<string:meme_id>", methods=["DELETE"])
def remove_meme(meme_id: str):
    """删除指定 ID 的表情包记录，级联删除其 MemeTag 关联"""
    success = delete_meme(meme_id)
    if not success:
        return jsonify({"error": "Meme not found"}), 404
    return jsonify({"message": "Meme deleted"})


@api_bp.route("/stats", methods=["GET"])
def get_stats():
    """返回各处理状态（pending/processing/completed/error）的表情包数量统计"""
    counts = get_meme_count_by_status()
    return jsonify(counts)


@api_bp.route("/file_preview", methods=["GET"])
def file_preview():
    """返回指定路径图片文件的二进制内容，用于前端预览"""
    file_path = request.args.get("path", "")
    if not file_path:
        return jsonify({"error": "Path parameter required"}), 400

    fp = Path(file_path)
    if not fp.is_file():
        return jsonify({"error": "File not found"}), 404

    return send_file(str(fp.resolve()))
