"""
生产入口。app.py 在被导入时已自动建库 + 生成示例照片。
- gunicorn 用:  gunicorn app:app  (或 gunicorn wsgi:app)
- PythonAnywhere 的 WSGI 配置文件里 import 的是 application
"""
from app import app

application = app
