from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_model import db, Patient, MedicalHistory, User, ChatSession, ChatMessage, DoctorPatientRelation, Appointment, PhysicalExam, BrainCTScan, NeurologicalAssessment, MedicationRecord, MentalHealth, ImagingReport, Notification
from datetime import datetime, timedelta
import re
from router.auth import login_required, doctor_required, admin_required
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from sqlalchemy import func, text, or_
from collections import Counter


def init_patient_management_routes(app):
    @app.route('/patients')
    @login_required
    def patient_list():
        """通用患者管理功能，可查看所有患者基本信息"""
        search_query = request.args.get('search', '').strip()

        if search_query:
            search_query_strip = search_query.strip()
            if search_query_strip.lower().startswith('id:'):
                try:
                    patient_id = int(search_query_strip[3:])
                    patients = Patient.query.filter(Patient.patient_id == patient_id).all()
                except Exception:
                    patients = []
            elif search_query_strip.isdigit():
                patient_id = int(search_query_strip)
                patients = Patient.query.filter(Patient.patient_id == patient_id).all()
                if not patients:
                    patients = Patient.query.filter(
                        Patient.name.ilike(f"%{search_query}%")
                    ).all()
            else:
                patients = Patient.query.filter(
                    Patient.name.ilike(f"%{search_query}%")
                ).all()
        else:
            patients = Patient.query.all()

        # 获取患者的诊疗记录和预约信息
        patient_records = {}
        for patient in patients:
            # 获取患者的主治医生
            doctor_relation = DoctorPatientRelation.query.filter_by(patient_id=patient.patient_id, relation_type='主治').first()
            doctor_name = "未分配"
            if doctor_relation:
                doctor = User.query.get(doctor_relation.doctor_id)
                if doctor:
                    doctor_name = doctor.real_name

            # 获取最近的预约记录
            recent_appointment = Appointment.query.filter_by(patient_id=patient.patient_id).order_by(Appointment.appointment_date.desc()).first()

            patient_records[patient.patient_id] = {
                "doctor_name": doctor_name,
                "recent_appointment": recent_appointment
            }

        # 统计患者状态
        total_patients = len(patients)
        new_count = in_treatment_count = completed_count = followup_count = urgent_count = 0
        for p in patients:
            if p.status == '新患者':
                new_count += 1
            elif p.status == '治疗中' or p.status == '就诊中':
                in_treatment_count += 1
            elif p.status == '已完成' or p.status == '治疗完成' or p.status == '已出院':
                completed_count += 1
            elif p.status == '待随访' or p.status == '随访中':
                followup_count += 1
            elif p.status == '需紧急处理':
                urgent_count += 1
            # 将待就诊的患者也计入治疗中类别
            elif p.status == '待就诊':
                in_treatment_count += 1

        # 获取今日预约数
        today = datetime.now().date()
        today_appointments = Appointment.query.filter(
            func.date(Appointment.appointment_date) == today
        ).count()

        return render_template('doctor/patient.html',
                              patients=patients,
                              patient_records=patient_records,
                              total_patients=total_patients,
                              new_count=new_count,
                              in_treatment_count=in_treatment_count,
                              completed_count=completed_count,
                              followup_count=followup_count,
                              urgent_count=urgent_count,
                              today_appointments=today_appointments)

    @app.route('/patients/<int:patient_id>/detail')
    @login_required
    def patient_detail(patient_id):
        """患者详细信息页面，包含所有医疗记录和历史"""
        patient = Patient.query.get_or_404(patient_id)

        # 获取患者的所有医疗记录
        medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).first()
        physical_exams = PhysicalExam.query.filter_by(patient_id=patient_id).order_by(PhysicalExam.exam_date.desc()).all()
        brain_scans = BrainCTScan.query.filter_by(patient_id=patient_id).order_by(BrainCTScan.scan_date.desc()).all()
        neuro_assessments = NeurologicalAssessment.query.filter_by(patient_id=patient_id).order_by(NeurologicalAssessment.assessment_date.desc()).all()
        medication_records = MedicationRecord.query.filter_by(patient_id=patient_id).all()
        mental_health = MentalHealth.query.filter_by(patient_id=patient_id).order_by(MentalHealth.assessment_date.desc()).all()
        imaging_reports = ImagingReport.query.filter_by(patient_id=patient_id).order_by(ImagingReport.report_date.desc()).all()

        # 获取患者的所有预约记录
        appointments = Appointment.query.filter_by(patient_id=patient_id).order_by(Appointment.appointment_date.desc()).all()

        # 获取治疗该患者的医生列表
        doctor_relations = DoctorPatientRelation.query.filter_by(patient_id=patient_id).all()
        doctors = []
        for relation in doctor_relations:
            doctor = User.query.get(relation.doctor_id)
            if doctor:
                doctors.append({
                    "doctor": doctor,
                    "relation": relation
                })

        # 健康趋势数据 - 体检记录图表数据
        vital_signs_data = {
            'dates': [],
            'heart_rate': [],
            'systolic': [],
            'diastolic': [],
            'weight': []
        }

        for exam in physical_exams:
            vital_signs_data['dates'].append(exam.exam_date.strftime('%m-%d'))
            vital_signs_data['heart_rate'].append(exam.heart_rate)
            vital_signs_data['systolic'].append(exam.blood_pressure_systolic)
            vital_signs_data['diastolic'].append(exam.blood_pressure_diastolic)
            vital_signs_data['weight'].append(exam.weight)

        # 反转列表以保持时间顺序
        for key in vital_signs_data:
            vital_signs_data[key] = vital_signs_data[key][-5:]  # 只取最近5条记录

        return render_template('doctor/patient_info.html',
                              patient=patient,
                              medical_history=medical_history,
                              physical_exams=physical_exams,
                              brain_scans=brain_scans,
                              neuro_assessments=neuro_assessments,
                              medication_records=medication_records,
                              mental_health=mental_health,
                              imaging_reports=imaging_reports,
                              appointments=appointments,
                              doctors=doctors,
                              vital_signs_data=vital_signs_data)
    @app.route('/api/patient/status_counts', methods=['GET'])
    @login_required
    def get_patient_status_counts():
        """
        获取当前医生名下所有患者的状态统计。
        """
        try:
            doctor_id = session.get('user_id')
            if not doctor_id:
                return jsonify(success=False, message="未找到医生ID"), 401

            # 查询该医生关联的所有患者的状态
            relations = DoctorPatientRelation.query.filter_by(doctor_id=doctor_id).all()
            patient_ids = [rel.patient_id for rel in relations]

            if not patient_ids:
                return jsonify(success=True, counts={})

            # 获取所有相关患者的状态列表
            patient_statuses = db.session.query(Patient.status).filter(Patient.patient_id.in_(patient_ids)).all()

            # patient_statuses 是一个元组列表，例如 [('待就诊',), ('治疗中',)]
            # 我们需要将其转换为一个简单的状态字符串列表
            status_list = [status[0] for status in patient_statuses if status[0]]

            # 使用 Counter 进行高效计数
            status_counts = Counter(status_list)

            return jsonify(success=True, counts=dict(status_counts))

        except Exception as e:
            # 在生产环境中，应该记录这个错误
            # logger.error(f"Error fetching patient status counts for doctor {doctor_id}: {e}")
            return jsonify(success=False, message="服务器内部错误"), 500

    @app.route('/patients/statistics')
    @login_required
    def patient_statistics():
        """患者数据统计分析页面"""
        # 获取基础患者数据
        total_patients = Patient.query.count()

        # 按性别统计
        male_count = Patient.query.filter_by(gender='男').count()
        female_count = Patient.query.filter_by(gender='女').count()

        # 按年龄段统计
        age_groups = {
            '0-18': 0,
            '19-30': 0,
            '31-45': 0,
            '46-60': 0,
            '61-75': 0,
            '76+': 0
        }

        patients = Patient.query.all()
        for patient in patients:
            if patient.age is None:
                continue
            if patient.age <= 18:
                age_groups['0-18'] += 1
            elif patient.age <= 30:
                age_groups['19-30'] += 1
            elif patient.age <= 45:
                age_groups['31-45'] += 1
            elif patient.age <= 60:
                age_groups['46-60'] += 1
            elif patient.age <= 75:
                age_groups['61-75'] += 1
            else:
                age_groups['76+'] += 1

        # 按状态统计
        status_counts = {
            '新患者': Patient.query.filter_by(status='新患者').count(),
            '治疗中': Patient.query.filter_by(status='治疗中').count(),
            '待随访': Patient.query.filter_by(status='待随访').count(),
            '已完成': Patient.query.filter_by(status='已完成').count(),
            '需紧急处理': Patient.query.filter_by(status='需紧急处理').count()
        }

        # 最近30天的预约趋势
        today = datetime.now().date()
        thirty_days_ago = today - timedelta(days=30)

        date_counts = {}
        for i in range(31):
            date = thirty_days_ago + timedelta(days=i)
            date_counts[date.strftime('%Y-%m-%d')] = 0

        recent_appointments = Appointment.query.filter(
            Appointment.appointment_date >= thirty_days_ago,
            Appointment.appointment_date <= today
        ).all()

        for appointment in recent_appointments:
            date_str = appointment.appointment_date.strftime('%Y-%m-%d')
            if date_str in date_counts:
                date_counts[date_str] += 1

        # 转换为图表数据
        appointment_dates = list(date_counts.keys())
        appointment_counts = list(date_counts.values())

        return render_template('admin/patient_statistics.html',
                              total_patients=total_patients,
                              male_count=male_count,
                              female_count=female_count,
                              age_groups=age_groups,
                              status_counts=status_counts,
                              appointment_dates=appointment_dates,
                              appointment_counts=appointment_counts)

    @app.route('/patients/generate_report')
    @login_required
    @admin_required
    def generate_patient_report():
        """生成患者数据分析报表"""
        report_type = request.args.get('type', 'general')

        if report_type == 'general':
            # 基础患者数据报表
            patients = Patient.query.all()
            data = []

            for patient in patients:
                doctor_rel = DoctorPatientRelation.query.filter_by(patient_id=patient.patient_id, relation_type='主治').first()
                doctor_name = doctor_rel.doctor.real_name if doctor_rel else "N/A"
                data.append(
                    [patient.patient_id, patient.name, patient.age, patient.gender, patient.status,
                     doctor_name])

            df = pd.DataFrame(data,
                              columns=['ID', '姓名', '年龄', '性别', '状态', '主治医生'])
            return df.to_html(classes='layui-table', escape=False)

        elif report_type == 'appointment':
            # 预约数据报表
            appointments = Appointment.query.order_by(Appointment.appointment_date.desc()).all()
            data = []

            for appt in appointments:
                patient = Patient.query.get(appt.patient_id)
                doctor = User.query.get(appt.doctor_id)

                patient_name = patient.name if patient else "未知"
                doctor_name = doctor.real_name if doctor else "未知"

                data.append({
                    "预约ID": appt.appointment_id,
                    "患者": patient_name,
                    "医生": doctor_name,
                    "科室": appt.department,
                    "预约类型": appt.appointment_type,
                    "预约日期": appt.appointment_date.strftime("%Y-%m-%d"),
                    "时间段": appt.time_slot,
                    "状态": appt.status
                })

            # 生成CSV文件
            df = pd.DataFrame(data)
            csv_data = df.to_csv(index=False)

            # 返回为下载文件
            return csv_data, 200, {
                'Content-Type': 'text/csv; charset=utf-8',
                'Content-Disposition': f'attachment; filename=预约数据报表_{datetime.now().strftime("%Y%m%d")}.csv'
            }

        return jsonify({"status": "error", "message": "无效的报表类型"})

    @app.route('/patients/add', methods=['GET', 'POST'])
    @login_required
    def add_patient():
        if request.method == 'POST':
            try:
                # 获取身份证号
                id_card = request.form.get('id_card')
                if not id_card:
                    return jsonify({"status": "error", "message": "请填写身份证号"})

                # 检查身份证号是否重复
                if User.query.filter_by(id_card=id_card).first():
                    return jsonify({"status": "error", "message": "身份证号已存在，请勿重复添加"})

                # 添加患者基本信息
                new_patient = Patient(
                    name=request.form['name'],
                    age=int(request.form['age']),
                    gender=request.form['gender'],
                    address=request.form['address'],
                    contact_info=request.form['contact_info'],
                    blood_type=request.form.get('blood_type'),
                    emergency_contact=request.form.get('emergency_contact')
                )
                db.session.add(new_patient)
                db.session.commit()  # 此时 patient_id 自动生成

                # 添加病史（如果提供）
                if request.form.get('allergy_info') or request.form.get('neurological_conditions'):
                    medical_history = MedicalHistory(
                        patient_id=new_patient.patient_id,
                        allergy_info=request.form.get('allergy_info', ''),
                        family_history=request.form.get('family_history', ''),
                        previous_head_injuries=request.form.get('previous_head_injuries', ''),
                        neurological_conditions=request.form.get('neurological_conditions', '')
                    )
                    db.session.add(medical_history)

                # 创建用户名
                username = f"{new_patient.name}_{new_patient.patient_id}"
                if User.query.filter_by(username=username).first():
                    username += f"_{datetime.now().strftime('%Y%m%d')}"

                # 创建用户账号
                new_user = User(
                    username=username,
                    real_name=new_patient.name,
                    id_card=id_card,
                    phone=request.form.get('contact_info', ''),
                    role='patient',
                    patient_id=new_patient.patient_id,
                    registration_date=datetime.now(),
                    is_active=True
                )
                new_user.set_password('123456')  # 初始密码
                db.session.add(new_user)
                db.session.commit()

                return jsonify({
                    "status": "success",
                    "message": f"患者添加成功，账号已创建，用户名：{username}，初始密码：123456",
                    "redirect": url_for('patient_list')
                })

            except Exception as e:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"添加患者或创建用户失败：{str(e)}"})

        return render_template('doctor/patient_form.html', action='add')

    @app.route('/patients/<int:patient_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_patient(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).first()
        user = User.query.filter_by(patient_id=patient_id).first()

        if request.method == 'POST':
            try:
                # 更新患者信息
                patient.name = request.form['name']
                patient.age = int(request.form['age'])
                patient.gender = request.form['gender']
                patient.address = request.form['address']
                patient.contact_info = request.form['contact_info']
                patient.blood_type = request.form.get('blood_type')
                patient.emergency_contact = request.form.get('emergency_contact')

                # 更新用户信息（身份证号）
                if user:
                    user.id_card = request.form['id_card']
                    user.real_name = request.form['name']  # 同步更新真实姓名
                    user.phone = request.form['contact_info']  # 同步更新电话

                # 更新病史记录（如果存在）
                if medical_history:
                    medical_history.allergy_info = request.form.get('allergy_info', medical_history.allergy_info)
                    medical_history.family_history = request.form.get('family_history', medical_history.family_history)
                    medical_history.previous_head_injuries = request.form.get('previous_head_injuries',
                                                                              medical_history.previous_head_injuries)
                    medical_history.neurological_conditions = request.form.get('neurological_conditions',
                                                                               medical_history.neurological_conditions)
                else:
                    # 如果没有病史记录，创建新的病史记录
                    medical_history = MedicalHistory(
                        patient_id=patient_id,
                        allergy_info=request.form.get('allergy_info'),
                        family_history=request.form.get('family_history'),
                        previous_head_injuries=request.form.get('previous_head_injuries'),
                        neurological_conditions=request.form.get('neurological_conditions')
                    )
                    db.session.add(medical_history)

                # 提交更改
                db.session.commit()
                return jsonify({
                    "status": "success",
                    "message": "更新患者信息成功",
                    "redirect": url_for('patient_medical_record', patient_id=patient_id)
                })

            except Exception as e:
                db.session.rollback()
                return jsonify({
                    "status": "error",
                    "message": f"更新患者信息失败: {str(e)}"
                })

        return render_template('doctor/patient_form.html',
                              patient=patient,
                              user=user,
                              medical_history=medical_history,
                              action='edit')

    @app.route('/patients/<int:patient_id>/delete', methods=['POST'])
    @login_required
    def patient_delete(patient_id):
        patient = Patient.query.get_or_404(patient_id)

        try:
            # 删除关联的User记录
            user = User.query.filter_by(patient_id=patient_id).first()
            if user:
                # 先删除与用户相关的通知
                Notification.query.filter_by(user_id=user.user_id).delete()

                # 删除用户的聊天会话和消息
                chat_sessions = ChatSession.query.filter_by(user_id=user.user_id).all()
                for session in chat_sessions:
                    # 删除会话中的所有消息
                    ChatMessage.query.filter_by(session_id=session.session_id).delete()
                    # 删除会话
                    db.session.delete(session)

                # 删除用户
                db.session.delete(user)

            # 删除医患关系
            DoctorPatientRelation.query.filter_by(patient_id=patient_id).delete()

            # 删除与患者关联的所有预约记录
            Appointment.query.filter_by(patient_id=patient_id).delete()

            # 删除所有相关记录
            for record in patient.medical_history:
                db.session.delete(record)
            for exam in patient.physical_exams:
                db.session.delete(exam)
            for med in patient.medication_records:
                db.session.delete(med)
            for mh in patient.mental_health_records:
                db.session.delete(mh)
            for scan in patient.brain_ct_scans:
                for followup in scan.follow_ups:
                    db.session.delete(followup)
                db.session.delete(scan)
            for assessment in patient.neurological_assessments:
                db.session.delete(assessment)
            for report in patient.imaging_reports:
                db.session.delete(report)

            # 最后删除患者记录
            db.session.delete(patient)
            db.session.commit()
            flash('患者信息已删除。', 'success')
            return redirect(url_for('patient_list'))
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除患者失败: {str(e)}"
            })

    @app.route('/patients/search_partial')
    @login_required
    def patient_search_partial():
        search_term = request.args.get('q', '').strip()
        # 复用主列表的搜索逻辑
        search_query_strip = search_term.strip()
        if search_query_strip.lower().startswith('id:'):
            try:
                patient_id = int(search_query_strip[3:])
                patients = Patient.query.filter(Patient.patient_id == patient_id).all()
            except Exception:
                patients = []
        elif search_query_strip.isdigit():
            patient_id = int(search_query_strip)
            patients = Patient.query.filter(Patient.patient_id == patient_id).all()
            if not patients:
                patients = Patient.query.filter(
                    Patient.name.ilike(f"%{search_term}%")
                ).all()
        else:
            patients = Patient.query.filter(
                Patient.name.ilike(f"%{search_term}%")
            ).all()
        # patient_records 复用主列表逻辑
        patient_records = {}
        for patient in patients:
            doctor_relation = DoctorPatientRelation.query.filter_by(patient_id=patient.patient_id, relation_type='主治').first()
            doctor_name = "未分配"
            if doctor_relation:
                doctor = User.query.get(doctor_relation.doctor_id)
                if doctor:
                    doctor_name = doctor.real_name
            recent_appointment = Appointment.query.filter_by(patient_id=patient.patient_id).order_by(Appointment.appointment_date.desc()).first()
            patient_records[patient.patient_id] = {
                "doctor_name": doctor_name,
                "recent_appointment": recent_appointment
            }
        return render_template('doctor/_patient_table_body.html', patients=patients, patient_records=patient_records)

    @app.route('/api/patients/search', methods=['GET'])
    @login_required
    def api_search_patients():
        """一个更通用的患者搜索API，用于弹窗等场景"""
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({'status': 'error', 'message': 'Query parameter is missing.'}), 400

        search_term = f"%{query}%"
        patients = Patient.query.filter(
            or_(
                Patient.name.ilike(search_term),
                Patient.contact_info.ilike(search_term)
            )
        ).limit(10).all()

        results = [
            {
                'patient_id': p.patient_id,
                'name': p.name,
                'contact_info': p.contact_info,
                'age': p.age,
                'gender': p.gender
            } for p in patients
        ]

        return jsonify({'status': 'success', 'data': results})

    @app.route('/api/check_id_card', methods=['POST'])
    def api_check_id_card():
        data = request.get_json()
        id_card = data.get('id_card')
        if not id_card:
            return {'exists': False}
        exists = User.query.filter_by(id_card=id_card).first() is not None
        return {'exists': exists}

    @app.route('/doctor/my-patients')
    @login_required
    @doctor_required
    def doctor_my_patients():
        """医生的个人患者管理，只显示与该医生有关联的患者"""
        doctor_id = session.get('user_id')
        username = session.get('username')

        # 获取与医生关联的所有患者关系 - 使用一次查询加载所有数据
        doctor_patient_relations = DoctorPatientRelation.query.filter_by(
            doctor_id=doctor_id,
            is_active=True
        ).all()

        # 如果没有关联患者，直接返回空结果
        if not doctor_patient_relations:
            return render_template('doctor/my_patients.html',
                                  username=username,
                                  patients_data=[],
                                  patient_groups={},
                                  status_counts={},
                                  total_patients=0)

        # 批量获取患者ID
        patient_ids = [relation.patient_id for relation in doctor_patient_relations]

        # 批量获取患者信息 - 一次查询
        patients = Patient.query.filter(Patient.patient_id.in_(patient_ids)).all()
        patients_dict = {patient.patient_id: patient for patient in patients}

        # 批量获取最新预约 - 修复SQL查询结果的处理
        latest_appointments_query = text("""
            WITH LatestAppointments AS (
                SELECT a.*,
                       ROW_NUMBER() OVER (PARTITION BY a.patient_id ORDER BY a.appointment_date DESC) as rn
                FROM appointment a
                WHERE a.doctor_id = :doctor_id AND a.patient_id IN :patient_ids
            )
            SELECT * FROM LatestAppointments WHERE rn = 1
        """)

        latest_appointments_result = db.session.execute(
            latest_appointments_query,
            {"doctor_id": doctor_id, "patient_ids": patient_ids})

        # 将结果转换为字典，以便快速查找 - 修复处理方式
        latest_appointments = {}
        for row in latest_appointments_result:
            # 正确方式：获取RowMapping对象的属性
            appointment = {}
            for column in row._fields:
                appointment[column] = getattr(row, column)
            latest_appointments[appointment['patient_id']] = appointment

        # 批量获取最新体检记录 - 修复SQL查询结果的处理
        latest_exams_query = text("""
            WITH LatestExams AS (
                SELECT e.*,
                       ROW_NUMBER() OVER (PARTITION BY e.patient_id ORDER BY e.exam_date DESC) as rn
                FROM physical_exam e
                WHERE e.patient_id IN :patient_ids
            )
            SELECT * FROM LatestExams WHERE rn = 1
        """)

        latest_exams_result = db.session.execute(
            latest_exams_query,
            {"patient_ids": patient_ids})

        # 将结果转换为字典 - 修复处理方式
        latest_exams = {}
        for row in latest_exams_result:
            # 正确方式：获取RowMapping对象的属性
            exam = {}
            for column in row._fields:
                exam[column] = getattr(row, column)
            latest_exams[exam['patient_id']] = exam

        # 构建关系字典，用于快速查找
        relations_dict = {relation.patient_id: relation for relation in doctor_patient_relations}

        # 一次性获取所有患者状态的计数 - 使用GROUP BY
        status_counts_query = db.session.query(
            Patient.status,
            db.func.count(Patient.patient_id)
        ).filter(
            Patient.patient_id.in_(patient_ids)
        ).group_by(Patient.status).all()

        # 转换为字典
        status_counts = {}
        valid_statuses = ['新患者', '待就诊', '就诊中', '随访中', '治疗中', '已完成', '已出院', '已转诊']
        for status in valid_statuses:
            status_counts[status] = 0

        for status, count in status_counts_query:
            if status in status_counts:
                status_counts[status] = count

        # 构建患者数据
        patients_data = []
        for patient_id in patient_ids:
            patient = patients_dict.get(patient_id)
            if not patient:
                continue

            relation = relations_dict.get(patient_id)
            latest_appointment = latest_appointments.get(patient_id)
            latest_exam = latest_exams.get(patient_id)

            # 检查是否有未完成的治疗任务
            has_pending_treatment = False
            if latest_appointment and latest_appointment.get('status') in ['待确认', '已确认'] and not latest_appointment.get('completed_at'):
                has_pending_treatment = True

            patients_data.append({
                'patient': patient,
                'relation': relation,
                'latest_appointment': latest_appointment,
                'latest_exam': latest_exam,
                'medications': [],  # 简化：不加载用药记录以提高性能
                'has_pending_treatment': has_pending_treatment
            })

        # 按照患者分组进行分类
        patient_groups = {}
        for data in patients_data:
            group = data['relation'].patient_group or '未分组'
            if group not in patient_groups:
                patient_groups[group] = []
            patient_groups[group].append(data)

        return render_template('doctor/my_patients.html',
                              username=username,
                              patients_data=patients_data,
                              patient_groups=patient_groups,
                              status_counts=status_counts,
                              total_patients=len(patients_data))

    @app.route('/api/doctor/my-patients/search', methods=['GET'])
    @login_required
    @doctor_required
    def search_my_patients():
        """高级搜索功能：根据多种条件搜索医生的患者"""
        doctor_id = session.get('user_id')

        # 获取搜索参数
        search_term = request.args.get('q', '').strip()
        status_filter = request.args.get('status', '').strip()
        relation_type = request.args.get('relation', '').strip()
        age_min = request.args.get('age_min', type=int)
        age_max = request.args.get('age_max', type=int)
        gender = request.args.get('gender', '').strip()
        last_visit_days = request.args.get('last_visit_days', type=int)  # 最近就诊天数

        # 构建查询
        # 1. 获取与医生关联的患者关系记录
        relations_query = DoctorPatientRelation.query.filter_by(doctor_id=doctor_id, is_active=True)

        # 2. 如果指定了关系类型，进行过滤
        if relation_type:
            relations_query = relations_query.filter(DoctorPatientRelation.relation_type == relation_type)

        # 3. 如果指定了最近就诊天数，进行过滤
        if last_visit_days:
            cutoff_date = datetime.now() - timedelta(days=last_visit_days)
            relations_query = relations_query.filter(DoctorPatientRelation.last_visit_date >= cutoff_date)

        # 4. 执行查询获取关系记录
        doctor_patient_relations = relations_query.all()

        # 5. 获取患者ID列表
        patient_ids = [relation.patient_id for relation in doctor_patient_relations]

        # 如果没有相关患者，直接返回空结果
        if not patient_ids:
            return jsonify({
                'status': 'success',
                'data': {
                    'patients_data': [],
                    'total': 0
                }
            })

        # 6. 构建患者查询
        patients_query = Patient.query.filter(Patient.patient_id.in_(patient_ids))

        # 7. 根据搜索词过滤
        if search_term:
            patients_query = patients_query.filter(
                or_(Patient.name.ilike(f"%{search_term}%"),
                    Patient.contact_info.ilike(f"%{search_term}%"),
                    Patient.address.ilike(f"%{search_term}%"),
                    Patient.emergency_contact.ilike(f"%{search_term}%"))
            )

        # 8. 根据状态过滤
        if status_filter:
            patients_query = patients_query.filter(Patient.status == status_filter)

        # 9. 根据年龄范围过滤
        if age_min is not None:
            patients_query = patients_query.filter(Patient.age >= age_min)
        if age_max is not None:
            patients_query = patients_query.filter(Patient.age <= age_max)

        # 10. 根据性别过滤
        if gender:
            patients_query = patients_query.filter(Patient.gender == gender)

        # 11. 执行查询
        filtered_patients = patients_query.all()

        # 12. 构建结果数据
        result_data = []
        for patient in filtered_patients:
            # 找到对应的患者-医生关系
            relation = next((r for r in doctor_patient_relations if r.patient_id == patient.patient_id), None)

            if relation:
                # 获取该患者的最新检查
                latest_exam = PhysicalExam.query.filter_by(
                    patient_id=patient.patient_id
                ).order_by(PhysicalExam.exam_date.desc()).first()

                # 构建患者数据
                patient_data = {
                    'patient': {
                        'patient_id': patient.patient_id,
                        'name': patient.name,
                        'age': patient.age,
                        'gender': patient.gender,
                        'status': patient.status,
                        'contact_info': patient.contact_info
                    },
                    'relation': {
                        'relation_type': relation.relation_type,
                        'patient_group': relation.patient_group,
                        'next_visit_date': relation.next_visit_date.strftime('%Y-%m-%d') if relation.next_visit_date else None,
                        'last_visit_date': relation.last_visit_date.strftime('%Y-%m-%d') if relation.last_visit_date else None,
                        'notes': relation.notes,
                        'doctor': {
                            'real_name': session.get('real_name') or '医生'
                        }
                    },
                    'latest_exam': {
                        'exam_date': latest_exam.exam_date.strftime('%Y-%m-%d') if latest_exam else None
                    }
                }

                result_data.append(patient_data)

        return jsonify({
            'status': 'success',
            'data': {
                'patients_data': result_data,
                'total': len(result_data)
            }
        })

    @app.route('/doctor/statistics')
    @login_required
    @doctor_required
    def doctor_statistics():
        """医生诊疗统计分析页面"""
        doctor_id = session.get('user_id')

        # 统计数据
        stats = {}

        # 1. 总计数据
        # 关联患者总数
        stats['total_patients'] = DoctorPatientRelation.query.filter_by(
            doctor_id=doctor_id,
            is_active=True
        ).count()

        # 本月新增患者
        first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats['new_patients_month'] = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id == doctor_id,
            DoctorPatientRelation.start_date >= first_day_of_month
        ).count()

        # 本月诊疗数
        stats['treatments_month'] = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == '已完成',
            Appointment.completed_at >= first_day_of_month
        ).count()

        # 需随访患者数
        today = datetime.now().date()
        stats['followup_count'] = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id == doctor_id,
            DoctorPatientRelation.is_active == True,
            DoctorPatientRelation.next_visit_date.isnot(None)
        ).count()

        # 2. 患者状态分布
        status_counts = {}
        doctor_patient_relations = DoctorPatientRelation.query.filter_by(
            doctor_id=doctor_id,
            is_active=True
        ).all()

        for relation in doctor_patient_relations:
            patient = Patient.query.get(relation.patient_id)
            if patient:
                status = patient.status
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts[status] = 1

        # 3. 患者分组分布
        group_counts = {}
        for relation in doctor_patient_relations:
            group = relation.patient_group
            if group is None:
                continue  # 跳过 None 值
            if group in group_counts:
                group_counts[group] += 1
            else:
                group_counts[group] = 1


        # 定义patient_ids变量，从关系中提取患者ID
        patient_ids = [relation.patient_id for relation in doctor_patient_relations]

        # 4. 预约类型分布（替换原来的检查类型分布）
        appointment_types = {}

        # 英文预约类型到中文的映射
        appt_type_mapping = {
            'regular_check': '常规检查',
            'follow_up': '复诊随访',
            'specialist': '专科预约',
            'emergency': '加急预约',
            'regular': '常规检查',
            'followup': '复诊随访',
            'specialist_appointment': '专科预约',
            'urgent': '加急预约'
        }

        if patient_ids:  # 确保列表不为空
            # 获取该医生处理的所有预约
            appointments = Appointment.query.filter(
                Appointment.doctor_id == doctor_id,
                Appointment.status == '已完成'
            ).all()

            # 统计不同预约类型的数量，并转换为中文
            for appointment in appointments:
                appt_type = appointment.appointment_type
                # 如果是英文类型，转换为中文；如果已经是中文或者映射中没有对应关系，则保持原样
                display_type = appt_type_mapping.get(appt_type, appt_type)

                if display_type in appointment_types:
                    appointment_types[display_type] += 1
                else:
                    appointment_types[display_type] = 1

        # 5. 患者年龄分布
        age_groups = {
            '0-18': 0,
            '19-30': 0,
            '31-45': 0,
            '46-60': 0,
            '61-75': 0,
            '76+': 0
        }

        for relation in doctor_patient_relations:
            patient = Patient.query.get(relation.patient_id)
            if patient and patient.age:
                if patient.age <= 18:
                    age_groups['0-18'] += 1
                elif patient.age <= 30:
                    age_groups['19-30'] += 1
                elif patient.age <= 45:
                    age_groups['31-45'] += 1
                elif patient.age <= 60:
                    age_groups['46-60'] += 1
                elif patient.age <= 75:
                    age_groups['61-75'] += 1
                else:
                    age_groups['76+'] += 1

        # 6. 近30天诊疗趋势
        thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
        recent_appointments = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == '已完成',
            Appointment.completed_at >= thirty_days_ago
        ).all()

        # 生成日期列表和初始化计数
        trend_dates = []
        trend_counts = []

        for i in range(30):
            date = (thirty_days_ago + timedelta(days=i)).strftime('%m-%d')
            trend_dates.append(date)
            trend_counts.append(0)

        # 填充实际数据
        for appointment in recent_appointments:
            if appointment.completed_at:
                day_index = (appointment.completed_at.date() - thirty_days_ago).days
                if 0 <= day_index < 30:
                    trend_counts[day_index] += 1

        # 7. 即将随访的患者
        followup_patients = []
        relations_for_followup = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id == doctor_id,
            DoctorPatientRelation.is_active == True,
            DoctorPatientRelation.next_visit_date.isnot(None),
            DoctorPatientRelation.next_visit_date >= today
        ).order_by(DoctorPatientRelation.next_visit_date).limit(10).all()

        for relation in relations_for_followup:
            patient = Patient.query.get(relation.patient_id)
            if patient:
                # 获取随访原因（从最近一次预约的随访备注中获取）
                recent_appointment = Appointment.query.filter(
                    Appointment.doctor_id == doctor_id,
                    Appointment.patient_id == patient.patient_id,
                    Appointment.follow_up_required == True
                ).order_by(Appointment.completed_at.desc()).first()

                followup_reason = "常规随访"
                if recent_appointment and recent_appointment.follow_up_notes:
                    followup_reason = recent_appointment.follow_up_notes

                # 将today从date类型转换为datetime类型以匹配next_visit_date的类型
                today_datetime = datetime.combine(today, datetime.min.time())
                days_remaining = (relation.next_visit_date - today_datetime).days

                followup_patients.append({
                    'patient': patient,
                    'reason': followup_reason,
                    'followup_date': relation.next_visit_date,
                    'days_remaining': days_remaining
                })

        # 8. 最近治疗记录
        recent_treatments = []
        recent_completed = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == '已完成'
        ).order_by(Appointment.completed_at.desc()).limit(10).all()

        for appt in recent_completed:
            patient = Patient.query.get(appt.patient_id)
            if patient:
                # 只有当completed_at不为None时才添加到列表中
                if appt.completed_at:
                    recent_treatments.append({
                        'patient': patient,
                        'treatment_date': appt.completed_at,
                        'treatment_content': f"{appt.appointment_type}（{appt.department}）",
                        'treatment_effect': appt.follow_up_notes if appt.follow_up_notes else "治疗完成"
                    })
                else:
                    # 如果completed_at为None，使用appointment_date或当前日期
                    recent_treatments.append({
                        'patient': patient,
                        'treatment_date': appt.appointment_date or datetime.now().date(),
                        'treatment_content': f"{appt.appointment_type}（{appt.department}）",
                        'treatment_effect': appt.follow_up_notes if appt.follow_up_notes else "治疗完成"
                    })

        return render_template('doctor/statistics.html',
                             stats=stats,
                             status_counts=status_counts,
                             group_counts=group_counts,
                             appointment_types=appointment_types,
                             age_groups=age_groups,
                             trend_dates=trend_dates,
                             trend_counts=trend_counts,
                             followup_patients=followup_patients,
                             recent_treatments=recent_treatments)

    @app.route('/doctor/patient/add-relation', methods=['POST'])
    @login_required
    @doctor_required
    def add_patient_relation():
        """添加医生与患者的关联关系"""
        doctor_id = session.get('user_id')
        patient_id = request.form.get('patient_id')
        relation_type = request.form.get('relation_type')
        patient_group = request.form.get('patient_group')
        notes = request.form.get('notes')

        if not patient_id:
            return jsonify({'status': 'error', 'message': '未选择患者'})

        try:
            patient_id = int(patient_id)
            # 检查患者是否存在
            patient = Patient.query.get(patient_id)
            if not patient:
                return jsonify({'status': 'error', 'message': '患者不存在'})

            # 检查是否已经存在关联关系
            existing_relation = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id
            ).first()

            if existing_relation:
                # 已存在关系，更新关系信息
                existing_relation.relation_type = relation_type
                existing_relation.patient_group = patient_group
                existing_relation.is_active = True
                if notes:
                    existing_relation.notes = notes
                db.session.commit()
                return jsonify({
                    'status': 'success',
                    'message': f'已更新与患者 {patient.name} 的关联关系（{relation_type}）',
                    'isUpdate': True
                })
            else:
                # 创建新的关系记录
                new_relation = DoctorPatientRelation(
                    doctor_id=doctor_id,
                    patient_id=patient_id,
                    relation_type=relation_type,
                    patient_group=patient_group,
                    start_date=datetime.now(),
                    is_active=True,
                    notes=notes
                )
                db.session.add(new_relation)
                db.session.commit()
                return jsonify({
                    'status': 'success',
                    'message': f'成功添加患者 {patient.name} 的关联关系（{relation_type}）',
                    'isNew': True
                })

        except Exception as e:
            db.session.rollback()
            return jsonify({'status': 'error', 'message': f'添加关联失败: {str(e)}'})

    @app.route('/doctor/patient/<int:patient_id>/add-note', methods=['POST'])
    @login_required
    @doctor_required
    def add_patient_note(patient_id):
        """更新医生与患者关系中的备注信息"""
        doctor_id = session.get('user_id')
        note = request.form.get('note')

        if not note:
            return jsonify({
                'status': 'error',
                'message': '备注内容不能为空'
            })

        try:
            # 查找医生与患者的关联关系
            relation = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id,
                is_active=True
            ).first()

            if not relation:
                return jsonify({
                    'status': 'error',
                    'message': '未找到与该患者的关联关系'
                })

            # 更新备注信息
            relation.notes = note
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': '患者备注已更新'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'更新备注失败: {str(e)}'
            })

    @app.route('/doctor/patient/<int:patient_id>/remove-relation', methods=['POST'])
    @login_required
    @doctor_required
    def remove_patient_relation(patient_id):
        """移除医生与患者的关联关系（不删除患者数据）"""
        doctor_id = session.get('user_id')

        try:
            # 查找医生与患者的关联关系
            relation = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id
            ).first()

            if not relation:
                return jsonify({
                    'status': 'error',
                    'message': '未找到与该患者的关联关系'
                })

            # 获取患者姓名用于返回信息
            patient = Patient.query.get(patient_id)
            patient_name = patient.name if patient else "未知患者"

            # 方案1：直接删除关联记录
            db.session.delete(relation)

            # 方案2：设置为非活跃（如果你希望保留历史记录）
            # relation.is_active = False
            # relation.end_date = datetime.now()

            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': f'已移除与患者 {patient_name} 的关联关系',
                'patient_id': patient_id
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'移除关联关系失败: {str(e)}'
            })

    @app.route('/api/doctor/statistics_data', methods=['GET'])
    @login_required
    @doctor_required
    def doctor_statistics_api():
        """医生诊疗统计数据 JSON 接口"""
        doctor_id = session.get('user_id')
        # 统计基础数据
        stats = {}
        stats['total_patients'] = DoctorPatientRelation.query.filter_by(doctor_id=doctor_id, is_active=True).count()
        first_day = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        stats['new_patients_month'] = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id==doctor_id,
            DoctorPatientRelation.start_date>=first_day
        ).count()
        stats['treatments_month'] = Appointment.query.filter(
            Appointment.doctor_id==doctor_id,
            Appointment.status=='已完成',
            Appointment.completed_at>=first_day
        ).count()
        today = datetime.now().date()
        stats['followup_count'] = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id==doctor_id,
            DoctorPatientRelation.is_active==True,
            DoctorPatientRelation.next_visit_date.isnot(None)
        ).count()

        # 获取关系列表
        relations = DoctorPatientRelation.query.filter_by(doctor_id=doctor_id, is_active=True).all()
        # 患者状态分布
        status_counts = {}
        for rel in relations:
            p = Patient.query.get(rel.patient_id)
            if p:
                status_counts[p.status] = status_counts.get(p.status, 0) + 1
        # 患者分组分布
        group_counts = {}
        for rel in relations:
            grp = rel.patient_group
            if grp:
                group_counts[grp] = group_counts.get(grp, 0) + 1
        # 年龄分布
        age_groups = {'0-18':0,'19-30':0,'31-45':0,'46-60':0,'61-75':0,'76+':0}
        for rel in relations:
            p = Patient.query.get(rel.patient_id)
            if p and p.age:
                age = p.age
                if age<=18: age_groups['0-18']+=1
                elif age<=30: age_groups['19-30']+=1
                elif age<=45: age_groups['31-45']+=1
                elif age<=60: age_groups['46-60']+=1
                elif age<=75: age_groups['61-75']+=1
                else: age_groups['76+']+=1
        # 近30天趋势
        thirty_ago = (datetime.now()-timedelta(days=30)).date()
        recent_appts = Appointment.query.filter(
            Appointment.doctor_id==doctor_id,
            Appointment.status=='已完成',
            Appointment.completed_at>=thirty_ago
        ).all()
        trend_dates = [(thirty_ago+timedelta(days=i)).strftime('%m-%d') for i in range(30)]
        trend_counts = [0]*30
        for appt in recent_appts:
            if appt.completed_at:
                idx = (appt.completed_at.date()-thirty_ago).days
                if 0<=idx<30: trend_counts[idx]+=1
        # 未来随访列表
        follow_list = []
        follow_rels = DoctorPatientRelation.query.filter(
            DoctorPatientRelation.doctor_id==doctor_id,
            DoctorPatientRelation.is_active==True,
            DoctorPatientRelation.next_visit_date.isnot(None),
            DoctorPatientRelation.next_visit_date>=today
        ).order_by(DoctorPatientRelation.next_visit_date).limit(10).all()
        for rel in follow_rels:
            p = Patient.query.get(rel.patient_id)
            if p:
                days = (rel.next_visit_date - datetime.combine(today, datetime.min.time())).days
                follow_list.append({
                    'patient': {'patient_id':p.patient_id, 'name':p.name, 'age':p.age, 'gender':p.gender},
                    'reason': rel.notes or '常规随访',
                    'followup_date': rel.next_visit_date.strftime('%Y-%m-%d'),
                    'days_remaining': days
                })
        # 最近完成记录
        recent_treats = []
        comp_appts = Appointment.query.filter(
            Appointment.doctor_id==doctor_id,
            Appointment.status=='已完成'
        ).order_by(Appointment.completed_at.desc()).limit(10).all()
        for appt in comp_appts:
            p = Patient.query.get(appt.patient_id)
            if p:
                date = appt.completed_at or appt.appointment_date or datetime.now()
                recent_treats.append({
                    'patient': {'patient_id':p.patient_id, 'name':p.name},
                    'treatment_date': date.strftime('%Y-%m-%d'),
                    'treatment_content': f"{appt.appointment_type}（{appt.department}）",
                    'treatment_effect': appt.follow_up_notes or '治疗完成'
                })
        return jsonify({
            'stats': stats,
            'status_counts': status_counts,
            'group_counts': group_counts,
            'age_groups': age_groups,
            'trend_dates': trend_dates,
            'trend_counts': trend_counts,
            'followup_patients': follow_list,
            'recent_treatments': recent_treats
        })

    @app.route('/api/doctor/followup_date', methods=['POST'])
    @login_required
    @doctor_required
    def update_followup_date():
        data = request.get_json()
        patient_id = data.get('patient_id')
        new_date = data.get('new_date')
        doctor_id = session.get('user_id')
        try:
            relation = DoctorPatientRelation.query.filter_by(
                doctor_id=doctor_id,
                patient_id=patient_id,
                is_active=True
            ).first()
            if not relation:
                return jsonify({'status':'error','message':'未找到关联关系'}), 404
            if new_date:
                relation.next_visit_date = datetime.strptime(new_date, '%Y-%m-%d')
            else:
                relation.next_visit_date = None
            db.session.commit()
            return jsonify({'status':'success','message':'随访日期已更新'})
        except Exception as e:
            db.session.rollback()
            return jsonify({'status':'error','message':f'更新失败: {str(e)}'}), 500


