# -*- coding: utf-8 -*-
"""
数据库模型定义
包含 Meme（表情包图片）、Tag（标签）和 MemeTag（多对多关联）三个模型
"""
import uuid
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

# SQLAlchemy 数据库实例，由 app 工厂函数初始化
db = SQLAlchemy()


class MemeStatus:
    """Meme 处理状态常量（对应数据库 INTEGER 值）"""
    PENDING = 0
    PROCESSING = 1
    COMPLETED = 2
    ERROR = 3

    # 状态值到字符串标签的映射（用于 API 响应和前端展示）
    LABELS = {0: "pending", 1: "processing", 2: "completed", 3: "error"}
    # 字符串标签到状态值的反向映射
    VALUES = {"pending": 0, "processing": 1, "completed": 2, "error": 3}


class Meme(db.Model):
    """表情包图片模型，记录文件路径、处理状态，通过 MemeTag 关联标签"""
    __tablename__ = "Memes"

    # 主键：UUID 十六进制字符串（去横线）
    Id = db.Column(db.Text, primary_key=True, default=lambda: uuid.uuid4().hex)
    # 文件绝对路径
    FilePath = db.Column(db.Text, nullable=False)
    # 原始文件名
    FileName = db.Column(db.Text, nullable=False)
    # 文件 MD5 哈希值，唯一索引用于去重
    Md5Hash = db.Column(db.Text, nullable=False, unique=True, index=True)
    # 处理状态：0=待处理 1=处理中 2=已完成 3=错误
    Status = db.Column(db.Integer, nullable=False, default=MemeStatus.PENDING, index=True)
    # 记录创建时间
    CreatedAt = db.Column(db.Text, nullable=False, default=lambda: datetime.utcnow().isoformat())

    # 多对多关系：通过 MemeTag 关联 Tag
    meme_tags = db.relationship(
        "MemeTag", back_populates="meme", cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """将模型实例序列化为字典，用于 JSON 响应"""
        return {
            "id": self.Id,
            "file_path": self.FilePath,
            "file_name": self.FileName,
            "md5_hash": self.Md5Hash,
            "status": MemeStatus.LABELS.get(self.Status, "pending"),
            "tags": [
                {"name": mt.tag.Name, "type": mt.tag.Type}
                for mt in self.meme_tags
            ],
            "created_at": self.CreatedAt,
        }


class Tag(db.Model):
    """独立标签表，可被多个 Meme 共享，Name 全局唯一"""
    __tablename__ = "Tags"

    # 主键自增 ID
    Id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    # 标签名称（全局唯一，不区分大小写）
    Name = db.Column(db.Text, nullable=False, unique=True)
    # 标签类型（预留扩展字段）
    Type = db.Column(db.Integer, nullable=False, default=0)

    # 多对多反向关系
    meme_tags = db.relationship(
        "MemeTag", back_populates="tag", cascade="all, delete-orphan"
    )


class MemeTag(db.Model):
    """多对多关联表，记录 Meme 与 Tag 的绑定关系"""
    __tablename__ = "MemeTags"

    # 复合主键：MemeId + TagId
    MemeId = db.Column(db.Text, db.ForeignKey("Memes.Id", ondelete="CASCADE"), primary_key=True)
    TagId = db.Column(db.Integer, db.ForeignKey("Tags.Id", ondelete="CASCADE"), primary_key=True)

    # 双向关系
    meme = db.relationship("Meme", back_populates="meme_tags")
    tag = db.relationship("Tag", back_populates="meme_tags")
