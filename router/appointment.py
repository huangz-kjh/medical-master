from flask import render_template, request, redirect, url_for, session, jsonify, flash
from db_model import db, User, Patient, Appointment, DoctorPatientRelation, Notification, AppointmentStatus, AppointmentType, Department, TimeSlot, NotificationType
from datetime import datetime, timedelta
from router.auth import login_required, doctor_required
import random
from sqlalchemy.orm import joinedload
from sqlalchemy import case, desc
from flask import Blueprint
from flask import current_app

appointment_bp = Blueprint('appointment', __name__)

def generate_appointment_code():
    """生成预约编号"""
    now = datetime.now()
    date_part = now.strftime('%Y%m%d')
    random_part = str(random.randint(1000, 9999))
    return f"YY{date_part}{random_part}"


def _build_appointment_query_order(query):
    """
    构建预约查询的排序逻辑 (MySQL 兼容版).
    - 状态优先级: 待确认 > 已确认 > 其他
    - 主要排序: 按预约日期倒序 (最近的在前, NULL值在后)
    - 次要排序: 按时间段升序 (早的在前, NULL值在后)
    - 最终排序: 按ID倒序, 确保分页稳定
    """
    order_logic = [
        case(
            (Appointment.status == 'pending', 0),
            (Appointment.status == 'confirmed', 1),
            else_=2
        ).label('status_order'),
        # MySQL中 DESC 默认将 NULL 排在最后
        desc(Appointment.appointment_date),
        # MySQL中 ASC 默认将 NULL 排在最前, 使用 `IS NULL` 将其排在最后
        Appointment.time_slot.is_(None),
        Appointment.time_slot.asc(),
        desc(Appointment.appointment_id)
    ]
    return query.order_by(*order_logic)


