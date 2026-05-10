from flask import session, jsonify, request, redirect, url_for, render_template
from db_model import User, Patient, db
from router.auth import login_required
import re


def init_user_profile_routes(app):
    @app.route('/profile')
    @login_required
    def profile():
        if not session.get('logged_in'):
            return render_template('public/login.html')
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        patient = None
        if user.role == 'patient' and user.patient_id:
            patient = Patient.query.get(user.patient_id)
        return render_template('public/user_profile.html', user=user, patient=patient)

    @app.route('/user_profile')
    def user_profile():
        return render_template('public/user_profile.html')

    @app.route('/get_user_profile', methods=['GET'])
    @login_required
    def get_user_profile():
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "用户不存在"})

        try:
            user_data = {
                "username": user.username or "",
                "real_name": user.real_name or "",
                "id_card": user.id_card or "",
                "email": user.email or "",
                "phone": user.phone or "",
                "role": user.role or "",
                "registration_date": user.registration_date.strftime(
                    '%Y-%m-%d %H:%M:%S') if user.registration_date else None,
                "last_login": user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                "is_active": user.is_active
            }

            if user.role == 'patient' and user.patient_id:
                patient = Patient.query.get(user.patient_id)
                if patient:
                    user_data["address"] = patient.address or ""

                    # 处理紧急联系人字段
                    emergency_contact = patient.emergency_contact
                    if emergency_contact and re.search('[\u4e00-\u9fa5]', emergency_contact):
                        user_data["emergency_contact"] = emergency_contact
                    else:
                        user_data["emergency_contact"] = "无"

            return jsonify({"status": "success", "data": user_data})
        except Exception as e:
            print(f"获取用户资料时发生错误: {str(e)}")
            return jsonify({"status": "error", "message": "获取用户资料失败"})

    @app.route('/get_user_role', methods=['GET'])
    @login_required
    def get_user_role():
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({"status": "error", "message": "用户不存在"})
        return jsonify({"status": "success", "role": user.role})

    @app.route('/update_profile', methods=['POST'])
    @login_required
    def update_profile():
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({"status": "error", "message": "用户不存在"})

        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        emergency_contact = request.form.get("emergency_contact")

        # 验证手机号（如果提供）
        if phone and not re.match(r'^1[3-9]\d{9}$', phone):
            return jsonify({"status": "error", "message": "请输入正确的手机号"})

        # 验证紧急联系人电话（如果提供）
        if emergency_contact and emergency_contact != "无":
            try:
                emergency_phone = emergency_contact.split(":")[1]
                if not re.match(r'^1[3-9]\d{9}$', emergency_phone):
                    return jsonify({"status": "error", "message": "请输入正确的紧急联系人电话"})
            except:
                return jsonify({"status": "error", "message": "紧急联系人信息格式不正确"})

        # 更新用户信息
        if email:
            user.email = email
        if phone:
            user.phone = phone

        # 如果是患者，同时更新患者信息
        if user.role == 'patient' and user.patient_id:
            patient = Patient.query.get(user.patient_id)
            if patient:
                if phone:
                    patient.contact_info = phone
                if address:
                    patient.address = address
                if emergency_contact:
                    patient.emergency_contact = emergency_contact

        try:
            db.session.commit()
            return jsonify({"status": "success", "message": "个人资料更新成功"})
        except Exception as e:
            db.session.rollback()
            print(f"数据库更新失败: {str(e)}")
            return jsonify({"status": "error", "message": f"更新失败: {str(e)}"})

    @app.route('/change_password', methods=['POST'])
    @login_required
    def change_password():
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        if not user:
            return jsonify({"status": "error", "message": "用户不存在"})

        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # 校验当前密码
        if not user.check_password(current_password):
            return jsonify({"status": "error", "message": "当前密码不正确"})

        # 校验新密码长度
        if not new_password or len(new_password) < 6:
            return jsonify({"status": "error", "message": "新密码长度不能少于6个字符"})

        # 校验新密码一致性
        if new_password != confirm_password:
            return jsonify({"status": "error", "message": "两次输入的新密码不一致"})

        try:
            user.set_password(new_password)
            db.session.commit()
            return jsonify({
                "status": "success",
                "message": "密码修改成功,即将跳转主页",
                "redirect": url_for("dashboard")
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                "status": "error",
                "message": f"密码修改失败: {str(e)}"
            }) 