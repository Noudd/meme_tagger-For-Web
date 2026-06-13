# -*- coding: utf-8 -*-
"""
数据库操作服务层
封装所有与数据库交互的业务逻辑，包括 Meme 的增删改查和标签管理
"""
import logging
from pathlib import Path
from typing import Any, Optional

from app.models import Meme, Tag, db

logger = logging.getLogger(__name__)


def get_or_create_meme(file_path: Path, md5_hash: str) -> Meme:
    """根据文件路径查找已有 Meme 记录，不存在则创建新的 pending 状态记录"""
    meme = Meme.query.filter_by(file_path=str(file_path)).first()
    if meme:
        return meme

    meme = Meme(
        file_path=str(file_path),
        file_name=file_path.name,
        md5_hash=md5_hash,
        status="pending",
    )
    db.session.add(meme)
    db.session.commit()
    return meme


def update_meme_status(
    meme_id: int, status: str, error_message: Optional[str] = None
) -> None:
    """更新指定 Meme 的处理状态，可选附带错误信息"""
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        logger.warning("Attempted to update non-existent meme ID %d", meme_id)
        return
    meme.status = status
    if error_message:
        meme.error_message = error_message
    db.session.commit()


def add_tags_to_meme(meme_id: int, tags: list[dict[str, Any]]) -> None:
    """为指定 Meme 批量写入标签（先清除旧标签再写入新标签，实现覆盖更新）"""
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        logger.warning("Attempted to add tags to non-existent meme ID %d", meme_id)
        return

    Tag.query.filter_by(meme_id=meme_id).delete()

    for tag_data in tags:
        tag = Tag(
            name=tag_data["name"],
            confidence=tag_data["confidence"],
            meme_id=meme_id,
        )
        db.session.add(tag)

    db.session.commit()


def get_all_memes(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    search: Optional[str] = None,
) -> dict[str, Any]:
    """分页查询 Meme 列表，支持按状态筛选和文件名/标签名模糊搜索"""
    query = Meme.query

    if status_filter:
        query = query.filter_by(status=status_filter)

    if search:
        query = query.filter(
            Meme.file_name.ilike(f"%{search}%")
            | Meme.tags.any(Tag.name.ilike(f"%{search}%"))
        )

    query = query.order_by(Meme.updated_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "memes": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
    }


def delete_meme(meme_id: int) -> bool:
    """删除指定 Meme 记录及其关联的 Tag 记录，返回是否删除成功"""
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        return False
    db.session.delete(meme)
    db.session.commit()
    return True


def get_meme_count_by_status() -> dict[str, int]:
    """按处理状态分组统计 Meme 数量，返回 {status: count} 字典"""
    results = (
        db.session.query(Meme.status, db.func.count(Meme.id))
        .group_by(Meme.status)
        .all()
    )
    counts: dict[str, int] = {}
    for status, count in results:
        counts[status] = count
    return counts
