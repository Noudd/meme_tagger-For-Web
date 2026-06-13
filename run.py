# -*- coding: utf-8 -*-
"""
Meme Tagger Web 应用入口文件
启动 Flask 开发服务器，监听本地 5000 端口
"""
from app import create_app

# 通过工厂函数创建 Flask 应用实例
app = create_app()

if __name__ == "__main__":
    # 开发模式下启动服务器，开启 debug 自动重载
    app.run(debug=True, host="127.0.0.1", port=5000)
