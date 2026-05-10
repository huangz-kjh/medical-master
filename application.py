import os
import sys

from flask import Flask, jsonify, request, session
from flask_cors import CORS

from router import init_app
from db_model import db, PageVisit, User
from router.scheduler import scheduler  # 导入预约调度器
from sqlalchemy.exc import IntegrityError
from db_config import get_sqlalchemy_uri


def create_app():
    app = Flask(__name__)
    # 更新CORS配置，允许所有源、方法和头信息
    CORS(app, resources={
        r"/*": {"origins": "*", "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"], "allow_headers": "*"}})
    # 应用配置
    app.secret_key = "your-secret-key"

    # Sealos远程数据库配置
    # app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:jzlxhknh@dbconn.sealosbja.site:45217/app'
    # 本地数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = get_sqlalchemy_uri('local')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 增加调试信息
    print("[INFO] 创建Flask应用")

    # 添加iframe嵌入所需的HTTP头
    @app.after_request
    def add_security_headers(response):
        # 允许iframe嵌入
        response.headers['X-Frame-Options'] = 'ALLOWALL'
        response.headers['Content-Security-Policy'] = 'frame-ancestors *'
        # 添加CORS头，确保预检请求能正确处理
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        # 处理预检请求
        if request.method == 'OPTIONS':
            return response
        return response

    # 添加错误处理程序
    @app.errorhandler(404)
    def page_not_found(e):
        print(f"[错误] 404错误: {request.path}")
        if request.path.startswith('/api/'):
            return jsonify({"error": "找不到请求的资源", "path": request.path}), 404
        return f"<h1>404 错误</h1><p>找不到请求的页面: {request.path}</p>", 404

    @app.errorhandler(500)
    def server_error(e):
        print(f"[错误] 500错误: {str(e)}")
        return f"<h1>500 服务器错误</h1><p>服务器内部错误</p>", 500

    # 初始化数据库
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            print("[INFO] 数据库表已创建")
        except Exception as e:
            print("[ERROR] 数据库初始化失败:", str(e))

    # 注册所有路由模块
    init_app(app)

    # 初始化预约提醒调度器
    scheduler.init_app(app)

    # 记录每次页面访问
    @app.before_request
    def record_page_visit():
        # 只记录登录用户且不是静态资源
        if session.get('user_id') and request.endpoint and not request.endpoint.startswith('static'):
            visit = PageVisit(
                user_id=session.get('user_id'),
                endpoint=request.endpoint,
                ip=request.remote_addr
            )
            # 仅在用户存在时记录访问日志
            if db.session.get(User, session.get('user_id')):
                db.session.add(visit)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()

    return app


if __name__ == '__main__':
    # 处理命令行参数
    no_app = False
    start_app_delay = 5  # 默认延迟5秒启动应用

    # 解析命令行参数
    for arg in sys.argv[1:]:
        if arg == '--no-app':
            no_app = True
            print("[命令] 跳过应用服务器启动")
        elif arg.startswith('--app-delay='):
            try:
                start_app_delay = int(arg.split('=')[1])
                print(f"[命令] 应用服务器延迟启动时间设置为 {start_app_delay} 秒")
            except:
                pass

    # 先启动Flask应用
    app = create_app()
    port = 5002

    # 获取真实执行文件目录
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    print("BASE_DIR:", BASE_DIR)

    # 设置依赖目录
    UPLOAD_DIR = os.path.join(BASE_DIR, "predict", "nnunet_uploaded")
    OUTPUT_DIR = os.path.join(BASE_DIR, "predict", "nnunet_output")
    print("UPLOAD_DIR:", UPLOAD_DIR)
    print("OUTPUT_DIR:", OUTPUT_DIR)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 启动Flask应用
    print(f"[INFO] 启动Flask应用，监听端口: {port}")
    app.run(debug=True, port=port, host='0.0.0.0')
