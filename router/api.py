from flask import Blueprint, jsonify, request, session, current_app
from db_model import db, User, Patient, Appointment, Notification
from datetime import date
from functools import wraps
from sqlalchemy.orm import joinedload
from flask_cors import CORS

# 创建蓝图
api_bp = Blueprint('api', __name__)
# 启用CORS
CORS(api_bp, resources={r"/*": {"origins": "*"}})

# 权限检查装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function

def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': '请先登录'}), 401

        user = User.query.get(session['user_id'])
        if not user or user.role != 'doctor':
            return jsonify({'error': '只有医生才能访问此功能'}), 403
        return f(*args, **kwargs)
    return decorated_function

# 获取今日预约
@api_bp.route('/today_appointments', methods=['GET'])
@doctor_required
def get_today_appointments():
    try:
        # 获取当前医生ID
        doctor_id = session.get('user_id')

        # 查询今日该医生的所有预约
        today = date.today()
        appointments = Appointment.query.options(
            joinedload(Appointment.patient)  # 预加载患者信息
        ).filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == today
        ).order_by(
            Appointment.time_slot
        ).all()

        # 准备返回数据
        appointments_data = []
        for appointment in appointments:
            patient_data = None
            if appointment.patient:
                patient_data = {
                    'id': appointment.patient.patient_id,
                    'name': appointment.patient.name,
                    'gender': appointment.patient.gender,
                    'age': appointment.patient.age
                }

            appointments_data.append({
                'id': appointment.appointment_id,
                'time_slot': appointment.time_slot.display_name if appointment.time_slot else "",
                'appointment_type': appointment.appointment_type.display_name if appointment.appointment_type else "",
                'department': appointment.department.display_name if appointment.department else "",
                'status': appointment.status.display_name if appointment.status else "",
                'symptoms': appointment.symptoms,
                'patient': patient_data,
                'code': appointment.code
            })

        return jsonify(appointments_data)

    except Exception as e:
        return jsonify({'error': f'获取预约数据失败: {str(e)}'}), 500

# 获取用户通知
@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications():
    try:
        # 获取当前用户ID
        user_id = session.get('user_id')

        # 获取请求参数
        limit = request.args.get('limit', default=10, type=int)
        unread_only = request.args.get('unread_only', default='false', type=str).lower() == 'true'

        # 构建查询
        query = Notification.query.filter(Notification.user_id == user_id)

        # 如果只查询未读通知
        if unread_only:
            query = query.filter(Notification.is_read == False)

        # 按创建时间降序排序并限制数量
        notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()

        # 准备返回数据
        result = []
        for notification in notifications:
            result.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.type,
                'related_id': notification.related_id,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': notification.is_read
            })

        # 获取未读通知总数
        unread_count = Notification.query.filter(
            Notification.user_id == user_id,
            Notification.is_read == False
        ).count()

        return jsonify({
            'notifications': result,
            'unread_count': unread_count,
            'total': len(result)
        })

    except Exception as e:
        return jsonify({'error': f'获取通知失败: {str(e)}'}), 500

# 标记通知为已读
@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    try:
        # 获取当前用户ID
        user_id = session.get('user_id')

        # 查找指定通知
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()

        if not notification:
            return jsonify({'error': '通知不存在或无权限访问'}), 404

        # 标记为已读
        notification.is_read = True
        db.session.commit()

        return jsonify({'success': True, 'message': '通知已标记为已读'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'标记通知失败: {str(e)}'}), 500

# 标记所有通知为已读
@api_bp.route('/notifications/read-all', methods=['POST'])
@login_required
def mark_all_notifications_read():
    try:
        # 获取当前用户ID
        user_id = session.get('user_id')

        # 查找所有未读通知
        notifications = Notification.query.filter_by(user_id=user_id, is_read=False).all()

        # 标记为已读
        for notification in notifications:
            notification.is_read = True

        db.session.commit()

        return jsonify({'success': True, 'message': '所有通知已标记为已读'})

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'标记通知失败: {str(e)}'}), 500

# 创建测试通知（仅用于开发测试）
@api_bp.route('/notifications/test', methods=['POST'])
@login_required
def create_test_notification():
    try:
        # 获取当前用户ID
        user_id = session.get('user_id')

        # 创建一个测试通知
        notification = Notification(
            user_id=user_id,
            title="测试通知",
            message="这是一条测试通知，用于验证通知功能是否正常工作。",
            type="system_notification",
            created_at=date.today(),
            is_read=False
        )

        db.session.add(notification)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': '测试通知已创建',
            'notification': {
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'created_at': notification.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'创建测试通知失败: {str(e)}'}), 500

# 获取医生预约列表（适用于表格显示）
@api_bp.route('/doctor/appointments', methods=['GET'])
@login_required
def get_doctor_appointments_table():
    try:
        # 验证用户是医生
        role = session.get('role')
        if role != 'doctor':
            return jsonify({"status": "error", "message": "只有医生能访问此接口"}), 403

        # 获取当前医生ID
        doctor_id = session.get('user_id')

        # 查询该医生的所有预约
        appointments = Appointment.query.filter_by(doctor_id=doctor_id).order_by(
            Appointment.created_at.desc()
        ).all()

        # 准备返回数据
        result = []
        for appointment in appointments:
            # 获取患者信息
            patient = Patient.query.get(appointment.patient_id)
            patient_name = patient.name if patient else "未知患者"

            # 格式化数据，确保枚举字段返回字符串而不是对象
            result.append({
                'id': appointment.appointment_id,
                'patient_id': appointment.patient_id,
                'patient_name': patient_name,
                'appointment_type': appointment.appointment_type.display_name, # 直接返回中文显示名
                'department': appointment.department.display_name, # 直接返回中文显示名
                'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                'time_slot': appointment.time_slot.display_name, # 直接返回中文显示名
                'status': appointment.status.display_name, # 直接返回中文显示名
                'symptoms': appointment.symptoms,
                'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S') if appointment.created_at else '',
                'code': appointment.code
            })

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        return jsonify({"status": "error", "message": f"获取预约列表失败: {str(e)}"}), 500

# 全局错误处理器
@api_bp.app_errorhandler(404)
def handle_not_found(e):
    return jsonify({'error': '请求的资源不存在'}), 404

@api_bp.app_errorhandler(500)
def handle_internal_error(e):
    current_app.logger.error(f"API 500 Error: {e}")
    return jsonify({'error': '服务器内部错误', 'message': str(e)}), 500

def get_paginated_data(query, schema):
    """通用分页辅助函数"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    items = pagination.items
    data = schema.dump(items)

    return {
        'items': data,
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    }
