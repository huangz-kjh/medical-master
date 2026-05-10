from flask import render_template, request, redirect, url_for, session, flash, jsonify
from db_model import db, Patient, MedicalHistory, PhysicalExam, BrainCTScan, CTFollowUp, NeurologicalAssessment, \
    MedicationRecord, MentalHealth, User, ImagingReport, DoctorPatientRelation
from datetime import date, datetime, timedelta
from router.auth import login_required


def init_medical_records_routes(app):
    @app.route('/patients/<int:patient_id>')
    @login_required
    def patient_medical_record(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        status, status_color = "新患者", "info"
        if patient.brain_ct_scans:
            recent_ct = max(patient.brain_ct_scans, key=lambda x: x.scan_date)
            if (recent_ct.hemorrhage_status and
                    ("出血" in recent_ct.hemorrhage_status or
                     "血肿" in recent_ct.conclusion or
                     "紧急" in recent_ct.conclusion)):
                status, status_color = "需紧急处理", "danger"
            elif recent_ct.follow_up_recommended:
                status, status_color = "待随访", "warning"
            else:
                current_meds = any((m.end_date and m.end_date >= date.today()) or m.end_date is None for m in patient.medication_records)
                if current_meds:
                    status, status_color = "治疗中", "primary"
                else:
                    status, status_color = "已完成", "success"

        medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).first()
        physical_exams = PhysicalExam.query.filter_by(patient_id=patient_id).order_by(
            PhysicalExam.exam_date.desc()).all()
        brain_ct_scans = BrainCTScan.query.filter_by(patient_id=patient_id).order_by(BrainCTScan.scan_date.desc()).all()
        ct_followups = {
            scan.scan_id: CTFollowUp.query.filter_by(original_scan_id=scan.scan_id).order_by(
                CTFollowUp.follow_up_date).all()
            for scan in brain_ct_scans
        }
        neuro_assessments = NeurologicalAssessment.query.filter_by(patient_id=patient_id).order_by(
            NeurologicalAssessment.assessment_date.desc()).all()
        medication_records = MedicationRecord.query.filter_by(patient_id=patient_id).order_by(
            MedicationRecord.start_date.desc()).all()
        mental_health = MentalHealth.query.filter_by(patient_id=patient_id).order_by(
            MentalHealth.assessment_date.desc()).all()

        # 获取AI助手分析报告
        imaging_reports = ImagingReport.query.filter_by(patient_id=patient_id).order_by(
            ImagingReport.report_date.desc()).all()

        return render_template('doctor/patient_info.html',
                              patient=patient,
                              medical_history=medical_history,
                              physical_exams=physical_exams,
                              brain_ct_scans=brain_ct_scans,
                              ct_followups=ct_followups,
                              neuro_assessments=neuro_assessments,
                              medication_records=medication_records,
                              mental_health=mental_health,
                              status=status,
                              status_color=status_color,
                              imaging_reports=imaging_reports)

    @app.route('/patients/<int:patient_id>/ct/add', methods=['GET', 'POST'])
    @login_required
    def add_ct_scan(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        if request.method == 'POST':
            new_scan = BrainCTScan(
                patient_id=patient_id,
                scan_date=datetime.strptime(request.form['scan_date'], '%Y-%m-%dT%H:%M'),
                scan_type=request.form['scan_type'],
                technician=request.form['technician'],
                radiologist=request.form['radiologist'],
                scan_reason=request.form['scan_reason'],
                brain_structure=request.form['brain_structure'],
                ventricle_status=request.form['ventricle_status'],
                skull_condition=request.form['skull_condition'],
                lesion_description=request.form['lesion_description'],
                hemorrhage_status=request.form['hemorrhage_status'],
                ischemia_status=request.form['ischemia_status'],
                atrophy_status=request.form['atrophy_status'],
                density_abnormalities=request.form['density_abnormalities'],
                conclusion=request.form['conclusion'],
                follow_up_recommended=request.form.get('follow_up_recommended') == 'on'
            )
            db.session.add(new_scan)
            db.session.commit()
            flash('添加CT扫描记录成功', 'success')
            return redirect(url_for('patient_medical_record', patient_id=patient_id))

        return render_template('doctor/predict.html', patient=patient, action='add')

    @app.route('/patients/<int:patient_id>/treatment', methods=['GET', 'POST'])
    @login_required
    def medical_patient_treatment(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        current_user = User.query.get(session.get('user_id'))
        today = date.today()

        # 检查当前用户是否为医生
        if current_user.role == 'doctor':
            # 在GET请求时检查患者状态，如果是"待就诊"，则自动更改为"治疗中"
            if request.method == 'GET' and patient.status == '待就诊':
                try:
                    patient.status = '治疗中'
                    patient.doctor_id = current_user.user_id
                    db.session.commit()
                    flash('患者状态已自动更新为"治疗中"', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash(f'更新患者状态失败: {str(e)}', 'error')

        if request.method == 'POST':
            action = request.form.get('action')

            if action == 'update_status':
                try:
                    new_status = request.form.get('status')
                    doctor_advice = request.form.get('doctor_advice')

                    if not new_status:
                        raise ValueError("请选择患者状态")
                        
                    # 验证状态值是否合法
                    valid_statuses = ['待就诊', '治疗中', '随访中', '已完成']
                    if new_status not in valid_statuses:
                        raise ValueError(f"无效的状态值: {new_status}")

                    # 更新患者状态
                    previous_status = patient.status
                    patient.status = new_status
                    patient.doctor_advice = doctor_advice
                    patient.doctor_id = current_user.user_id

                    # 确保医患关系记录存在
                    doctor_patient = DoctorPatientRelation.query.filter_by(
                        doctor_id=current_user.user_id,
                        patient_id=patient_id
                    ).first()

                    if not doctor_patient:
                        # 创建新的医患关系
                        doctor_patient = DoctorPatientRelation(
                            doctor_id=current_user.user_id,
                            patient_id=patient_id,
                            start_date=datetime.now(),
                            is_active=True,
                            relation_type='主治',
                            last_visit_date=datetime.now()
                        )
                        db.session.add(doctor_patient)
                    else:
                        # 更新已有医患关系的最近就诊日期
                        doctor_patient.last_visit_date = datetime.now()
                        doctor_patient.is_active = True

                    # 处理随访相关的状态
                    if new_status == '随访中' and doctor_patient:
                        # 如果状态变更为随访中，设置下次随访日期（默认为30天后）
                        next_visit_date = date.today() + timedelta(days=30)
                        doctor_patient.next_visit_date = next_visit_date

                    db.session.commit()
                    flash(f'患者状态已从"{previous_status}"更新为"{new_status}"', 'success')
                    return redirect(url_for('medical_patient_treatment', patient_id=patient_id))

                except ValueError as e:
                    flash(f'更新状态失败: {str(e)}', 'error')
                    db.session.rollback()
                except Exception as e:
                    flash(f'更新状态失败: {str(e)}', 'error')
                    db.session.rollback()

            elif action == 'update_advice':
                patient.doctor_advice = request.form.get('doctor_advice')
                patient.doctor_id = current_user.user_id
                db.session.commit()
                flash('医生建议已更新', 'success')

            elif action == 'add_physical_exam':
                try:
                    # 验证必填字段
                    required_fields = ['exam_date', 'heart_rate', 'respiratory_rate',
                                       'blood_pressure_systolic', 'blood_pressure_diastolic',
                                       'temperature', 'weight', 'height']
                    missing_fields = [field for field in required_fields if not request.form.get(field)]
                    if missing_fields:
                        raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

                    # 解析日期时间字符串
                    exam_date_str = request.form.get('exam_date')
                    exam_date = datetime.strptime(exam_date_str, '%Y-%m-%dT%H:%M')

                    # 创建体检记录
                    exam = PhysicalExam(
                        patient_id=patient_id,
                        exam_date=exam_date,
                        heart_rate=request.form.get('heart_rate'),
                        respiratory_rate=request.form.get('respiratory_rate'),
                        blood_pressure_systolic=request.form.get('blood_pressure_systolic'),
                        blood_pressure_diastolic=request.form.get('blood_pressure_diastolic'),
                        temperature=request.form.get('temperature'),
                        weight=request.form.get('weight'),
                        height=request.form.get('height')
                    )

                    db.session.add(exam)
                    db.session.commit()
                    flash('体检记录已添加', 'success')
                    return redirect(url_for('medical_patient_treatment', patient_id=patient_id))

                except ValueError as e:
                    flash(f'添加体检记录失败: {str(e)}', 'error')
                    db.session.rollback()
                except Exception as e:
                    flash(f'添加体检记录失败: {str(e)}', 'error')
                    db.session.rollback()

            elif action == 'add_mental_health':
                try:
                    # 验证必填字段
                    required_fields = ['assessment_date', 'anxiety_level', 'depression_level',
                                       'sleep_quality', 'status_summary', 'recommended_action']
                    missing_fields = [field for field in required_fields if not request.form.get(field)]
                    if missing_fields:
                        raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

                    mental_health = MentalHealth(
                        patient_id=patient_id,
                        assessment_date=datetime.strptime(request.form.get('assessment_date'), '%Y-%m-%dT%H:%M').date(),
                        anxiety_level=request.form.get('anxiety_level'),
                        depression_level=request.form.get('depression_level'),
                        sleep_quality=request.form.get('sleep_quality'),
                        status_summary=request.form.get('status_summary'),
                        recommended_action=request.form.get('recommended_action')
                    )
                    db.session.add(mental_health)
                    db.session.commit()
                    flash('心理健康评估已添加', 'success')
                    return redirect(url_for('medical_patient_treatment', patient_id=patient_id))
                except ValueError as e:
                    flash(f'添加心理健康评估失败: {str(e)}', 'error')
                    db.session.rollback()
                except Exception as e:
                    flash(f'添加心理健康评估失败: {str(e)}', 'error')
                    db.session.rollback()

            elif action == 'add_neuro_assessment':
                try:
                    # 验证必填字段
                    required_fields = ['assessment_date', 'gcs_score', 'mmse_score', 'moca_score',
                                       'motor_function', 'sensory_function', 'reflex_status',
                                       'coordination', 'cranial_nerve_exam', 'performed_by']
                    missing_fields = [field for field in required_fields if not request.form.get(field)]
                    if missing_fields:
                        raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

                    assessment = NeurologicalAssessment(
                        patient_id=patient_id,
                        assessment_date=datetime.strptime(request.form.get('assessment_date'), '%Y-%m-%dT%H:%M').date(),
                        gcs_score=request.form.get('gcs_score'),
                        mmse_score=request.form.get('mmse_score'),
                        moca_score=request.form.get('moca_score'),
                        motor_function=request.form.get('motor_function'),
                        sensory_function=request.form.get('sensory_function'),
                        reflex_status=request.form.get('reflex_status'),
                        coordination=request.form.get('coordination'),
                        cranial_nerve_exam=request.form.get('cranial_nerve_exam'),
                        assessment_notes=request.form.get('assessment_notes'),
                        performed_by=request.form.get('performed_by')
                    )
                    db.session.add(assessment)
                    db.session.commit()
                    flash('神经系统评估已添加', 'success')
                    return redirect(url_for('medical_patient_treatment', patient_id=patient_id))
                except ValueError as e:
                    flash(f'添加神经系统评估失败: {str(e)}', 'error')
                    db.session.rollback()
                except Exception as e:
                    flash(f'添加神经系统评估失败: {str(e)}', 'error')
                    db.session.rollback()

            elif action == 'add_medication':
                try:
                    # 验证必填字段
                    required_fields = ['medication_name', 'dosage', 'frequency', 'administration_route',
                                       'start_date', 'end_date']
                    missing_fields = [field for field in required_fields if not request.form.get(field)]
                    if missing_fields:
                        raise ValueError(f"缺少必填字段: {', '.join(missing_fields)}")

                    medication = MedicationRecord(
                        patient_id=patient_id,
                        medication_name=request.form.get('medication_name'),
                        dosage=request.form.get('dosage'),
                        frequency=request.form.get('frequency'),
                        administration_route=request.form.get('administration_route'),
                        start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
                        end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
                        indication=request.form.get('indication'),
                        side_effects=request.form.get('side_effects'),
                        effectiveness=request.form.get('effectiveness'),
                        notes=request.form.get('notes')
                    )
                    db.session.add(medication)
                    db.session.commit()
                    flash('用药记录已添加', 'success')
                    return redirect(url_for('medical_patient_treatment', patient_id=patient_id))
                except ValueError as e:
                    flash(f'添加用药记录失败: {str(e)}', 'error')
                    db.session.rollback()
                except Exception as e:
                    flash(f'添加用药记录失败: {str(e)}', 'error')
                    db.session.rollback()

        # 获取所有相关数据
        physical_exams = PhysicalExam.query.filter_by(patient_id=patient_id).order_by(
            PhysicalExam.exam_date.asc()).all()
        mental_health = MentalHealth.query.filter_by(patient_id=patient_id).order_by(
            MentalHealth.assessment_date.asc()).all()
        neuro_assessments = NeurologicalAssessment.query.filter_by(patient_id=patient_id).order_by(
            NeurologicalAssessment.assessment_date.asc()).all()
        medications = MedicationRecord.query.filter_by(patient_id=patient_id).order_by(
            MedicationRecord.start_date.asc()).all()

        return render_template('doctor/patient_treatment.html',
                              patient=patient,
                              current_user=current_user,
                              today=today,
                              physical_exams=physical_exams,
                              mental_health=mental_health,
                              neuro_assessments=neuro_assessments,
                              medications=medications)

    @app.route('/personal/<int:patient_id>')
    @login_required
    def personal_profile(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        status, status_color = "新患者", "info"
        if patient.brain_ct_scans:
            recent_ct = max(patient.brain_ct_scans, key=lambda x: x.scan_date)
            if (recent_ct.hemorrhage_status and
                    ("出血" in recent_ct.hemorrhage_status or
                     "血肿" in recent_ct.conclusion or
                     "紧急" in recent_ct.conclusion)):
                status, status_color = "需紧急处理", "danger"
            elif recent_ct.follow_up_recommended:
                status, status_color = "待随访", "warning"
            else:
                current_meds = any((m.end_date and m.end_date >= date.today()) or m.end_date is None for m in patient.medication_records)
                if current_meds:
                    status, status_color = "治疗中", "primary"
                else:
                    status, status_color = "已完成", "success"

        medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).first()
        physical_exams = PhysicalExam.query.filter_by(patient_id=patient_id).order_by(
            PhysicalExam.exam_date.desc()).all()
        brain_ct_scans = BrainCTScan.query.filter_by(patient_id=patient_id).order_by(BrainCTScan.scan_date.desc()).all()
        ct_followups = {
            scan.scan_id: CTFollowUp.query.filter_by(original_scan_id=scan.scan_id).order_by(
                CTFollowUp.follow_up_date).all()
            for scan in brain_ct_scans
        }
        neuro_assessments = NeurologicalAssessment.query.filter_by(patient_id=patient_id).order_by(
            NeurologicalAssessment.assessment_date.desc()).all()
        medication_records = MedicationRecord.query.filter_by(patient_id=patient_id).order_by(
            MedicationRecord.start_date.desc()).all()
        mental_health = MentalHealth.query.filter_by(patient_id=patient_id).order_by(
            MentalHealth.assessment_date.desc()).all()

        return render_template('patient/personal_patient_report.html',
                              patient=patient,
                              medical_history=medical_history,
                              physical_exams=physical_exams,
                              brain_ct_scans=brain_ct_scans,
                              ct_followups=ct_followups,
                              neuro_assessments=neuro_assessments,
                              medication_records=medication_records,
                              mental_health=mental_health,
                              status=status,
                              status_color=status_color)

    @app.route("/personal_record/<int:patient_id>")
    @login_required
    def personal_record(patient_id):
        patient = Patient.query.get_or_404(patient_id)
        user = User.query.filter_by(patient_id=patient_id).first()
        medical_history = MedicalHistory.query.filter_by(patient_id=patient_id).first()

        # 获取最新的体检记录
        physical_exam = PhysicalExam.query.filter_by(patient_id=patient_id).order_by(
            PhysicalExam.exam_date.desc()).first()

        # 获取最新的影像报告
        imaging_report = ImagingReport.query.filter_by(patient_id=patient_id).order_by(
            ImagingReport.created_at.desc()).first()

        # 获取最新的脑部CT扫描
        brain_ct_scan = BrainCTScan.query.filter_by(patient_id=patient_id).order_by(
            BrainCTScan.scan_date.desc()).first()

        # 获取最新的神经系统评估
        neuro_assessment = NeurologicalAssessment.query.filter_by(patient_id=patient_id).order_by(
            NeurologicalAssessment.assessment_date.desc()).first()

        # 获取最新的心理健康评估
        mental_health = MentalHealth.query.filter_by(patient_id=patient_id).order_by(
            MentalHealth.assessment_date.desc()).first()

        # 获取当前用药记录
        current_medications = MedicationRecord.query.filter(
            MedicationRecord.patient_id == patient_id,
            MedicationRecord.end_date != None,
            MedicationRecord.end_date >= date.today()
        ).all()

        # 获取开具医嘱的医生姓名
        doctor_name = None
        if patient.doctor_id:
            doctor = User.query.filter_by(user_id=patient.doctor_id, role='doctor').first()
            if doctor:
                doctor_name = doctor.real_name[0] + "医生"  # 取第一个字作为姓氏

        # 获取所有影像报告并按创建时间降序排序
        imaging_reports = ImagingReport.query.filter_by(patient_id=patient_id).order_by(
            ImagingReport.created_at.desc()).all()

        return render_template("patient/personal_patient_record.html",
                              patient=patient,
                              user=user,
                              medical_history=medical_history,
                              physical_exam=physical_exam,
                              imaging_reports=imaging_reports,
                              brain_ct_scan=brain_ct_scan,
                              neuro_assessment=neuro_assessment,
                              mental_health=mental_health,
                              current_medications=current_medications,
                              doctor_name=doctor_name)

    # 删除记录API端点
    @app.route('/patients/<int:report_id>/delete-report', methods=['POST'])
    @login_required
    def delete_imaging_report(report_id):
        try:
            report = ImagingReport.query.get_or_404(report_id)
            patient_id = report.patient_id

            # 删除报告
            db.session.delete(report)
            db.session.commit()

            return jsonify({
                "status": "success",
                "message": "分析报告已成功删除"
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除分析报告失败: {str(e)}"
            })

    @app.route('/patients/<int:record_id>/delete-physical-exam', methods=['POST'])
    @login_required
    def delete_physical_exam(record_id):
        try:
            exam = PhysicalExam.query.get_or_404(record_id)
            db.session.delete(exam)
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "体检记录已删除"
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除体检记录失败: {str(e)}"
            })

    @app.route('/patients/<int:record_id>/delete-mental-health', methods=['POST'])
    @login_required
    def delete_mental_health(record_id):
        try:
            record = MentalHealth.query.get_or_404(record_id)
            db.session.delete(record)
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "心理健康评估已删除"
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除心理健康评估失败: {str(e)}"
            })

    @app.route('/patients/<int:record_id>/delete-neuro-assessment', methods=['POST'])
    @login_required
    def delete_neuro_assessment(record_id):
        try:
            assessment = NeurologicalAssessment.query.get_or_404(record_id)
            db.session.delete(assessment)
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "神经系统评估已删除"
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除神经系统评估失败: {str(e)}"
            })

    @app.route('/patients/<int:record_id>/delete-medication', methods=['POST'])
    @login_required
    def delete_medication(record_id):
        try:
            medication = MedicationRecord.query.get_or_404(record_id)
            db.session.delete(medication)
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "用药记录已删除"
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"删除用药记录失败: {str(e)}"
            }) 