def init_appointment_routes(app):
    """初始化预约相关的路由"""

    # 关键修复：在这里注册本文件定义的蓝图，使其生效
    app.register_blueprint(appointment_bp)

    @app.route('/api/v2/doctors', methods=['GET'])
    @login_required
    def get_doctors_list_v2():
        """获取医生列表的API"""
        try:
            doctors = User.query.filter_by(role='doctor').all()
            doctor_list = [{'id': d.user_id, 'name': d.real_name} for d in doctors]
            return jsonify(status='success', data=doctor_list)
        except Exception as e:
            current_app.logger.error(f"获取医生列表时发生错误: {e}", exc_info=True)
            return jsonify(status='error', message='服务器内部错误'), 500

    @app.route('/api/appointments/doctor-paginated', methods=['GET'])
    @login_required
    def get_doctor_appointments_paginated():
        """
        获取医生预约列表（分页、可搜索、可筛选）
        """
        doctor_id = session.get('user_id')
        if not doctor_id:
            return jsonify({"status": "error", "message": "无法获取医生ID，请重新登录"}), 401

        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 10, type=int)
        search_query = request.args.get('q', '').strip()
        status_filter = request.args.get('status', '').strip()
        date_range_str = request.args.get('date_range', '').strip()

        query = Appointment.query.filter(Appointment.doctor_id == doctor_id)

        if status_filter:
            query = query.filter(Appointment.status == status_filter)

        if search_query:
            query = query.join(Patient, Appointment.patient_id == Patient.patient_id).filter(Patient.name.like(f'%{search_query}%'))

        if date_range_str:
            try:
                start_date_str, end_date_str = date_range_str.split(' - ')
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
                query = query.filter(Appointment.appointment_date.between(start_date, end_date))
            except (ValueError, IndexError):
                pass

        query = _build_appointment_query_order(query)

        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        appointments = pagination.items

        appointments_data = []
        for appt in appointments:
            patient = Patient.query.get(appt.patient_id)
            appointments_data.append({
                'appointment_id': appt.appointment_id,
                'patient_name': patient.name if patient else '未知患者',
                'patient_id': appt.patient_id,
                'appointment_date': appt.appointment_date.strftime('%Y-%m-%d') if appt.appointment_date else '无日期',
                'time_slot': {
                    'value': appt.time_slot.value,
                    'display_name': appt.time_slot.display_name
                } if appt.time_slot else None,
                'appointment_type': {
                    'value': appt.appointment_type.value,
                    'display_name': appt.appointment_type.display_name
                } if appt.appointment_type else None,
                'status': {
                    'value': appt.status.value,
                    'display_name': appt.status.display_name
                } if appt.status else None,
                'symptoms': appt.symptoms or '无',
                'created_at': appt.created_at.strftime('%Y-%m-%d %H:%M:%S') if appt.created_at else '未知时间',
            })

        return jsonify({
            'status': 'success',
            'data': appointments_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total_items': pagination.total,
                'total_pages': pagination.pages
            }
        })

    @app.route('/appointments')
    @login_required
    def appointment_list():
        """
        Renders the patient's appointments page, supporting different views (active, upcoming, past)
        and pagination. Handles both full page loads and AJAX requests for partial updates.
        """
        status_group = request.args.get('status_group', 'active')
        page = request.args.get('page', 1, type=int)
        user_id = session.get('user_id')
        patient_id = session.get('patient_id')

        # Define allowed 'per_page' values and get from request, with validation
        allowed_per_page = [5, 10, 20, 50]
        per_page = request.args.get('per_page', 10, type=int)
        if per_page not in allowed_per_page:
            per_page = 10

        base_query = db.session.query(Appointment).filter(
            Appointment.patient_id == patient_id
        ).options(
            joinedload(Appointment.doctor)
        )

        status_mapping = {
            'active': [AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED],
            'completed': [AppointmentStatus.COMPLETED],
            'cancelled': [AppointmentStatus.CANCELLED, AppointmentStatus.REJECTED]
        }

        query = base_query.filter(Appointment.status.in_(status_mapping.get(status_group, [])))

        pagination = query.order_by(Appointment.appointment_date.desc(), Appointment.appointment_id.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        template_to_render = (
            'patient/_appointments_content.html'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            else 'patient/appointment.html'
        )

        return render_template(
            template_to_render,
            pagination=pagination,
            status_group=status_group,
            per_page=per_page,
            allowed_per_page=allowed_per_page,
            role='patient'
        )

    @app.route('/appointments/book', methods=['GET', 'POST'])
    @login_required
    def book_appointment():
        """预约医生页面和处理"""
        patient_id = session.get('patient_id')
        user_id = session.get('user_id')
        role = session.get('role')

        # 验证当前用户是否有权限预约
        if not patient_id and role != 'admin':
            flash('只有患者可以预约医生', 'error')
            return redirect(url_for('appointment_list'))

        if request.method == 'POST':
            # 获取表单数据
            doctor_id = request.form.get('doctor_id')
            date_str = request.form.get('date')
            time_slot = request.form.get('time_slot')
            symptoms = request.form.get('description')
            appointment_type = request.form.get('appointment_type')
            department = request.form.get('department', 'neurology')  # 默认为神经科

            # 如果是管理员，可以为他人预约
            if role == 'admin':
                patient_id = request.form.get('patient_id')
                if not patient_id:
                    flash('请选择患者', 'error')
                    return redirect(url_for('book_appointment'))

            # 验证表单数据
            if not all([doctor_id, date_str, time_slot, appointment_type]):
                flash('请填写所有必填字段', 'error')
                return redirect(url_for('book_appointment'))

            # 检查预约时间是否有效（不在过去）
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if appointment_date < datetime.now().date():
                flash('预约日期不能在过去', 'error')
                return redirect(url_for('book_appointment'))

            # 检查医生和时间段是否已被预约
            existing_appointment = Appointment.query.filter_by(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                time_slot=TimeSlot(time_slot)
            ).first()

            if existing_appointment:
                flash('该时间段已被预约，请选择其他时间', 'error')
                return redirect(url_for('book_appointment'))

            try:
                # 创建预约记录
                appointment = Appointment(
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    appointment_date=appointment_date,
                    time_slot=TimeSlot(time_slot),
                    symptoms=symptoms,
                    appointment_type=AppointmentType(appointment_type),
                    department=Department(department),
                    status=AppointmentStatus.PENDING,
                    code=generate_appointment_code()
                )
                db.session.add(appointment)

                # 检查医患关系是否已存在，不存在则创建
                doctor_patient = DoctorPatientRelation.query.filter_by(
                    doctor_id=doctor_id,
                    patient_id=patient_id
                ).first()

                if not doctor_patient:
                    # 创建新的医患关系
                    doctor_patient = DoctorPatientRelation(
                        doctor_id=doctor_id,
                        patient_id=patient_id,
                        start_date=datetime.now(),
                        is_active=True,
                        relation_type='主治' if appointment_type == 'regular' else '会诊',
                        next_visit_date=appointment_date
                    )
                    db.session.add(doctor_patient)
                else:
                    # 更新已有医患关系的下次随访日期
                    doctor_patient.next_visit_date = appointment_date
                    doctor_patient.is_active = True

                # 更新患者状态为待就诊
                patient = Patient.query.get(patient_id)
                if patient and patient.status == '新患者':
                    patient.status = '待就诊'

                # 创建通知给医生
                try:
                    # 获取患者信息
                    patient_name = patient.name if patient else "患者"

                    # 发送通知给医生
                    notification = Notification(
                        receiver_type='doctor',
                        receiver_id=doctor_id,
                        sender_id=user_id,
                        title="新预约请求",
                        message=f"患者 {patient_name} 请求预约，日期：{appointment_date.strftime('%Y-%m-%d')}",
                        type=NotificationType.APPOINTMENT_NEW,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                except Exception as notification_error:
                    # 通知创建失败不应影响整个流程
                    current_app.logger.error(f"创建新预约通知失败: {str(notification_error)}")

                db.session.commit()
                flash('预约成功！请等待医生确认', 'success')
                return redirect(url_for('appointment_list'))
            except Exception as e:
                db.session.rollback()
                flash(f'预约失败：{str(e)}', 'error')
                return redirect(url_for('book_appointment'))

        # 获取可预约的医生列表
        doctors = User.query.filter_by(role='doctor').all()

        # 如果是管理员，获取患者列表
        patients = None
        if role == 'admin':
            patients = Patient.query.all()

        # 准备可用的时间段
        time_slots = [slot.value for slot in TimeSlot]

        # 预约类型
        appointment_types = [type.value for type in AppointmentType]

        # 科室列表
        departments = [dept.value for dept in Department]

        return render_template('patient/book_appointment.html',
                               doctors=doctors,
                               patients=patients,
                               time_slots=time_slots,
                               appointment_types=appointment_types,
                               departments=departments,
                               role=role)

    @app.route('/appointments/<int:appointment_id>/cancel', methods=['POST'])
    @login_required
    def cancel_appointment(appointment_id):
        """取消预约"""
        appointment = Appointment.query.get_or_404(appointment_id)
        user_id = session.get('user_id')
        role = session.get('role')
        patient_id = session.get('patient_id')

        # 验证权限（只有自己的预约、管理员或相关医生可以取消）
        if role != 'admin' and appointment.doctor_id != user_id and appointment.patient_id != patient_id:
            flash('您无权取消此预约', 'error')
            return redirect(url_for('appointment_list'))

        try:
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = datetime.now()
            if role == 'patient':
                appointment.cancelled_by = 'patient'
            elif role == 'doctor':
                appointment.cancelled_by = 'doctor'
            else:
                appointment.cancelled_by = 'admin'

            # 获取取消原因（Web表单可能没有，设为空字符串）
            cancel_reason = request.form.get('reason', '')
            if cancel_reason:
                appointment.cancel_reason = cancel_reason

            # 创建通知
            try:
                # 如果是患者取消，通知医生
                if role == 'patient' and appointment.doctor_id:
                    # 获取患者信息
                    patient = Patient.query.get(patient_id)
                    patient_name = patient.name if patient else "患者"
                    message = f"患者 {patient_name} 取消了您的预约 (预约日期: {appointment.appointment_date.strftime('%Y-%m-%d')})"
                    if cancel_reason:
                        message += f" 原因: {cancel_reason}"

                    notification = Notification(
                        receiver_type='doctor',
                        receiver_id=appointment.doctor_id,
                        sender_id=user_id,
                        title="预约已取消",
                        message=message,
                        type=NotificationType.APPOINTMENT_CANCELLED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)

                # 如果是医生或管理员取消，通知患者
                elif role in ['doctor', 'admin'] and appointment.patient_id:
                    patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                    if patient_user:
                        # 获取医生信息
                        doctor_name = "管理员"
                        if role == 'doctor':
                            doctor = User.query.get(user_id)
                            doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                        message = f"您的预约已被 {doctor_name} 取消 (预约日期: {appointment.appointment_date.strftime('%Y-%m-%d')})"
                        if cancel_reason:
                            message += f" 原因: {cancel_reason}"

                        notification = Notification(
                            receiver_type='patient',
                            receiver_id=patient_user.patient_id,
                            sender_id=user_id,
                            title="您的预约已被取消",
                            message=message,
                            type=NotificationType.APPOINTMENT_CANCELLED,
                            related_id=appointment.appointment_id
                        )
                        db.session.add(notification)
            except Exception as notification_error:
                # 通知创建失败不应影响整个流程
                current_app.logger.error(f"创建取消通知失败: {str(notification_error)}")

            db.session.commit()
            flash('预约已取消', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'取消预约失败：{str(e)}', 'error')

        return redirect(url_for('appointment_list'))

    @app.route('/appointments/<int:appointment_id>/confirm', methods=['POST'])
    @login_required
    def confirm_appointment(appointment_id):
        """医生确认预约 - Web接口"""
        if session.get('role') != 'doctor':
            flash('只有医生能确认预约', 'error')
            return redirect(url_for('appointment_list'))

        appointment = Appointment.query.get_or_404(appointment_id)
        doctor_id = session.get('user_id')

        # 验证是否是预约的医生
        if appointment.doctor_id != doctor_id:
            flash('您不能修改其他医生的预约', 'error')
            return redirect(url_for('doctor_appointments'))

        try:
            # 检查预约状态
            if appointment.status != '待确认' and appointment.status != 'pending' and appointment.status != AppointmentStatus.PENDING:
                flash('只有待确认状态的预约可以确认', 'error')
                return redirect(url_for('doctor_appointments'))

            # 更新预约状态
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_at = datetime.now()
            appointment.updated_at = datetime.now()
            db.session.commit()

            # 创建通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                if patient_user:
                    # 获取医生信息
                    doctor = User.query.get(doctor_id)
                    doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="预约已确认",
                        message=f"医生 {doctor_name} 已确认您的预约，日期：{appointment.appointment_date.strftime('%Y-%m-%d')}",
                        type=NotificationType.APPOINTMENT_CONFIRMED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as notification_error:
                # 通知创建失败不应影响整个流程
                current_app.logger.error(f"创建确认通知失败: {str(notification_error)}")

            flash('预约已确认', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'确认预约失败：{str(e)}', 'error')

        return redirect(url_for('doctor_appointments'))

    @app.route('/appointments/<int:appointment_id>/complete', methods=['POST'])
    @login_required
    def complete_appointment(appointment_id):
        """医生完成预约 - Web接口"""
        if session.get('role') != 'doctor':
            flash('只有医生能完成预约', 'error')
            return redirect(url_for('appointment_list'))

        appointment = Appointment.query.get_or_404(appointment_id)
        doctor_id = session.get('user_id')

        # 验证是否是预约的医生
        if appointment.doctor_id != doctor_id:
            flash('您不能修改其他医生的预约', 'error')
            return redirect(url_for('doctor_appointments'))

        try:
            # 检查预约状态
            if appointment.status != '已确认' and appointment.status != 'confirmed' and appointment.status != AppointmentStatus.CONFIRMED:
                flash('只有已确认状态的预约可以完成', 'error')
                return redirect(url_for('doctor_appointments'))

            # 获取表单数据 - Web表单和API可能略有不同
            notes = request.form.get('notes', '')
            follow_up_required = request.form.get('follow_up_required') == 'on'
            follow_up_date = request.form.get('follow_up_date', '')
            follow_up_notes = request.form.get('follow_up_notes', '')

            # 更新预约状态
            appointment.status = AppointmentStatus.COMPLETED
            appointment.completed_at = datetime.now()
            appointment.updated_at = datetime.now()

            # 添加备注
            if notes:
                appointment.notes = notes

            # 处理随访设置
            if follow_up_required:
                appointment.follow_up_required = True

                if follow_up_date:
                    try:
                        follow_up_date_obj = datetime.strptime(follow_up_date, '%Y-%m-%d').date()
                        appointment.follow_up_date = follow_up_date_obj
                    except ValueError:
                        flash('随访日期格式无效', 'error')
                        return redirect(url_for('doctor_appointments'))

                if follow_up_notes:
                    appointment.follow_up_notes = follow_up_notes

            db.session.commit()

            # 创建通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                if patient_user:
                    # 获取医生信息
                    doctor = User.query.get(doctor_id)
                    doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                    message = f"医生 {doctor_name} 已完成您的就诊，日期：{appointment.appointment_date.strftime('%Y-%m-%d')}"

                    if notes:
                        message += f" 备注: {notes[:50]}"
                        if len(notes) > 50:
                            message += "..."

                    if follow_up_required and appointment.follow_up_date:
                        message += f" 需要随访，日期: {appointment.follow_up_date.strftime('%Y-%m-%d')}"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="就诊已完成",
                        message=message,
                        type=NotificationType.APPOINTMENT_COMPLETED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as notification_error:
                # 通知创建失败不应影响整个流程
                current_app.logger.error(f"创建就诊完成通知失败: {str(notification_error)}")

            flash('预约已完成', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'完成预约失败：{str(e)}', 'error')

        return redirect(url_for('doctor_appointments'))

    @app.route('/api/appointments/<int:appointment_id>/confirm', methods=['POST'])
    @login_required
    def confirm_appointment_api(appointment_id):
        """API: 确认预约"""
        try:
            user_id = session.get('user_id')
            role = session.get('role')

            # 添加详细调试日志
            print(f"开始确认预约 - ID: {appointment_id}, 用户ID: {user_id}, 角色: {role}")

            if role != 'doctor':
                print(f"确认预约失败 - 非医生角色: {role}")
                return jsonify({"status": "error", "message": "只有医生能确认预约"}), 403

            appointment = Appointment.query.get_or_404(appointment_id)
            doctor_id = session.get('user_id')

            # 记录预约状态信息
            print(f"预约状态: {appointment.status}, 类型: {type(appointment.status)}")
            if isinstance(appointment.status, AppointmentStatus):
                print(f"枚举值: {appointment.status.value}, 显示名称: {appointment.status.display_name}")

            # 验证是否是预约的医生
            if appointment.doctor_id != doctor_id:
                print(f"确认预约失败 - 医生ID不匹配: 预约医生ID {appointment.doctor_id} vs 当前医生ID {doctor_id}")
                return jsonify({"status": "error", "message": "您不能修改其他医生的预约"}), 403

            # 检查预约状态 - 修复状态检查逻辑
            is_pending = False

            # 处理不同类型的状态值
            if isinstance(appointment.status, AppointmentStatus):
                is_pending = (appointment.status == AppointmentStatus.PENDING)
                print(f"检查AppointmentStatus枚举类型: {is_pending}")
            elif isinstance(appointment.status, str):
                is_pending = (appointment.status == '待确认' or appointment.status == 'pending')
                print(f"检查字符串类型状态: {is_pending}")
            else:
                # 尝试将状态转换为字符串进行比较
                status_str = str(appointment.status)
                is_pending = (status_str == '待确认' or status_str == 'pending' or status_str == 'AppointmentStatus.PENDING')
                print(f"检查其他类型状态: {is_pending}, 状态字符串: {status_str}")

            if not is_pending:
                print(f"确认预约失败 - 状态不是待确认: {appointment.status}")
                return jsonify({"status": "error", "message": "只有待确认状态的预约可以确认"}), 400

            # 更新预约状态
            appointment.status = AppointmentStatus.CONFIRMED
            appointment.confirmed_at = datetime.now()
            appointment.updated_at = datetime.now()
            db.session.commit()

            # 创建通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                if patient_user:
                    # 获取医生信息
                    doctor = User.query.get(doctor_id)
                    doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="预约已确认",
                        message=f"医生 {doctor_name} 已确认您的预约，日期：{appointment.appointment_date.strftime('%Y-%m-%d')}",
                        type=NotificationType.APPOINTMENT_CONFIRMED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as notification_error:
                # 通知创建失败不应影响整个流程
                current_app.logger.error(f"创建确认通知失败: {str(notification_error)}")

            print(f"预约确认成功 - ID: {appointment_id}, 医生ID: {doctor_id}")
            return jsonify({
                "status": "success",
                "message": "预约已确认",
                "data": appointment.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            error_detail = str(e)
            print(f"确认预约失败 - ID: {appointment_id}, 错误: {error_detail}")
            return jsonify({"status": "error", "message": f"确认预约失败：{error_detail}"}), 500

    @app.route('/api/appointments/<int:appointment_id>/complete', methods=['POST'])
    @login_required
    def complete_appointment_api(appointment_id):
        """API: 完成预约"""
        try:
            if session.get('role') != 'doctor':
                return jsonify({"status": "error", "message": "只有医生能完成预约"}), 403

            appointment = Appointment.query.get_or_404(appointment_id)
            doctor_id = session.get('user_id')
            doctor = User.query.get(doctor_id)
            doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

            # 验证是否是预约的医生
            if appointment.doctor_id != doctor_id:
                return jsonify({"status": "error", "message": "您不能修改其他医生的预约"}), 403

            # 检查预约状态
            if appointment.status != '已确认' and appointment.status != 'confirmed' and appointment.status != AppointmentStatus.CONFIRMED:
                return jsonify({"status": "error", "message": "只有已确认状态的预约可以完成"}), 400

            # 处理请求数据
            data = request.get_json() or {}
            notes = data.get('notes', '')
            follow_up_required = data.get('follow_up_required', False)

            # 更新预约状态
            appointment.status = AppointmentStatus.COMPLETED
            appointment.completed_at = datetime.now()
            appointment.updated_at = datetime.now()

            # 添加备注
            if notes:
                appointment.notes = notes

            # 处理随访设置
            if follow_up_required:
                appointment.follow_up_required = True

                if 'follow_up_date' in data and data['follow_up_date']:
                    try:
                        follow_up_date = datetime.strptime(data['follow_up_date'], '%Y-%m-%d').date()
                        appointment.follow_up_date = follow_up_date
                    except ValueError:
                        return jsonify({"status": "error", "message": "随访日期格式不正确"}), 400

                if 'follow_up_notes' in data:
                    appointment.follow_up_notes = data['follow_up_notes']

            db.session.commit()

            # 创建通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                if patient_user:
                    message = f"医生 {doctor_name} 已完成您的就诊，日期：{appointment.appointment_date.strftime('%Y-%m-%d')}"

                    if notes:
                        message += f" 备注: {notes[:50]}"
                        if len(notes) > 50:
                            message += "..."

                    if follow_up_required and appointment.follow_up_date:
                        message += f" 需要随访，日期: {appointment.follow_up_date.strftime('%Y-%m-%d')}"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="就诊已完成",
                        message=message,
                        type=NotificationType.APPOINTMENT_COMPLETED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as notification_error:
                # 通知创建失败不应影响整个流程
                current_app.logger.error(f"创建就诊完成通知失败: {str(notification_error)}")
                # 不回滚，仍然完成预约确认流程

            print(f"预约完成操作成功 - ID: {appointment_id}, 医生ID: {doctor_id}, 随访要求: {follow_up_required}")
            return jsonify({
                "status": "success",
                "message": "就诊已完成",
                "data": appointment.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            error_detail = str(e)
            print(f"完成就诊失败 - ID: {appointment_id}, 错误: {error_detail}")
            return jsonify({"status": "error", "message": f"完成就诊失败：{error_detail}"}), 500

    @app.route('/api/available_slots', methods=['GET'])
    @login_required
    def available_slots():
        """获取医生可用时间槽API"""
        doctor_id = request.args.get('doctor_id')
        date_str = request.args.get('date')

        if not doctor_id or not date_str:
            return jsonify({"status": "error", "message": "请提供医生ID和日期"})

        try:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"status": "error", "message": "日期格式无效"})

        # 所有可能的时间槽
        all_slots = [slot.value for slot in TimeSlot]

        # 查询该医生在选择日期已有的预约
        booked_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date == selected_date,
            Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED])
        ).all()

        # 已预约的时间槽
        booked_slots = [appointment.time_slot.value for appointment in booked_appointments]

        # 可用的时间槽
        available_slots = [slot for slot in all_slots if slot not in booked_slots]

        return jsonify({
            "status": "success",
            "available_slots": available_slots
        })

    @app.route('/doctor/appointments')
    @login_required
    def doctor_appointments():
        """医生预约管理页面 - 现在只渲染框架"""
        if session.get("role") != 'doctor':
            flash("无权访问", "error")
            return redirect(url_for("dashboard"))

        user_id = session.get('user_id')
        doctor = User.query.get(user_id)

        return render_template('doctor/doctor_appointments.html',
                               username=session.get("username"),
                               role=session.get("role"),
                               doctor=doctor,
                               user_id=user_id)

    @app.route('/api/appointments', methods=['POST'])
    @login_required
    def create_appointment_api():
        """创建预约的API接口"""
        data = request.get_json()
        user_id = session.get('user_id')
        role = session.get('role')
        patient_id = session.get('patient_id')

        # 如果是管理员或医生，从请求中获取patient_id
        if role in ['admin', 'doctor'] and 'patient_id' in data:
            patient_id = data['patient_id']

        # 处理可能的不同字段名
        missing_fields = []
        doctor_id = data.get('doctor_id', user_id)  # 医生创建预约时使用自己的ID

        # 处理日期字段
        date_str = data.get('appointment_date') or data.get('date')
        if not date_str: missing_fields.append("appointment_date/date")

        # 处理其他字段
        time_slot = data.get('time_slot')
        appointment_type = data.get('appointment_type') or data.get('type')
        department = data.get('department')
        symptoms = data.get('symptoms') or data.get('description')

        # 检查必填字段
        if not doctor_id: missing_fields.append("doctor_id")
        if not time_slot: missing_fields.append("time_slot")
        if not appointment_type: missing_fields.append("appointment_type/type")
        if not department: missing_fields.append("department")

        # 处理患者ID
        if role == 'patient':
            # 患者必须有自己的ID
            if not patient_id:
                return jsonify({"status": "error", "message": "患者ID无效，请重新登录"}), 400
        else:
            # 医生或管理员必须指定患者ID
            if not patient_id:
                missing_fields.append("patient_id")

        if missing_fields:
            return jsonify({"status": "error", "message": f"请填写所有必填字段: {', '.join(missing_fields)}"}), 400

        try:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            today = datetime.now().date()
            if appointment_date < today:
                return jsonify({"status": "error", "message": "预约日期不能在过去，请选择今天或未来的日期"}), 400

            existing_appointment = Appointment.query.filter_by(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                time_slot=TimeSlot(time_slot),
                status=AppointmentStatus.CONFIRMED
            ).first()

            if existing_appointment:
                return jsonify({"status": "error", "message": "该时间段已被预约，请选择其他时间"}), 400

            # 根据创建者角色设置初始状态
            initial_status = AppointmentStatus.CONFIRMED if role == 'doctor' else AppointmentStatus.PENDING

            try:
                # 验证枚举值
                time_slot_enum = TimeSlot(time_slot)
                appointment_type_enum = AppointmentType(appointment_type)
                department_enum = Department(department)

                appointment = Appointment(
                    patient_id=patient_id,
                    doctor_id=doctor_id,
                    appointment_date=appointment_date,
                    time_slot=time_slot_enum,
                    symptoms=symptoms,
                    appointment_type=appointment_type_enum,
                    department=department_enum,
                    status=initial_status,
                    code=generate_appointment_code(),
                    created_at=datetime.now()
                )
            except ValueError as e:
                return jsonify({"status": "error", "message": str(e)}), 400

            db.session.add(appointment)

            # 添加或更新医患关系
            doctor_patient = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id
            ).first()

            if not doctor_patient:
                doctor_patient = DoctorPatientRelation(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    start_date=datetime.now(),
                    is_active=True,
                    relation_type='主治' if appointment_type == 'regular' else '会诊',
                    next_visit_date=appointment_date
                )
                db.session.add(doctor_patient)
            else:
                doctor_patient.next_visit_date = appointment_date
                doctor_patient.is_active = True

            # 更新患者状态
            patient = Patient.query.get(patient_id)
            if patient and patient.status == '新患者':
                patient.status = '待就诊'

            db.session.commit()

            # 创建通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=patient_id).first()
                if patient_user:
                    # 获取医生信息
                    doctor = User.query.get(doctor_id)
                    doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="医生已为您创建预约",
                        message=f"医生 {doctor_name} 已为您创建预约，日期：{appointment_date.strftime('%Y-%m-%d')}，时间段：{TimeSlot(time_slot).display_name}",
                        type=NotificationType.APPOINTMENT_NEW,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as e:
                # 通知失败不影响预约创建
                current_app.logger.error(f"发送医生创建预约通知失败: {str(e)}")

            # 返回序列化后的数据
            return jsonify({
                "status": "success",
                "message": "预约创建成功",
                "data": {
                    'appointment_id': appointment.appointment_id,
                    'patient_id': appointment.patient_id,
                    'doctor_id': appointment.doctor_id,
                    'appointment_type': {
                        'value': appointment.appointment_type.value,
                        'display_name': appointment.appointment_type.display_name
                    },
                    'department': {
                        'value': appointment.department.value,
                        'display_name': appointment.department.display_name
                    },
                    'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                    'time_slot': {
                        'value': appointment.time_slot.value,
                        'display_name': appointment.time_slot.display_name
                    },
                    'symptoms': appointment.symptoms,
                    'status': {
                        'value': appointment.status.value,
                        'display_name': appointment.status.display_name
                    },
                    'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S') if appointment.created_at else None,
                    'notes': appointment.notes if hasattr(appointment, 'notes') else None,
                    'code': appointment.code
                }
            })

        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"创建预约失败：{str(e)}"}), 500

    @app.route('/api/appointments/doctor-all', methods=['GET'])
    @login_required
    def get_doctor_appointments():
        """API: 获取医生的所有预约"""
        user_id = session.get('user_id')
        role = session.get('role')
        if role != 'doctor':
            return jsonify({"status": "error", "message": "只有医生能访问此接口"}), 403
        try:
            all_appointments = Appointment.query.filter_by(doctor_id=user_id).order_by(
                Appointment.created_at.desc()).all()
            results = []
            for appt in all_appointments:
                patient = Patient.query.get(appt.patient_id)
                result = {
                    'appointment_id': appt.appointment_id,
                    'patient_id': appt.patient_id,
                    'patient_name': patient.name if patient else "未知患者",
                    'patient_gender': patient.gender if patient else "",
                    'patient_age': patient.age if patient and hasattr(patient, 'age') else "",
                    'patient_contact': patient.contact_info if patient else "",
                    'appointment_type': {
                        'value': appt.appointment_type.value if appt.appointment_type else None,
                        'display_name': appt.appointment_type.display_name if appt.appointment_type else None
                    },
                    'department': {
                        'value': appt.department.value if appt.department else None,
                        'display_name': appt.department.display_name if appt.department else None
                    },
                    'appointment_date': appt.appointment_date.strftime('%Y-%m-%d') if appt.appointment_date else None,
                    'time_slot': {
                        'value': appt.time_slot.value if appt.time_slot else None,
                        'display_name': appt.time_slot.display_name if appt.time_slot else None
                    },
                    'status': {
                        'value': appt.status.value if appt.status else None,
                        'display_name': appt.status.display_name if appt.status else None
                    },
                    'symptoms': appt.symptoms,
                    'created_at': appt.created_at.strftime('%Y-%m-%d %H:%M') if appt.created_at else "",
                    'notes': appt.notes if hasattr(appt, 'notes') else ""
                }
                if hasattr(appt, 'diagnosis') and appt.diagnosis:
                    result['diagnosis'] = appt.diagnosis
                results.append(result)
            return jsonify({
                "status": "success",
                "data": results
            })
        except Exception as e:
            print(f"获取医生预约列表失败: {str(e)}")
            return jsonify({"status": "error", "message": f"获取预约列表失败: {str(e)}"}), 500

    @app.route('/api/debug-request', methods=['GET', 'POST'])
    @login_required
    def debug_request():
        """调试请求信息"""
        return jsonify({
            "status": "success",
            "request_data": {
                "method": request.method,
                "url": request.url,
                "headers": dict(request.headers),
                "form": dict(request.form),
                "args": dict(request.args),
                "json": request.get_json(silent=True),
                "data": request.get_data(as_text=True),
            }
        })

    @app.route('/api/appointments/<int:appointment_id>/details', methods=['GET'])
    @login_required
    def get_appointment_details(appointment_id):
        """API: 获取预约详情"""
        user_id = session.get('user_id')
        role = session.get('role')
        session_patient_id = session.get('patient_id')

        appointment = db.session.get(Appointment, appointment_id)
        if not appointment:
            return jsonify({"status": "error", "message": "预约不存在"}), 404

        # --- 统一的权限验证 ---
        has_permission = False
        if role == 'admin':
            has_permission = True
        elif role == 'doctor' and appointment.doctor_id == user_id:
            has_permission = True
        elif role == 'patient' and session_patient_id is not None:
            if appointment.patient_id == int(session_patient_id):
                has_permission = True

        if not has_permission:
            return jsonify({"status": "error", "message": "无权查看此预约"}), 403

        try:
            doctor = db.session.get(User, appointment.doctor_id)
            doctor_name = doctor.real_name if doctor else "未知医生"

            patient = db.session.get(Patient, appointment.patient_id)
            patient_name = patient.name if patient else "未知患者"

            # 处理预约类型中文显示
            type_name = ""
            if hasattr(appointment.appointment_type, 'display_name'):
                type_name = appointment.appointment_type.display_name

            # 处理科室中文显示
            department_name = ""
            if hasattr(appointment.department, 'display_name'):
                department_name = appointment.department.display_name

            appointment_details = {
                "id": appointment.appointment_id,
                "appointment_id": appointment.appointment_id,
                "patient_name": patient_name,              # 添加患者姓名
                "doctor_id": appointment.doctor_id,
                "doctor_name": doctor_name,
                "type_name": type_name,                    # 添加中文预约类型
                "department_name": department_name,        # 添加中文科室名称
                "appointment_type": {
                    'value': appointment.appointment_type.value if appointment.appointment_type else None,
                    'display_name': appointment.appointment_type.display_name if appointment.appointment_type else None
                },
                "department": {
                    'value': appointment.department.value if appointment.department else None,
                    'display_name': appointment.department.display_name if appointment.department else None
                },
                "appointment_date": appointment.appointment_date.strftime('%Y-%m-%d'),
                "time_slot": {
                    'value': appointment.time_slot.value if appointment.time_slot else None,
                    'display_name': appointment.time_slot.display_name if appointment.time_slot else None
                },
                "status": {
                    'value': appointment.status.value if appointment.status else None,
                    'display_name': appointment.status.display_name if appointment.status else None
                },
                "symptoms": appointment.symptoms,
                "notes": appointment.notes if hasattr(appointment, 'notes') else None,
                "created_at": appointment.created_at.strftime('%Y-%m-%d %H:%M:%S') if appointment.created_at else None,
            }
            return jsonify({
                "status": "success",
                "data": appointment_details
            })
        except Exception as e:
            return jsonify({"status": "error", "message": f"获取预约详情失败: {str(e)}"}), 500

    @app.route('/api/appointments/<int:appointment_id>/update', methods=['PUT'])
    @login_required
    def update_appointment(appointment_id):
        """API: 更新预约信息"""
        appointment = Appointment.query.get_or_404(appointment_id)
        data = request.get_json()

        try:
            # 更新预约类型
            if 'type' in data:
                appointment.appointment_type = AppointmentType(data['type'])

            # 更新科室
            if 'department' in data:
                appointment.department = Department(data['department'])

            # 更新医生
            if 'doctor_id' in data and data['doctor_id']:
                new_doctor_id = int(data['doctor_id'])
                # 检查医生是否存在且是医生角色
                doctor = User.query.filter_by(user_id=new_doctor_id, role='doctor').first()
                if not doctor:
                    return jsonify({"status": "error", "message": "所选医生不存在或不是医生角色"}), 400
                appointment.doctor_id = new_doctor_id

            # 更新日期
            if 'date' in data and data['date']:
                try:
                    new_date = datetime.strptime(data['date'], '%Y-%m-%d').date()
                    appointment.appointment_date = new_date
                except ValueError:
                    return jsonify({"status": "error", "message": "日期格式不正确"}), 400

            # 更新时间段
            if 'time_slot' in data:
                appointment.time_slot = TimeSlot(data['time_slot'])

            # 更新症状描述
            if 'symptoms' in data:
                appointment.symptoms = data['symptoms']

            # 更新修改时间
            appointment.updated_at = datetime.now()

            # 保存更改
            db.session.commit()

            # 获取当前用户角色和ID信息
            user_id = session.get('user_id')
            role = session.get('role')

            # 发送通知给相关方
            try:
                # 获取医生和患者的用户信息
                doctor = User.query.get(appointment.doctor_id)
                doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()

                # 构造通知消息
                update_message = f"预约已更新：日期 {appointment.appointment_date.strftime('%Y-%m-%d')}, " \
                                f"时间段 {appointment.time_slot.display_name}, " \
                                f"科室 {appointment.department.display_name}"

                # 如果是患者更新，通知医生
                if role == 'patient' and doctor:
                    notification_doctor = Notification(
                        receiver_type='doctor',
                        receiver_id=doctor.user_id,
                        sender_id=user_id,
                        title="患者修改了预约信息",
                        message=update_message,
                        type=NotificationType.APPOINTMENT_UPDATED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification_doctor)

                # 如果是医生或管理员更新，通知患者
                if role != 'patient' and patient_user:
                    notification_patient = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=user_id,
                        title="您的预约信息已更新",
                        message=update_message,
                        type=NotificationType.APPOINTMENT_UPDATED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification_patient)

                db.session.commit()
            except Exception as e:
                # 通知创建失败不影响预约更新流程
                current_app.logger.error(f"创建预约更新通知失败: {str(e)}")

            return jsonify({
                "status": "success",
                "message": "预约更新成功",
                "data": appointment.to_dict()
            })

        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({"status": "error", "message": f"更新预约失败：{str(e)}"}), 500

    @app.route('/api/appointments/<int:appointment_id>/reject', methods=['POST'])
    @login_required
    def api_reject_appointment(appointment_id):
        """API: 拒绝预约"""
        try:
            user_id = session.get('user_id')
            role = session.get('role')
            appointment = Appointment.query.get_or_404(appointment_id)
            print(f"开始拒绝预约 - ID: {appointment_id}, 用户ID: {user_id}, 角色: {role}")

            # 只有对应医生本人可以操作
            if role != 'doctor' or appointment.doctor_id != user_id:
                return jsonify({"status": "error", "message": "无权操作此预约"}), 403

            # 检查预约状态
            current_status = appointment.status
            print(f"当前预约状态: {current_status}, 类型: {type(current_status)}")
            if isinstance(current_status, AppointmentStatus):
                if current_status != AppointmentStatus.PENDING:
                    return jsonify({"status": "error", "message": "只有待确认状态的预约可以拒绝"}), 400
            else:
                status_str = str(current_status).lower()
                if status_str not in ['待确认', 'pending', 'appointmentstatus.pending']:
                    return jsonify({"status": "error", "message": "只有待确认状态的预约可以拒绝"}), 400

            data = request.get_json() or {}
            reason = data.get('reason', '').strip()

            # 更新状态
            appointment.status = AppointmentStatus.REJECTED
            appointment.updated_at = datetime.now()
            if reason:
                appointment.notes = f"拒绝原因: {reason}"

            # 通知患者
            try:
                patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                doctor = User.query.get(appointment.doctor_id)
                doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"
                if patient_user:
                    message = f"医生 {doctor_name} 已拒绝您的预约 (预约日期: {appointment.appointment_date.strftime('%Y-%m-%d')})"
                    if reason:
                        message += f" 原因: {reason}"
                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=user_id,
                        title="预约已被拒绝",
                        message=message,
                        type=NotificationType.APPOINTMENT_REJECTED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
            except Exception as e:
                print(f"创建拒绝通知失败: {str(e)}")

            db.session.commit()
            print(f"预约拒绝成功 - ID: {appointment_id}")
            return jsonify({"status": "success", "message": "预约已拒绝", "data": appointment.to_dict()})
        except Exception as e:
            db.session.rollback()
            print(f"拒绝预约失败 - ID: {appointment_id}, 错误: {str(e)}")
            return jsonify({"status": "error", "message": f"拒绝预约失败：{str(e)}"}), 500

    @app.route('/api/patient/search', methods=['GET'])
    @login_required
    def patient_search():
        q = request.args.get('q', '').strip()
        current_app.logger.info(f"患者搜索API请求 - 关键词: '{q}'")

        if not q:
            current_app.logger.info("搜索关键词为空，返回空结果")
            return jsonify([])

        # 测试关键词 "test" 返回模拟数据
        if q.lower() == 'test':
            current_app.logger.info("检测到测试关键词，返回测试数据")
            test_data = [
                {
                    'id': 1001,
                    'name': '测试患者001',
                    'gender': '男',
                    'age': 35,
                    'status': '新患者',
                    'contact': '13800138000'
                },
                {
                    'id': 1002,
                    'name': '测试患者002',
                    'gender': '女',
                    'age': 42,
                    'status': '待就诊',
                    'contact': '13900139000'
                }
            ]
            return jsonify(test_data)

        try:
            # 改进搜索：支持按姓名、患者ID和联系方式模糊匹配
            # 使用 OR 条件查询多个字段
            patients = Patient.query.filter(
                db.or_(
                    Patient.name.ilike(f'%{q}%'),  # 使用 ilike 忽略大小写
                    db.cast(Patient.patient_id, db.String).like(f'%{q}%'),  # ID转为字符串搜索
                    Patient.contact_info.ilike(f'%{q}%')  # 联系方式搜索
                )
            ).limit(20).all()  # 限制最多返回20条结果，避免数据过多

            data = [{
                'id': p.patient_id,
                'name': p.name,
                'contact': p.contact_info or '',
                'gender': p.gender or '',
                'age': p.age,  # 直接使用模型中的age字段
                'status': p.status or '新患者'
            } for p in patients]

            current_app.logger.info(f"搜索完成，找到 {len(data)} 位患者")
            return jsonify(data)

        except Exception as e:
            current_app.logger.error(f"患者搜索失败：{e}", exc_info=True)
            return jsonify([]), 500

    @app.route('/doctor/appointments/create', methods=['POST'])
    @login_required
    def doctor_create_appointment():
        """医生创建预约接口"""
        if session.get('role') != 'doctor':
            return jsonify({"status": "error", "message": "只有医生能创建预约"}), 403

        doctor_id = session.get('user_id')
        # 获取表单数据
        patient_id = request.form.get('patient_id')
        appointment_type = request.form.get('appointment_type')
        department = request.form.get('department')
        date_str = request.form.get('appointment_date')
        time_slot = request.form.get('time_slot')
        symptoms = request.form.get('symptoms', '')

        # 验证表单数据
        if not all([patient_id, appointment_type, department, date_str, time_slot]):
            return jsonify({"status": "error", "message": "请填写所有必填字段"}), 400

        try:
            # 处理日期
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # 检查日期是否有效（不在过去）
            if appointment_date < datetime.now().date():
                return jsonify({"status": "error", "message": "预约日期不能在过去"}), 400

            # 检查医生和时间段是否已被预约
            existing_appointment = Appointment.query.filter_by(
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                time_slot=TimeSlot(time_slot)
            ).filter(Appointment.status.in_([
                AppointmentStatus.PENDING,
                AppointmentStatus.CONFIRMED
            ])).first()

            if existing_appointment:
                return jsonify({"status": "error", "message": "该时间段您已有预约，请选择其他时间"}), 400

            # 创建预约记录 - 医生创建的预约直接为已确认状态
            appointment = Appointment(
                patient_id=patient_id,
                doctor_id=doctor_id,
                appointment_date=appointment_date,
                time_slot=TimeSlot(time_slot),
                symptoms=symptoms,
                appointment_type=AppointmentType(appointment_type),
                department=Department(department),
                status=AppointmentStatus.CONFIRMED,  # 医生创建的预约直接为已确认状态
                code=generate_appointment_code(),
                created_at=datetime.now()
            )

            db.session.add(appointment)

            # 添加或更新医患关系
            doctor_patient = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id
            ).first()

            if not doctor_patient:
                doctor_patient = DoctorPatientRelation(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    start_date=datetime.now(),
                    is_active=True,
                    relation_type='主治' if appointment_type == 'regular' else '会诊',
                    next_visit_date=appointment_date
                )
                db.session.add(doctor_patient)
            else:
                doctor_patient.next_visit_date = appointment_date
                doctor_patient.is_active = True

            # 更新患者状态
            patient = Patient.query.get(patient_id)
            if patient and patient.status == '新患者':
                patient.status = '待就诊'

            db.session.commit()

            # 发送通知给患者
            try:
                patient_user = User.query.filter_by(patient_id=patient_id).first()
                if patient_user:
                    # 获取医生信息
                    doctor = User.query.get(doctor_id)
                    doctor_name = doctor.real_name if doctor and hasattr(doctor, 'real_name') else "医生"

                    notification = Notification(
                        receiver_type='patient',
                        receiver_id=patient_user.patient_id,
                        sender_id=doctor_id,
                        title="医生已为您创建预约",
                        message=f"医生 {doctor_name} 已为您创建预约，日期：{appointment_date.strftime('%Y-%m-%d')}，时间段：{TimeSlot(time_slot).display_name}",
                        type=NotificationType.APPOINTMENT_NEW,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                    db.session.commit()
            except Exception as e:
                # 通知失败不影响预约创建
                current_app.logger.error(f"发送医生创建预约通知失败: {str(e)}")

            return jsonify({
                "status": "success",
                "message": "预约创建成功",
                "data": {
                    'appointment_id': appointment.appointment_id,
                    'patient_id': appointment.patient_id,
                    'doctor_id': appointment.doctor_id,
                    'appointment_type': {
                        'value': appointment.appointment_type.value,
                        'display_name': appointment.appointment_type.display_name
                    },
                    'department': {
                        'value': appointment.department.value,
                        'display_name': appointment.department.display_name
                    },
                    'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d'),
                    'time_slot': {
                        'value': appointment.time_slot.value,
                        'display_name': appointment.time_slot.display_name
                    },
                    'symptoms': appointment.symptoms,
                    'status': {
                        'value': appointment.status.value,
                        'display_name': appointment.status.display_name
                    },
                    'created_at': appointment.created_at.strftime('%Y-%m-%d %H:%M:%S') if appointment.created_at else None,
                    'code': appointment.code
                }
            })

        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400
        except Exception as e:
            db.session.rollback()
            print(f"创建预约失败: {str(e)}")
            return jsonify({"status": "error", "message": f"创建预约失败：{str(e)}"}), 500

    @app.route('/api/appointments/<int:appointment_id>/cancel', methods=['POST'])
    @login_required
    def cancel_appointment_api(appointment_id):
        """API: 取消预约"""
        try:
            appointment = db.session.get(Appointment, appointment_id)
            if not appointment:
                return jsonify({"status": "error", "message": "预约不存在"}), 404

            user_id = session.get('user_id')
            role = session.get('role')

            # 从 session 安全地获取 patient_id
            session_patient_id = session.get('patient_id')

            print(f"开始取消预约 - ID: {appointment_id}, 用户ID: {user_id}, 角色: {role}, Session Patient ID: {session_patient_id}")

            # --- 统一的权限验证逻辑 ---
            has_permission = False
            if role == 'admin':
                has_permission = True
            elif role == 'doctor' and appointment.doctor_id == user_id:
                has_permission = True
            elif role == 'patient' and session_patient_id is not None:
                # 确保比较时类型一致
                if appointment.patient_id == int(session_patient_id):
                    has_permission = True

            if not has_permission:
                print(f"权限验证失败: appt.patient_id={appointment.patient_id}, appt.doctor_id={appointment.doctor_id}")
                return jsonify({"status": "error", "message": "您无权取消此预约"}), 403

            # 检查状态
            current_status = appointment.status
            print(f"当前预约状态: {current_status}, 类型: {type(current_status)}")
            if isinstance(current_status, AppointmentStatus):
                if current_status == AppointmentStatus.COMPLETED:
                    return jsonify({"status": "error", "message": "已完成的预约不能取消"}), 400
            else:
                status_str = str(current_status).lower()
                if status_str in ['已完成', 'completed', 'appointmentstatus.completed']:
                    return jsonify({"status": "error", "message": "已完成的预约不能取消"}), 400

            data = request.get_json() or {}
            reason = data.get('reason', '').strip()

            # 更新状态
            original_status = current_status
            appointment.status = AppointmentStatus.CANCELLED
            appointment.cancelled_at = datetime.now()
            appointment.updated_at = datetime.now()
            appointment.cancelled_by = 'patient' if role == 'patient' else 'doctor' if role == 'doctor' else 'admin'
            if reason:
                appointment.cancel_reason = reason

            # 通知相关方
            try:
                if role == 'patient' and appointment.doctor_id:
                    # 患者取消，通知医生
                    doctor = User.query.get(appointment.doctor_id)
                    message = f"患者 {appointment.patient.name} 已取消了与您的预约。"
                    if reason:
                        message += f" 原因: {reason}"
                    notification = Notification(
                        receiver_type='doctor',
                        receiver_id=appointment.doctor_id,
                        sender_id=user_id,
                        title="预约已取消",
                        message=message,
                        type=NotificationType.APPOINTMENT_CANCELLED,
                        related_id=appointment.appointment_id
                    )
                    db.session.add(notification)
                elif role in ['doctor', 'admin'] and appointment.patient_id:
                    # 医生或管理员取消，通知患者
                    patient_user = User.query.filter_by(patient_id=appointment.patient_id).first()
                    canceller_name = "管理员"
                    if role == 'doctor':
                        canceller = User.query.get(user_id)
                        if canceller:
                           canceller_name = canceller.real_name

                    if patient_user:
                        message = f"您的预约已被 {canceller_name} 取消。"
                        if reason:
                            message += f" 原因: {reason}"
                        notification = Notification(
                            receiver_type='patient',
                            receiver_id=patient_user.patient_id,
                            sender_id=user_id,
                            title="您的预约已被取消",
                            message=message,
                            type=NotificationType.APPOINTMENT_CANCELLED,
                            related_id=appointment.appointment_id
                        )
                        db.session.add(notification)
            except Exception as e:
                current_app.logger.error(f"创建取消通知失败: {str(e)}")

            db.session.commit()
            print(f"预约取消成功 - ID: {appointment_id}, 状态从 {original_status} 变为 {appointment.status}")
            return jsonify({"status": "success", "message": "预约已取消", "data": appointment.to_dict()})
        except Exception as e:
            db.session.rollback()
            print(f"取消预约失败 - ID: {appointment_id}, 错误: {str(e)}")
            return jsonify({"status": "error", "message": f"取消预约失败：{str(e)}"}), 500
