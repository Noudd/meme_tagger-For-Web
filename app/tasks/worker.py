# -*- coding: utf-8 -*-
"""
后台任务管理器
使用线程池并发处理图片的 AI 标签分析任务，支持 SSE 实时进度推送
"""
import logging
import queue
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from flask import Flask

from app.models import db
from app.services.ai_service import analyze_image
from app.services.db_service import (
    add_tags_to_meme,
    get_or_create_meme,
    update_meme_status,
)
from app.services.file_service import compute_md5
from config import Config

logger = logging.getLogger(__name__)


class TaskStatus:
    """任务状态常量定义"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class TaskManager:
    """
    任务管理器：管理后台打标签任务的生命周期
    - 使用线程池（ThreadPoolExecutor）并发处理多张图片
    - 通过消息队列向 SSE 端点推送实时进度
    - 线程安全：所有共享状态通过 threading.Lock 保护
    """

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=Config.MAX_WORKERS)
        self._tasks: dict[str, dict[str, Any]] = {}  # 所有任务的状态数据
        self._lock = threading.Lock()  # 保护 _tasks 的并发访问锁
        self._progress_queues: dict[str, queue.Queue[dict[str, Any]]] = {}  # 每个任务的进度消息队列

    def create_task(self, file_paths: list[Path], app: Flask) -> str:
        """创建新的打标签任务，提交到线程池执行，返回任务 ID"""
        task_id = uuid.uuid4().hex[:12]
        total = len(file_paths)

        with self._lock:
            self._tasks[task_id] = {
                "task_id": task_id,
                "status": TaskStatus.PENDING,
                "total": total,
                "completed": 0,
                "current_file": "",
                "errors": [],
                "created_at": time.time(),
            }
            self._progress_queues[task_id] = queue.Queue[dict[str, Any]]()

        # 将任务提交到线程池异步执行
        self._executor.submit(self._run_task, task_id, file_paths, app)
        return task_id

    def _run_task(self, task_id: str, file_paths: list[Path], app: Flask) -> None:
        """任务执行主体：遍历文件列表，逐个调用 AI 分析并保存结果"""
        with self._lock:
            self._tasks[task_id]["status"] = TaskStatus.RUNNING

        self._push_progress(task_id, self._tasks[task_id])

        for fp in file_paths:
            with self._lock:
                self._tasks[task_id]["current_file"] = str(fp)

            self._push_progress(task_id, self._tasks[task_id])

            try:
                self._process_single_file(fp, task_id, app)
            except Exception as e:
                logger.error("Error processing %s: %s", fp, e)
                with self._lock:
                    self._tasks[task_id]["errors"].append(
                        {"file": str(fp), "error": str(e)}
                    )

            with self._lock:
                self._tasks[task_id]["completed"] += 1

            self._push_progress(task_id, self._tasks[task_id])

        with self._lock:
            self._tasks[task_id]["status"] = TaskStatus.COMPLETED
            self._tasks[task_id]["current_file"] = ""

        self._push_progress(task_id, self._tasks[task_id])
        self._push_done(task_id)

    def _process_single_file(self, file_path: Path, task_id: str, app: Flask) -> None:
        """
        处理单个文件的完整流程：
        1. 计算 MD5 → 2. 创建/获取数据库记录 → 3. 调用 AI 分析 → 4. 保存标签并更新状态
        """
        md5_hash = compute_md5(file_path)
        if md5_hash is None:
            raise OSError(f"Cannot read file: {file_path}")

        meme_id: int | None = None

        with app.app_context():
            try:
                meme = get_or_create_meme(file_path, md5_hash)
                meme_id = meme.id

                update_meme_status(meme_id, "processing")
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

        try:
            tags = analyze_image(file_path)
        except Exception as e:
            with app.app_context():
                try:
                    if meme_id is not None:
                        update_meme_status(meme_id, "error", str(e))
                        db.session.commit()
                except Exception:
                    db.session.rollback()
            raise

        with app.app_context():
            try:
                if meme_id is not None:
                    add_tags_to_meme(meme_id, tags)
                    update_meme_status(meme_id, "completed")
                    db.session.commit()
            except Exception:
                db.session.rollback()
                raise

    def _push_progress(
        self, task_id: str, task_data: dict[str, Any]
    ) -> None:
        """将任务进度数据推送到对应的 SSE 消息队列"""
        queue = self._progress_queues.get(task_id)
        if queue is None:
            return
        data = task_data.copy()
        data["errors"] = list(task_data["errors"])
        queue.put(data)

    def _push_done(self, task_id: str) -> None:
        """向队列推送 None 信号，通知 SSE 客户端任务已结束"""
        queue = self._progress_queues.get(task_id)
        if queue is not None:
            queue.put(None)

    def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取指定任务的当前状态快照（线程安全）"""
        with self._lock:
            return self._tasks.get(task_id)

    def subscribe_progress(
        self, task_id: str
    ) -> queue.Queue[dict[str, Any]] | None:
        """订阅指定任务的进度消息队列，供 SSE 端点消费"""
        return self._progress_queues.get(task_id)

    def unsubscribe_progress(self, task_id: str) -> None:
        """取消订阅进度队列，SSE 连接断开时调用"""
        self._progress_queues.pop(task_id, None)

    def shutdown(self) -> None:
        """关闭线程池，等待所有正在执行的任务完成"""
        self._executor.shutdown(wait=True)


# 全局单例任务管理器实例，供路由模块导入使用
task_manager = TaskManager()
