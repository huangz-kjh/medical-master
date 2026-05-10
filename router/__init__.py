# router/__init__.py
from router.auth import auth_routes
from router.dashboard import init_dashboard_routes
from router.admin_panel import init_admin_routes, admin_api
from router.appointment import init_appointment_routes
from router.patient_management import init_patient_management_routes
from router.medical_records import init_medical_records_routes
from router.user_profile import init_user_profile_routes
from router.medical_imaging import init_medical_imaging_routes
from router.chat_service import init_chat_routes
from router.predict import init_predict_routes
from router.api import api_bp
from router.notification import init_notification_routes
# from router.user import init_user_routes
# from router.patient import init_patient_routes
# from router.doctor import init_doctor_routes
# from router.settings import init_settings_routes
from router.analytics import init_analytics_routes
import logging

# 配置日志
logger = logging.getLogger(__name__)


def init_app(app):
    # 用户认证相关路由
    auth_routes(app)

    # 仪表盘和主页相关路由
    init_dashboard_routes(app)

    # 管理员功能相关路由
    init_admin_routes(app)

    # 预约管理相关路由
    init_appointment_routes(app)

    # 患者管理相关路由
    init_patient_management_routes(app)

    # 医疗记录相关路由
    init_medical_records_routes(app)

    # 用户资料相关路由
    init_user_profile_routes(app)

    # 医疗影像相关路由
    init_medical_imaging_routes(app)

    # 聊天和智能分析服务路由
    init_chat_routes(app)

    # 预测诊断相关路由
    init_predict_routes(app)

    # 通知相关路由
    init_notification_routes(app)

    # API路由
    app.register_blueprint(api_bp, url_prefix='/api')

    # 添加分析模块路由
    init_analytics_routes(app)

    # 注册admin_api蓝图，确保RESTful API可用
    app.register_blueprint(admin_api)
