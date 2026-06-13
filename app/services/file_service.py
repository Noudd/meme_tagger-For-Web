# -*- coding: utf-8 -*-
"""
文件工具服务
提供图片文件扫描和 MD5 哈希计算等通用文件操作
"""
import hashlib
from pathlib import Path
from typing import Optional

from config import Config


def get_image_files(directory: str) -> list[Path]:
    """递归扫描目录，返回所有符合 ALLOWED_EXTENSIONS 白名单的图片文件路径（已排序）"""
    dir_path = Path(directory).resolve()
    if not dir_path.exists() or not dir_path.is_dir():
        return []

    image_files: list[Path] = []
    for entry in dir_path.rglob("*"):
        if entry.is_file() and entry.suffix.lower() in Config.ALLOWED_EXTENSIONS:
            image_files.append(entry)
    return sorted(image_files)


def compute_md5(file_path: Path) -> Optional[str]:
    """计算文件的 MD5 哈希值，用于文件去重校验。读取失败时返回 None"""
    try:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except OSError:
        return None
