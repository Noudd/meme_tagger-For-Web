# -*- coding: utf-8 -*-
"""
主页面蓝图
提供前端页面的入口路由
"""
from flask import Blueprint, render_template

# 主页蓝图，无 URL 前缀
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """渲染前端单页应用主页"""
    return render_template("index.html")
