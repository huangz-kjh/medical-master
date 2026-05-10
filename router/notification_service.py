from datetime import datetime
from flask import url_for, session
from db_model import db, Notification, NotificationType, User

class NotificationService:
    @staticmethod
    def create_notification(
        receiver_type,
        receiver_id,
        notification_type,
        related_id=None,
        sender_id=None,
        title=None,
        message=None
    ):
        """
        统一的通知创建服务

        Args:
            receiver_type (str): 'patient' or 'doctor' or 'admin'
            receiver_id (int): 接收者ID
            notification_type (NotificationType): 通知类型枚举
            related_id (int, optional): 关联对象ID. Defaults to None.
            sender_id (int, optional): 发送者用户ID. Defaults to None.
            title (str, optional): 自定义标题. Defaults to None.
            message (str, optional): 自定义消息. Defaults to None.

        Returns:
            Notification: The created notification object.
        """
        # 如果没有提供发送者ID，但会话中存在，则自动填充
        if sender_id is None and session.get('user_id'):
            sender_id = session.get('user_id')

        # 生成通知内容和跳转链接
        content = NotificationService._generate_content(notification_type, related_id)

        # 允许传入的参数覆盖自动生成的内容
        final_title = title or content.get('title')
        final_message = message or content.get('message')
        action_url = content.get('action_url')

        if not final_title or not final_message:
            # 这是一个安全检查，防止内容生成失败
            print(f"Warning: Could not generate content for notification type {notification_type.name}")
            return None

        notification = Notification(
            receiver_type=receiver_type,
            receiver_id=receiver_id,
            sender_type='user' if sender_id else 'system',
            sender_id=sender_id,
            type=notification_type,
            title=final_title,
            message=final_message,
            related_id=related_id,
            action_url=action_url,
            created_at=datetime.now(),
        )
        db.session.add(notification)
        db.session.commit()
        return notification

    @staticmethod
    def _generate_content(notification_type, related_id):
        """
        根据通知类型和关联ID生成标题、消息和URL
        """
        # 默认内容
        content = {'title': '新通知', 'message': '您有一条新消息。', 'action_url': '#'}

        if related_id:
            if notification_type in [
                NotificationType.APPOINTMENT_NEW,
                NotificationType.APPOINTMENT_CONFIRMED,
                NotificationType.APPOINTMENT_CANCELLED,
                NotificationType.APPOINTMENT_COMPLETED,
                NotificationType.APPOINTMENT_REMINDER
            ]:
                # 假设有一个预约详情页的路由
                content['action_url'] = url_for('appointment.view_appointment', appointment_id=related_id, _external=True)

            elif notification_type == NotificationType.REPORT_READY:
                # 假设有一个报告详情页的路由
                content['action_url'] = url_for('medical_records.view_report', report_id=related_id, _external=True)

            elif notification_type == NotificationType.CHAT_MESSAGE:
                # 假设聊天页面路由
                content['action_url'] = url_for('chat_service.chat_view', session_id=related_id, _external=True)

        # 根据类型生成标题和消息
        if notification_type == NotificationType.APPOINTMENT_NEW:
            content['title'] = '新的预约申请'
            content['message'] = '您有一个新的预约申请需要处理。'
        elif notification_type == NotificationType.APPOINTMENT_CONFIRMED:
            content['title'] = '预约已确认'
            content['message'] = '您的预约已被确认，请准时参加。'
        elif notification_type == NotificationType.APPOINTMENT_CANCELLED:
            content['title'] = '预约已取消'
            content['message'] = '您的一个预约已被取消。'
        elif notification_type == NotificationType.APPOINTMENT_COMPLETED:
            content['title'] = '就诊已完成'
            content['message'] = '您最近的一次就诊已完成。'
        elif notification_type == NotificationType.REPORT_READY:
            content['title'] = '您的报告已生成'
            content['message'] = '您有一份新的医疗报告已生成，请及时查看。'
        elif notification_type == NotificationType.SYSTEM_ALERT:
            content['title'] = '系统警告'
            content['message'] = '系统检测到异常，请关注。'

        return content

    @staticmethod
    def get_unread_count(user):
        """
        获取指定用户的未读通知数量

        Args:
            user (User): The user object from session or query.

        Returns:
            int: The count of unread notifications.
        """
        if user.role == 'patient':
            # 患者使用 patient_id 作为 receiver_id
            return Notification.query.filter_by(
                receiver_type='patient',
                receiver_id=user.patient_id,
                is_read=False
            ).count()
        elif user.role == 'doctor' or user.role == 'admin':
            # 医生和管理员使用 user_id
            return Notification.query.filter_by(
                receiver_type=user.role,
                receiver_id=user.user_id,
                is_read=False
            ).count()
        return 0
