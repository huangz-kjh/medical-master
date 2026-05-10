from flask import render_template, session, redirect, url_for, jsonify
from db_model import db, User, Patient, BrainCTScan, ImagingReport, DoctorPatientRelation, Appointment, Notification, AppointmentStatus, MedicationRecord, PhysicalExam, NeurologicalAssessment
from datetime import date, datetime, time
from sqlalchemy import func, text, case, literal_column, and_
from sqlalchemy.orm import aliased
from .notification_service import NotificationService

def init_dashboard_routes(app):
    """
    初始化仪表板和相关API的路由。
    """

    @app.route('/')
    def index():
        """
        根路径，根据登录状态和角色重定向。
        """
        if not session.get("logged_in"):
            return render_template("public/login.html", username=None, role=None)

        if session.get("role") == 'admin':
            return redirect(url_for('admin.index')) # 假设管理员有自己的蓝图或路由

        user_id = session.get('user_id')
        user = User.query.get(user_id)

        return render_template("public/index.html",
                               username=session.get("username"),
                               role=session.get("role"),
                               patient_id=session.get("patient_id"),
                               user=user)

    @app.route('/dashboard')
    def dashboard():
        """
        渲染仪表板页面框架。
        所有动态数据将通过API异步加载。
        """
        if 'user_id' not in session:
            # 如果用户未登录，重定向到登录页面
            return redirect(url_for('auth.login'))

        # 从数据库获取当前登录用户对象
        user = User.query.get(session['user_id'])
        if not user:
            # 如果session中的用户ID无效，清空session并重定向
            session.clear()
            return redirect(url_for('auth.login'))

        # 将用户对象传递给模板
        return render_template("public/dashboard.html", current_user=user)

    @app.route('/api/dashboard/stats', methods=['GET'])
    def api_dashboard_stats():
        """
        提供仪表板顶部的核心统计数据。
        性能优化版本：将多次查询合并为一次。
        """
        if not session.get("logged_in"):
            return jsonify(status="error", message="用户未登录"), 401

        user_id = session.get('user_id')
        role = session.get('role')
        stats = {}

        try:
            # 1. 统一查询未读通知数 (这个通常与其他业务数据无关，可以单独查询)
            stats['unread_notifications'] = Notification.query.filter(
                Notification.receiver_id == user_id,
                Notification.receiver_type == role
            ).filter(Notification.is_read == False).count()

            # 2. 根据角色执行一次性的聚合查询
            if role == 'patient':
                patient_id = session.get('patient_id')
                if not patient_id:
                    return jsonify(status="error", message="患者信息不存在"), 404

                # 使用一次查询获取预约统计和下一次预约信息
                AppointmentAlias = aliased(Appointment)
                DoctorUserAlias = aliased(User)

                patient_dashboard_data = db.session.query(
                    func.count(case((Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]), Appointment.appointment_id))).label('pending_appointments'),
                    func.min(case((Appointment.status == AppointmentStatus.CONFIRMED, Appointment.appointment_date))).label('next_appointment_date')
                ).filter(Appointment.patient_id == patient_id).first()

                stats['pending_appointments'] = patient_dashboard_data.pending_appointments or 0

                if patient_dashboard_data.next_appointment_date:
                    next_appointment_details = db.session.query(
                        Appointment.time_slot,
                        Appointment.department,
                        User.real_name.label('doctor_name')
                    ).join(User, User.user_id == Appointment.doctor_id).filter(
                        Appointment.patient_id == patient_id,
                        Appointment.appointment_date == patient_dashboard_data.next_appointment_date,
                        Appointment.status == AppointmentStatus.CONFIRMED
                    ).order_by(Appointment.appointment_date).first()

                    stats['next_appointment'] = {
                        'date': patient_dashboard_data.next_appointment_date.strftime('%Y-%m-%d'),
                        'doctor': next_appointment_details.doctor_name or "未知医生",
                        'time_slot': next_appointment_details.time_slot.display_name,
                        'department': next_appointment_details.department.display_name
                    }
                else:
                    stats['next_appointment'] = None

            elif role == 'doctor':
                today = date.today()
                # 一次性查询所有医生相关的统计数据
                doctor_stats = db.session.query(
                    func.count(func.distinct(DoctorPatientRelation.patient_id)).label('my_patients'),
                    func.count(case((Appointment.status == AppointmentStatus.PENDING, Appointment.appointment_id))).label('pending_appointments'),
                    func.count(
                        case(
                            (
                                and_(
                                    func.date(Appointment.appointment_date) == today,
                                    Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
                                ),
                                Appointment.appointment_id
                            )
                        )
                    ).label('today_appointments_count')
                ).select_from(User).outerjoin(
                    DoctorPatientRelation, (User.user_id == DoctorPatientRelation.doctor_id) & (DoctorPatientRelation.is_active == True)
                ).outerjoin(
                    Appointment, User.user_id == Appointment.doctor_id
                ).filter(User.user_id == user_id).group_by(User.user_id).first()

                if doctor_stats:
                    stats['my_patients'] = doctor_stats.my_patients
                    stats['pending_appointments'] = doctor_stats.pending_appointments
                    stats['today_appointments_count'] = doctor_stats.today_appointments_count
                else:
                    stats['my_patients'] = 0
                    stats['pending_appointments'] = 0
                    stats['today_appointments_count'] = 0

            elif role == 'admin':
                # 管理员的查询通常是全表count，合并意义不大且可能更慢，但可以一次性执行
                # 这里用原生SQL可能更清晰
                sql = text("""
                    SELECT
                        (SELECT COUNT(*) FROM patient) AS total_patients,
                        (SELECT COUNT(*) FROM user WHERE role = 'doctor') AS total_doctors,
                        (SELECT COUNT(*) FROM brain_ct_scan) AS total_scans,
                        (SELECT COUNT(*) FROM imaging_report WHERE conclusion IS NULL) AS pending_reports
                """)
                admin_stats = db.session.execute(sql).first()
                stats.update(admin_stats._asdict())

            return jsonify(status="success", data=stats)

        except Exception as e:
            app.logger.error(f"获取仪表板统计数据失败: {e}", exc_info=True)
            return jsonify(status="error", message="服务器内部错误"), 500


    @app.route('/api/dashboard/recent-activity', methods=['GET'])
    def api_recent_activity():
        """
        提供最近的动态列表，如预约状态变更。
        性能优化版本。
        """
        if not session.get("logged_in"):
            return jsonify(status="error", message="用户未登录"), 401

        user_id = session.get('user_id')
        role = session.get('role')
        activity = []

        try:
            if role == 'doctor':
                # 优化：只查询需要的字段，避免不必要的数据加载
                recent_appointments = db.session.query(
                    Appointment.appointment_id,
                    Appointment.updated_at,
                    Appointment.created_at,
                    Appointment.status,
                    Patient.name.label("patient_name")
                ).join(Patient, Appointment.patient_id == Patient.patient_id)\
                .filter(Appointment.doctor_id == user_id)\
                .order_by(Appointment.updated_at.is_(None), Appointment.updated_at.desc(), Appointment.created_at.desc())\
                .limit(5).all()

                for appt in recent_appointments:
                    timestamp = appt.updated_at or appt.created_at
                    activity.append({
                        "type": "appointment",
                        "patient_name": appt.patient_name or "未知患者",
                        "date": timestamp.strftime('%Y-%m-%d %H:%M') if timestamp else "未知时间",
                        "status": appt.status.display_name if appt.status else "未知状态",
                        "id": appt.appointment_id
                    })

            elif role == 'patient':
                patient_id = session.get('patient_id')
                if patient_id:
                    # 优化：使用UNION查询合并预约和报告，避免Python中的排序
                    # 此处使用原生SQL以获得最佳性能
                    sql = text("""
                    (SELECT
                        a.updated_at as timestamp,
                        u.real_name as doctor_name,
                        LOWER(a.status) as status_value,
                        'appointment' as type
                    FROM appointment a
                    JOIN user u ON a.doctor_id = u.user_id
                    WHERE a.patient_id = :patient_id
                    ORDER BY COALESCE(a.updated_at, a.created_at) DESC
                    LIMIT 1)

                    UNION ALL

                    (SELECT
                        ir.report_date as timestamp,
                        ir.report_type as report_title,
                        NULL as status_value,
                        'report' as type
                    FROM imaging_report ir
                    WHERE ir.patient_id = :patient_id
                    ORDER BY ir.report_date DESC
                    LIMIT 1)

                    ORDER BY timestamp DESC
                    LIMIT 1
                    """)

                    result = db.session.execute(sql, {"patient_id": patient_id}).fetchall()

                    for row in result:
                        if row.type == 'appointment':
                            # 获取状态显示名称
                            status_display = "未知状态"
                            if row.status_value:
                                try:
                                    # 将字符串转换为AppointmentStatus枚举
                                    enum_status = AppointmentStatus(row.status_value)
                                    status_display = enum_status.display_name
                                except ValueError:
                                    # 手动处理特殊情况
                                    status_map = {
                                        'pending': '待确认',
                                        'confirmed': '已确认',
                                        'completed': '已完成',
                                        'cancelled': '已取消',
                                        'missed': '未到诊',
                                        'rejected': '已拒绝'
                                    }
                                    status_display = status_map.get(row.status_value.lower(), str(row.status_value))

                            activity.append({
                                "type": "appointment",
                                "timestamp": row.timestamp,
                                "doctor_name": row.doctor_name or "未知医生",
                                "status_display": status_display
                            })
                        elif row.type == 'report':
                            activity.append({
                                "type": "report",
                                "timestamp": row.timestamp,
                                "report_title": row.report_title or "无标题报告"
                            })

                    # 格式化时间
                    for item in activity:
                        if item.get('timestamp'):
                            item['timestamp'] = item['timestamp'].strftime('%Y-%m-%d %H:%M')

            return jsonify(status="success", data=activity)

        except Exception as e:
            app.logger.error(f"获取最近动态失败: {e}")
            return jsonify(status="error", message="服务器内部错误"), 500

    @app.route('/api/dashboard/charts', methods=['GET'])
    def api_dashboard_charts():
        """
        提供 ECharts 图表所需的数据。
        性能优化版本。
        """
        if not session.get("logged_in"):
            return jsonify(status="error", message="用户未登录"), 401

        user_id = session.get('user_id')
        role = session.get('role')
        charts_data = {}

        try:
            if role == 'doctor':
                # 优化：使用缓存或减少查询复杂度
                patient_status_counts = db.session.query(
                    Patient.status, func.count(Patient.patient_id)
                ).join(DoctorPatientRelation, Patient.patient_id == DoctorPatientRelation.patient_id)\
                .filter(DoctorPatientRelation.doctor_id == user_id, DoctorPatientRelation.is_active == True)\
                .group_by(Patient.status).all()

                charts_data['patient_status'] = [{'name': status, 'value': count} for status, count in patient_status_counts if status]

                appointment_type_stats = db.session.query(
                    Appointment.appointment_type, func.count(Appointment.appointment_id)
                ).filter(Appointment.doctor_id == user_id).group_by(Appointment.appointment_type).all()

                charts_data['appointment_types'] = [{'name': appt_type.display_name, 'value': count} for appt_type, count in appointment_type_stats]

            elif role == 'admin':
                # 这些查询可能较慢，考虑使用缓存
                appointment_type_stats = db.session.query(
                    Appointment.appointment_type, func.count(Appointment.appointment_id)
                ).group_by(Appointment.appointment_type).all()
                charts_data['appointment_types'] = [{'name': appt_type.display_name, 'value': count} for appt_type, count in appointment_type_stats]

                patient_status_counts = db.session.query(
                    Patient.status, func.count(Patient.patient_id)
                ).group_by(Patient.status).all()
                charts_data['patient_status'] = [{'name': status, 'value': count} for status, count in patient_status_counts if status]

            elif role == 'patient':
                patient_id = session.get('patient_id')
                if patient_id:
                    appointment_status_stats = db.session.query(
                        Appointment.status, func.count(Appointment.appointment_id)
                    ).filter(Appointment.patient_id == patient_id).group_by(Appointment.status).all()

                    charts_data['appointment_status'] = [{'name': status.display_name, 'value': count} for status, count in appointment_status_stats]

            return jsonify(status="success", data=charts_data)

        except Exception as e:
            app.logger.error(f"获取仪表板图表数据失败: {e}")
            return jsonify(status="error", message="服务器内部错误"), 500

    # 添加一个新的API端点，用于延迟加载患者的健康数据
    @app.route('/api/dashboard/health-data', methods=['GET'])
    def api_health_data():
        """
        提供患者的健康数据（用药、体检、神经评估、影像报告）。
        这些数据不是立即需要的，可以延迟加载。
        """
        if not session.get("logged_in") or session.get("role") != 'patient':
            return jsonify(status="error", message="未授权访问"), 401

        patient_id = session.get('patient_id')
        if not patient_id:
            return jsonify(status="error", message="无效的患者ID"), 400

        health_data = {}

        try:
            # 最新医疗记录 - 只查询必要字段
            latest_medication = db.session.query(
                MedicationRecord.medication_name,
                MedicationRecord.dosage,
                MedicationRecord.frequency,
                MedicationRecord.start_date
            ).filter(
                MedicationRecord.patient_id == patient_id
            ).order_by(MedicationRecord.start_date.desc()).first()

            if latest_medication:
                health_data['latest_medication'] = {
                    'name': latest_medication.medication_name,
                    'dosage': latest_medication.dosage,
                    'frequency': latest_medication.frequency,
                    'start_date': latest_medication.start_date.strftime('%Y-%m-%d') if latest_medication.start_date else '未知'
                }
            else:
                health_data['latest_medication'] = None

            # 最新体检数据 - 只查询必要字段
            latest_exam = db.session.query(
                PhysicalExam.exam_date,
                PhysicalExam.heart_rate,
                PhysicalExam.blood_pressure_systolic,
                PhysicalExam.blood_pressure_diastolic,
                PhysicalExam.temperature
            ).filter(
                PhysicalExam.patient_id == patient_id
            ).order_by(PhysicalExam.exam_date.desc()).first()

            if latest_exam:
                health_data['latest_exam'] = {
                    'date': latest_exam.exam_date.strftime('%Y-%m-%d'),
                    'heart_rate': latest_exam.heart_rate,
                    'blood_pressure': f"{latest_exam.blood_pressure_systolic}/{latest_exam.blood_pressure_diastolic}" if latest_exam.blood_pressure_systolic and latest_exam.blood_pressure_diastolic else "未记录",
                    'temperature': latest_exam.temperature
                }
            else:
                health_data['latest_exam'] = None

            # 最新神经评估 - 只查询必要字段
            latest_assessment = db.session.query(
                NeurologicalAssessment.assessment_date,
                NeurologicalAssessment.mmse_score,
                NeurologicalAssessment.moca_score,
                NeurologicalAssessment.gcs_score
            ).filter(
                NeurologicalAssessment.patient_id == patient_id
            ).order_by(NeurologicalAssessment.assessment_date.desc()).first()

            if latest_assessment:
                health_data['latest_assessment'] = {
                    'date': latest_assessment.assessment_date.strftime('%Y-%m-%d'),
                    'mmse_score': latest_assessment.mmse_score,
                    'moca_score': latest_assessment.moca_score,
                    'gcs_score': latest_assessment.gcs_score
                }
            else:
                health_data['latest_assessment'] = None

            # 最新影像报告 - 只查询必要字段
            latest_report = db.session.query(
                ImagingReport.report_date,
                ImagingReport.report_type,
                ImagingReport.conclusion
            ).filter(
                ImagingReport.patient_id == patient_id
            ).order_by(ImagingReport.report_date.desc()).first()

            if latest_report:
                health_data['latest_report'] = {
                    'date': latest_report.report_date.strftime('%Y-%m-%d') if latest_report.report_date else '未知',
                    'type': latest_report.report_type,
                    'conclusion': latest_report.conclusion[:100] + '...' if latest_report.conclusion and len(latest_report.conclusion) > 100 else latest_report.conclusion or '暂无结论'
                }
            else:
                health_data['latest_report'] = None

            return jsonify(status="success", data=health_data)

        except Exception as e:
            app.logger.error(f"获取健康数据失败: {e}")
            return jsonify(status="error", message="服务器内部错误"), 500
