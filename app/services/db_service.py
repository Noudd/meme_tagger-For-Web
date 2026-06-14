# -*- coding: utf-8 -*-
"""
数据库操作服务层
封装所有与数据库交互的业务逻辑，包括 Meme 的增删改查和标签管理
"""
import logging
from pathlib import Path
from typing import Any, Optional

from app.models import Meme, MemeStatus, MemeTag, Tag, db

logger = logging.getLogger(__name__)


def _get_or_create_tag(name: str, tag_type: int = 0) -> Tag:
    """根据名称查找已有 Tag，不存在则创建新的 Tag 记录"""
    tag = Tag.query.filter_by(Name=name).first()
    if tag:
        return tag
    tag = Tag(Name=name, Type=tag_type)
    db.session.add(tag)
    db.session.flush()
    return tag


def get_or_create_meme(file_path: Path, md5_hash: str) -> Meme:
    """根据 MD5 哈希值查找已有 Meme 记录，不存在则创建新的 pending 状态记录"""
    meme = Meme.query.filter_by(Md5Hash=md5_hash).first()
    if meme:
        return meme

    meme = Meme(
        FilePath=str(file_path),
        FileName=file_path.name,
        Md5Hash=md5_hash,
        Status=MemeStatus.PENDING,
    )
    db.session.add(meme)
    db.session.commit()
    return meme


def update_meme_status(meme_id: str, status: int) -> None:
    """更新指定 Meme 的处理状态（0=待处理 1=处理中 2=已完成 3=错误）"""
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        logger.warning("Attempted to update non-existent meme ID %s", meme_id)
        return
    meme.Status = status
    db.session.commit()


def add_tags_to_meme(meme_id: str, tags: list[dict[str, Any]]) -> None:
    """
    为指定 Meme 批量写入标签：先清除旧关联，再根据标签名查找或创建 Tag 并建立关联
    AI 返回的 confidence 字段仅用于日志记录，不持久化到数据库
    """
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        logger.warning("Attempted to add tags to non-existent meme ID %s", meme_id)
        return

    MemeTag.query.filter_by(MemeId=meme_id).delete()

    for tag_data in tags:
        name = tag_data["name"]
        tag = _get_or_create_tag(name)
        link = MemeTag(MemeId=meme_id, TagId=tag.Id)
        db.session.add(link)

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
        status_value = MemeStatus.VALUES.get(status_filter)
        if status_value is not None:
            query = query.filter_by(Status=status_value)

    if search:
        query = query.filter(
            Meme.FileName.ilike(f"%{search}%")
            | Meme.Id.in_(
                db.session.query(MemeTag.MemeId)
                .join(Tag, MemeTag.TagId == Tag.Id)
                .filter(Tag.Name.ilike(f"%{search}%"))
            )
        )

    query = query.order_by(Meme.CreatedAt.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return {
        "memes": [m.to_dict() for m in pagination.items],
        "total": pagination.total,
        "page": pagination.page,
        "per_page": pagination.per_page,
        "pages": pagination.pages,
    }


def delete_meme(meme_id: str) -> bool:
    """删除指定 Meme 记录，级联删除其 MemeTag 关联（外键 ON DELETE CASCADE）"""
    meme = db.session.get(Meme, meme_id)
    if meme is None:
        return False
    db.session.delete(meme)
    db.session.commit()
    return True


def get_meme_count_by_status() -> dict[str, int]:
    """按处理状态分组统计 Meme 数量，状态值映射为字符串标签返回"""
    results = (
        db.session.query(Meme.Status, db.func.count(Meme.Id))
        .group_by(Meme.Status)
        .all()
    )
    counts: dict[str, int] = {}
    for status, count in results:
        label = MemeStatus.LABELS.get(status, str(status))
        counts[label] = count
    return counts
