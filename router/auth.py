from flask import render_template, request, redirect, url_for, session, jsonify, flash
from datetime import datetime
from db_model import db, User, Patient, SystemLog, NotificationType
import re
from functools import wraps
from .notification_service import NotificationService


# 权限验证装饰器
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'doctor':
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def patient_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') or session.get('role') != 'patient':
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def auth_routes(app):
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """处理用户登录"""
        if request.method == 'POST':
            username = request.form.get("username")
            password = request.form.get("password")
            user = User.query.filter_by(username=username).first()

            if user and user.check_password(password):
                if not user.is_active:
                    return jsonify({"status": "error", "message": "账户已被禁用，请联系管理员"})
                session["logged_in"] = True
                session["user_id"] = user.user_id
                session["username"] = username
                session["role"] = user.role

                if user.role == 'patient':
                    session["patient_id"] = user.patient_id
                else:
                    session["patient_id"] = None

                user.last_login = datetime.now()
                db.session.commit()

                # 根据用户角色设置重定向地址
                if user.role == 'admin':
                    redirect_url = url_for("admin_index")
                else:
                    redirect_url = url_for("index")

                return jsonify({
                    "status": "success",
                    "redirect": redirect_url,
                    "message": f"欢迎回来，{user.real_name}!"
                })
            else:
                return jsonify({"status": "error", "message": "用户名或密码错误"})
        return render_template("public/login.html")

    @app.route('/logout')
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """处理新患者注册"""
        if request.method == 'POST':
            # 获取表单数据
            username = request.form.get("username")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")
            real_name = request.form.get("real_name")
            id_card = request.form.get("id_card")
            email = request.form.get("email", "")
            phone = request.form.get("phone", "")
            gender = request.form.get("gender", "男")
            age = request.form.get("age", 0)
            if age:
                try:
                    age = int(age)
                except ValueError:
                    return jsonify({"status": "error", "message": "年龄必须是数字"})

            address = request.form.get("address", "")
            blood_type = request.form.get("blood_type", "")
            emergency_contact = request.form.get("emergency_contact", "")

            # 基本验证
            if not all([username, password, confirm_password, real_name, id_card, phone]):
                return jsonify({"status": "error", "message": "请填写所有必填字段"})

            if password != confirm_password:
                return jsonify({"status": "error", "message": "两次输入的密码不一致"})

            # 简单验证密码强度
            if len(password) < 6:
                return jsonify({"status": "error", "message": "密码长度不能少于6个字符"})

            # 检查用户名是否已存在
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({"status": "error", "message": "用户名已存在"})

            # 检查身份证号是否已存在
            existing_id_card = User.query.filter_by(id_card=id_card).first()
            if existing_id_card:
                return jsonify({"status": "error", "message": "身份证号已被注册"})

            # 验证身份证号格式（简单验证为18位）
            if not re.match(r'^\d{17}[\dXx]$', id_card):
                return jsonify({"status": "error", "message": "请输入正确的18位身份证号"})

            # 验证手机号格式
            if not re.match(r'^1[3-9]\d{9}$', phone):
                return jsonify({"status": "error", "message": "请输入正确的手机号"})

            try:
                # 创建新患者记录
                new_patient = Patient(
                    name=real_name,
                    age=age,
                    gender=gender,
                    address=address,
                    contact_info=phone,
                    blood_type=blood_type,
                    emergency_contact=emergency_contact,
                    status='新患者'
                )
                db.session.add(new_patient)
                db.session.flush()

                # 创建新用户记录
                new_user = User(
                    username=username,
                    real_name=real_name,
                    id_card=id_card,
                    email=email,
                    phone=phone,
                    role='patient',
                    patient_id=new_patient.patient_id,
                    registration_date=datetime.now(),
                    is_active=True
                )
                new_user.set_password(password)

                db.session.add(new_user)
                db.session.commit()

                # --- 发送欢迎通知 ---
                try:
                    NotificationService.create_notification(
                        receiver_type='patient',
                        receiver_id=new_patient.patient_id,
                        notification_type=NotificationType.GENERAL,
                        title="欢迎加入智慧医疗平台",
                        message="您已成功注册！现在可以开始管理您的健康档案或预约就诊了。"
                    )
                    db.session.commit() # 提交通知
                except Exception as e:
                    # 即使通知失败，也不应影响注册流程
                    app.logger.error(f"发送新用户欢迎通知失败: {e}")
                # --- 通知结束 ---

                # 注册成功，自动登录
                session["logged_in"] = True
                session["user_id"] = new_user.user_id
                session["username"] = username
                session["role"] = 'patient'
                session["patient_id"] = new_patient.patient_id

                return jsonify({
                    "status": "success",
                    "redirect": url_for("index"),
                    "message": f"注册成功！欢迎，{real_name}!"
                })

            except Exception as e:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"注册失败: {str(e)}"})
        return render_template("public/register.html")

    # 检查用户名是否可用的API端点
    @app.route('/check_username', methods=['POST'])
    def check_username():
        username = request.form.get('username')

        # 用户名格式验证
        if not username:
            return jsonify({"available": False, "message": "用户名不能为空"})

        if len(username) < 3:
            return jsonify({"available": False, "message": "用户名长度至少为3个字符"})

        if not re.match(r'^[a-zA-Z0-9_]+$', username):
            return jsonify({"available": False, "message": "用户名只能包含字母、数字和下划线"})

        try:
            # 检查是否存在
            user = User.query.filter_by(username=username).first()
            if user:
                return jsonify({"available": False, "message": "用户名已被使用"})

            return jsonify({"available": True, "message": "用户名可用"})
        except Exception as e:
            print(f"检查用户名时出错: {str(e)}")
            return jsonify({"available": False, "message": "服务器错误，请重试"}), 500

    # 检查身份证号是否可用的API端点
    @app.route('/check_id_card', methods=['POST'])
    def check_id_card():
        id_card = request.form.get('id_card')

        # 身份证号格式验证
        if not id_card:
            return jsonify({"available": False, "message": "身份证号不能为空"})

        if not re.match(r'^(\d{15}|\d{18}|\d{17}[\dXx])$', id_card):
            return jsonify({"available": False, "message": "请输入正确的身份证号格式"})

        try:
            # 检查是否存在
            user = User.query.filter_by(id_card=id_card).first()
            if user:
                return jsonify({"available": False, "message": "此身份证号已被注册"})

            # 简单验证身份证的有效性（检查出生日期等）
            if len(id_card) == 18:
                # 验证出生日期
                try:
                    birth_year = int(id_card[6:10])
                    birth_month = int(id_card[10:12])
                    birth_day = int(id_card[12:14])

                    # 检查年份是否在合理范围内
                    current_year = datetime.now().year
                    if birth_year < 1900 or birth_year > current_year:
                        return jsonify({"available": False, "message": "身份证号中的出生年份无效"})

                    # 检查月份
                    if birth_month < 1 or birth_month > 12:
                        return jsonify({"available": False, "message": "身份证号中的出生月份无效"})

                    # 检查日期
                    if birth_day < 1 or birth_day > 31:
                        return jsonify({"available": False, "message": "身份证号中的出生日期无效"})

                    # 更复杂的日期验证可以加在这里
                except ValueError:
                    return jsonify({"available": False, "message": "身份证号中的出生日期格式错误"})

            return jsonify({"available": True, "message": "身份证号可用"})
        except Exception as e:
            print(f"检查身份证号时出错: {str(e)}")
            return jsonify({"available": False, "message": "服务器错误，请重试"}), 500

    @app.route('/admin_register', methods=['GET', 'POST'])
    @admin_required
    def admin_register():
        """管理员注册新用户"""
        if request.method == 'POST':
            # 获取表单数据
            username = request.form.get('username')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            role = request.form.get('role')
            real_name = request.form.get('real_name')
            id_card = request.form.get('id_card')
            email = request.form.get('email', '')
            phone = request.form.get('phone', '')

            # 验证表单数据
            if not all([username, password, confirm_password, role, real_name]):
                return jsonify({"status": "error", "message": "请填写所有必填字段"})

            if password != confirm_password:
                return jsonify({"status": "error", "message": "两次输入的密码不一致"})

            # 检查用户名是否已存在
            existing_user = User.query.filter_by(username=username).first()
            if existing_user:
                return jsonify({"status": "error", "message": "用户名已存在"})

            # 检查身份证号是否已存在
            if id_card:
                existing_id = User.query.filter_by(id_card=id_card).first()
                if existing_id:
                    return jsonify({"status": "error", "message": "身份证号已被注册"})

            try:
                # 如果是患者角色，需要创建患者记录
                patient_id = None
                if role == 'patient':
                    # 创建患者记录
                    patient = Patient(
                        name=real_name,
                        contact_info=phone,
                        status='新患者'
                    )
                    db.session.add(patient)
                    db.session.flush()
                    patient_id = patient.patient_id

                # 创建用户记录
                new_user = User(
                    username=username,
                    real_name=real_name,
                    id_card=id_card,
                    email=email,
                    phone=phone,
                    role=role,
                    patient_id=patient_id,
                    registration_date=datetime.now(),
                    is_active=True
                )
                new_user.set_password(password)
                db.session.add(new_user)

                # 记录管理员操作
                log = SystemLog(
                    user_id=session.get('user_id'),
                    username=session.get('username'),
                    operation='create',
                    description=f'管理员创建用户: {username}, 角色: {role}',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)

                db.session.commit()
                return jsonify({"status": "success", "message": "用户创建成功", "redirect": url_for('admin_user_list')})

            except Exception as e:
                db.session.rollback()
                return jsonify({"status": "error", "message": f"创建用户失败: {str(e)}"})

        return render_template("/admin/admin_register.html")

    @app.route('/admin_reg')
    def admin_reg_redirect():
        """直接重定向到管理员注册页面，无需权限验证"""
        return redirect(url_for('admin_register_public'))

    @app.route('/admin_register_public', methods=['GET', 'POST'])
    def admin_register_public():
        """公开的管理员注册页面，无需权限验证"""
        if request.method == 'POST':
            try:
                # 获取表单数据
                username = request.form.get('username')
                password = request.form.get('password')
                confirm_password = request.form.get('confirm_password')
                role = request.form.get('role')
                real_name = request.form.get('real_name')
                id_card = request.form.get('id_card')
                email = request.form.get('email', '')
                phone = request.form.get('phone', '')

                print(f"接收到注册请求: 用户名={username}, 角色={role}, 姓名={real_name}")

                # 验证表单数据
                if not all([username, password, confirm_password, role, real_name]):
                    return jsonify({"status": "error", "message": "请填写所有必填字段"})

                if password != confirm_password:
                    return jsonify({"status": "error", "message": "两次输入的密码不一致"})

                # 检查用户名是否已存在
                existing_user = User.query.filter_by(username=username).first()
                if existing_user:
                    return jsonify({"status": "error", "message": "用户名已存在"})

                # 检查身份证号是否已存在
                if id_card:
                    existing_id = User.query.filter_by(id_card=id_card).first()
                    if existing_id:
                        return jsonify({"status": "error", "message": "身份证号已被注册"})

                # 如果是患者角色，需要创建患者记录
                patient_id = None
                if role == 'patient':
                    # 创建患者记录
                    patient = Patient(
                        name=real_name,
                        contact_info=phone,
                        status='新患者'
                    )
                    db.session.add(patient)
                    db.session.flush()  # 获取自动生成的ID
                    patient_id = patient.patient_id
                    print(f"创建患者记录: patient_id={patient_id}")

                # 创建用户记录
                new_user = User(
                    username=username,
                    real_name=real_name,
                    id_card=id_card,
                    email=email,
                    phone=phone,
                    role=role,
                    patient_id=patient_id,
                    registration_date=datetime.now(),
                    is_active=True
                )
                new_user.set_password(password)
                db.session.add(new_user)

                # 记录系统日志
                log = SystemLog(
                    username="系统",
                    operation='create',
                    description=f'公开注册页面创建用户: {username}, 角色: {role}',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)

                db.session.commit()
                print(f"用户创建成功: user_id={new_user.user_id}, 角色={role}")

                return jsonify({
                    "status": "success",
                    "message": f"成功创建{role}账号: {username}",
                    "redirect": url_for('login')
                })

            except Exception as e:
                db.session.rollback()
                error_msg = f"创建用户失败: {str(e)}"
                print(f"错误: {error_msg}")
                return jsonify({"status": "error", "message": error_msg})

        return render_template("/admin/admin_register.html")
