# -*- coding: utf-8 -*-
"""
数据库模型定义
包含 Meme（表情包图片）和 Tag（标签）两个核心模型
"""
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy 数据库实例，由 app 工厂函数初始化
db = SQLAlchemy()


class Meme(db.Model):
    """表情包图片模型，记录文件信息、处理状态和关联标签"""
    __tablename__ = "memes"

    # 主键 ID
    id = db.Column(db.Integer, primary_key=True)
    # 文件绝对路径（唯一索引，防止重复录入）
    file_path = db.Column(db.String(1024), unique=True, nullable=False, index=True)
    # 原始文件名
    file_name = db.Column(db.String(512), nullable=False)
    # 文件 MD5 哈希值，用于去重校验
    md5_hash = db.Column(db.String(32), nullable=False)
    # 处理状态：pending / processing / completed / error
    status = db.Column(
        db.String(20), nullable=False, default="pending", index=True
    )
    # 处理失败时的错误信息
    error_message = db.Column(db.Text, nullable=True)
    # 记录创建时间（UTC）
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # 最后更新时间（UTC），插入和更新时自动刷新
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # 一对多关系：一个 Meme 可拥有多个 Tag，删除 Meme 时级联删除其 Tags
    tags = db.relationship("Tag", back_populates="meme", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        """将模型实例序列化为字典，用于 JSON 响应"""
        return {
            "id": self.id,
            "file_path": self.file_path,
            "file_name": self.file_name,
            "md5_hash": self.md5_hash,
            "status": self.status,
            "error_message": self.error_message,
            "tags": [t.to_dict() for t in self.tags],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Tag(db.Model):
    """标签模型，由 AI 分析生成，关联到具体的 Meme 图片"""
    __tablename__ = "tags"

    # 主键 ID
    id = db.Column(db.Integer, primary_key=True)
    # 标签名称（如"搞笑"、"动物"、"文字梗"等）
    name = db.Column(db.String(256), nullable=False)
    # AI 给出的置信度，范围 0.0 ~ 1.0
    confidence = db.Column(db.Float, nullable=False, default=0.0)
    # 外键：所属 Meme 的 ID
    meme_id = db.Column(db.Integer, db.ForeignKey("memes.id"), nullable=False)

    # 多对一反向关系
    meme = db.relationship("Meme", back_populates="tags")

    def to_dict(self) -> dict:
        """将标签实例序列化为字典，用于 JSON 响应"""
        return {
            "id": self.id,
            "name": self.name,
            "confidence": self.confidence,
            "meme_id": self.meme_id,
        }
