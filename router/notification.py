from flask import jsonify, request, session
from db_model import db, User, Notification, NotificationType
from router.auth import login_required
from .notification_service import NotificationService
import logging

def init_notification_routes(app):
    @app.route('/api/notifications', methods=['GET'])
    @login_required
    def get_notifications():
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'message': '用户未找到'}), 404

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)

        # 构建基础查询
        if user.role == 'patient':
            query = Notification.query.filter_by(receiver_type='patient', receiver_id=user.patient_id)
        else: # doctor or admin
            query = Notification.query.filter_by(receiver_type=user.role, receiver_id=user.user_id)

        # 获取分页结果
        paginated_notifications = query.order_by(Notification.created_at.desc()).paginate(page=page, per_page=limit, error_out=False)
        notifications = paginated_notifications.items

        # 获取总未读数
        total_unread = NotificationService.get_unread_count(user)

        notifications_data = []
        for n in notifications:
            notifications_data.append({
                'id': n.id,
                'type': n.type.name,
                'type_display': n.type.display_name,
                'title': n.title,
                'message': n.message,
                'action_url': n.action_url,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'is_read': n.is_read,
                'priority': n.priority
            })

        return jsonify({
            'notifications': notifications_data,
            'total_pages': paginated_notifications.pages,
            'current_page': paginated_notifications.page,
            'total_items': paginated_notifications.total,
            'unread_count': total_unread
        })

    @app.route('/api/notifications/<int:notification_id>/read', methods=['POST'])
    @login_required
    def mark_notification_as_read(notification_id):
        user = User.query.get(session['user_id'])
        notification = Notification.query.get_or_404(notification_id)

        # 验证权限
        is_owner = (user.role == notification.receiver_type and
                    ((user.role == 'patient' and user.patient_id == notification.receiver_id) or
                     (user.role != 'patient' and user.user_id == notification.receiver_id)))

        if not is_owner:
            return jsonify({'message': '无权操作此通知'}), 403

        notification.is_read = True
        db.session.commit()

        # 返回新的未读计数
        new_unread_count = NotificationService.get_unread_count(user)
        return jsonify({'message': '标记已读成功', 'unread_count': new_unread_count})

    @app.route('/api/notifications/read-all', methods=['POST'])
    @login_required
    def mark_all_as_read():
        user = User.query.get(session['user_id'])
        if not user:
            return jsonify({'message': '用户未找到'}), 404

        if user.role == 'patient':
            Notification.query.filter_by(receiver_type='patient', receiver_id=user.patient_id, is_read=False).update({'is_read': True})
        else: # doctor or admin
            Notification.query.filter_by(receiver_type=user.role, receiver_id=user.user_id, is_read=False).update({'is_read': True})

        db.session.commit()
        return jsonify({'message': '全部标记已读成功', 'unread_count': 0})

    @app.route('/api/notifications/count', methods=['GET'])
    @login_required
    def get_notification_count():
        user = User.query.get(session.get('user_id'))
        if not user:
            return jsonify({'total_unread': 0})

        total_unread = NotificationService.get_unread_count(user)
        return jsonify({'total_unread': total_unread})
