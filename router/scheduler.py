import threading
import time
import schedule
import datetime
import atexit
from flask import Flask
from db_model import db, User, Appointment, Notification, AppointmentStatus, NotificationType
from sqlalchemy import and_, or_
from .notification_service import NotificationService

class AppointmentScheduler:
    """预约提醒调度器"""

    def __init__(self, app=None):
        self.app = app
        self.scheduler_thread = None
        self.stop_flag = False

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """初始化应用"""
        self.app = app

        # 设置定时任务
        schedule.clear()
        schedule.every().day.at("08:00").do(self.send_appointment_reminders)  # 每天8点执行
        schedule.every().day.at("20:00").do(self.send_doctor_next_day_appointments)  # 每天20点执行

        # 启动调度线程
        self.start_scheduler()

        # 应用关闭时停止调度器
        # app.teardown_appcontext(lambda exc: self.stop_scheduler())
        atexit.register(self.stop_scheduler)

    def start_scheduler(self):
        """启动调度线程"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.stop_flag = False
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.daemon = True
            self.scheduler_thread.start()
            print("[INFO] 预约提醒调度器已启动")

    def stop_scheduler(self):
        """停止调度线程"""
        self.stop_flag = True
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            # self.scheduler_thread.join(timeout=3)
            print("[INFO] 预约提醒调度器已停止")

    def _run_scheduler(self):
        """运行调度器"""
        while not self.stop_flag:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次

    def send_appointment_reminders(self):
        """发送预约前24小时提醒"""
        print("[INFO] 执行预约提醒任务...")
        with self.app.app_context():
            try:
                # 获取明天的日期
                tomorrow = datetime.date.today() + datetime.timedelta(days=1)

                # 查询明天的所有已确认预约
                appointments = Appointment.query.filter(
                    and_(
                        Appointment.appointment_date == tomorrow,
                        Appointment.status == AppointmentStatus.CONFIRMED
                    )
                ).all()

                sent_count = 0
                for appointment in appointments:
                    # 获取患者用户
                    patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                    if not patient_user:
                        continue

                    # 使用服务创建通知
                    NotificationService.create_notification(
                        receiver_type='patient',
                        receiver_id=appointment.patient_id,
                        notification_type=NotificationType.APPOINTMENT_REMINDER,
                        related_id=appointment.appointment_id
                    )
                    sent_count += 1

                db.session.commit() # 事务提交由服务内部处理，这里可以移除或保留
                print(f"[INFO] 已发送{sent_count}条预约提醒")

            except Exception as e:
                db.session.rollback()
                print(f"[ERROR] 发送预约提醒失败: {str(e)}")

    def send_doctor_next_day_appointments(self):
        """发送医生次日预约清单"""
        print("[INFO] 执行医生次日预约清单任务...")
        with self.app.app_context():
            try:
                # 获取明天的日期
                tomorrow = datetime.date.today() + datetime.timedelta(days=1)

                # 获取所有医生ID列表
                doctors = User.query.filter_by(role='doctor').all()

                sent_count = 0
                for doctor in doctors:
                    # 查询该医生明天的所有预约
                    appointments = Appointment.query.filter(
                        and_(
                            Appointment.appointment_date == tomorrow,
                            Appointment.doctor_id == doctor.user_id,
                            Appointment.status.in_([AppointmentStatus.CONFIRMED, AppointmentStatus.PENDING])
                        )
                    ).order_by(Appointment.time_slot).all()

                    if not appointments:
                        continue  # 没有预约则跳过

                    # 生成预约列表消息
                    appointment_list = "\n".join([
                        f"{i+1}. {appt.time_slot.display_name} - "
                        f"患者: {User.query.filter_by(patient_id=appt.patient_id).first().real_name if User.query.filter_by(patient_id=appt.patient_id).first() else '未知'} "
                        f"({appt.appointment_type.display_name}) - "
                        f"{appt.status.display_name}"
                        for i, appt in enumerate(appointments)
                    ])

                    # 使用服务创建通知
                    NotificationService.create_notification(
                        receiver_type='doctor',
                        receiver_id=doctor.user_id,
                        notification_type=NotificationType.SYSTEM_ALERT, # 可以为此创建一个更具体的类型
                        title=f"明日预约清单 ({tomorrow.strftime('%Y-%m-%d')})",
                        message=f"您明天有{len(appointments)}个预约:\n\n{appointment_list}"
                    )
                    sent_count += 1

                db.session.commit()
                print(f"[INFO] 已发送{sent_count}条医生预约清单")

            except Exception as e:
                db.session.rollback()
                print(f"[ERROR] 发送医生预约清单失败: {str(e)}")

    def manual_run(self, task_name):
        """手动运行特定任务(用于测试)"""
        if task_name == "patient_reminder":
            self.send_appointment_reminders()
        elif task_name == "doctor_summary":
            self.send_doctor_next_day_appointments()
        else:
            print(f"[ERROR] 未知任务: {task_name}")

# 创建调度器实例
scheduler = AppointmentScheduler()
