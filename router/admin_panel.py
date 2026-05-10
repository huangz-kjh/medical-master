from flask import render_template, session, redirect, url_for, request, jsonify, flash, send_file, Blueprint, current_app
from db_model import db, User, Patient, SystemLog, SystemConfig, Appointment, ChatSession, AppointmentStatus, PageVisit
from datetime import datetime, timedelta
import os
import shutil
import subprocess
import logging
from router.auth import admin_required, login_required
import pandas as pd
from sqlalchemy import func, desc
import tempfile
from io import BytesIO
import json
import difflib
import re
from apscheduler.schedulers.background import BackgroundScheduler
from urllib.parse import urlparse
from sqlalchemy import create_engine, MetaData
import io

# 添加BackupSettings模型
class BackupSettings(db.Model):
    __tablename__ = 'backup_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    enable_auto_backup = db.Column(db.Boolean, default=False)
    backup_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly
    keep_backups = db.Column(db.Integer, default=5)
    last_backup_time = db.Column(db.DateTime)
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

admin_api = Blueprint('admin_api', __name__)

# 自动备份调度任务
scheduler = BackgroundScheduler()
def auto_backup_job():
    with current_app.app_context():
        settings = BackupSettings.query.first()
        if settings and settings.enable_auto_backup:
            # 触发自动备份
            app = current_app._get_current_object()
            try:
                app.logger.info('自动备份任务启动')
                # 复用已有的自动备份逻辑
                app.test_client().get('/admin/backup/auto')
            except Exception as e:
                app.logger.error(f'自动备份任务失败: {e}')

# 启动调度器（建议在主程序入口调用）
def start_admin_scheduler():
    scheduler.add_job(auto_backup_job, 'interval', hours=24, id='auto_backup')
    scheduler.start()

# RESTful API: 获取备份文件列表
@admin_api.route('/api/admin/backup/list', methods=['GET'])
@admin_required
def api_backup_list():
    backups_dir = os.path.join(current_app.root_path, 'backups')
    files = []
    for filename in os.listdir(backups_dir):
        if filename.startswith(('backup_', 'auto_')) and (filename.endswith('.db') or filename.endswith('.sql')):
            file_path = os.path.join(backups_dir, filename)
            file_stats = os.stat(file_path)
            files.append({
                'filename': filename,
                'size': round(file_stats.st_size / (1024 * 1024), 2),
                'create_time': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
            })
    files.sort(key=lambda x: x['create_time'], reverse=True)
    return jsonify({'code': 0, 'data': files})

# RESTful API: 批量删除备份
@admin_api.route('/api/admin/backup/delete', methods=['POST'])
@admin_required
def api_backup_delete():
    data = request.get_json()
    filenames = data.get('filenames', [])
    backups_dir = os.path.join(current_app.root_path, 'backups')
    deleted = []
    for filename in filenames:
        file_path = os.path.join(backups_dir, filename)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted.append(filename)
            except Exception as e:
                current_app.logger.error(f'删除备份失败: {filename}, {e}')
    # 记录日志
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='delete',
        description=f'批量删除备份: {deleted}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'deleted': deleted})

@admin_api.route('/api/admin/users/batch_update', methods=['POST'])
@admin_required
def api_batch_update_users():
    data = request.get_json()
    user_ids = data.get('user_ids', [])
    action = data.get('action')
    if not user_ids or action not in ['enable', 'disable', 'delete']:
        return jsonify({'code': 1, 'msg': '参数错误'})
    users = User.query.filter(User.user_id.in_(user_ids)).all()
    for user in users:
        if user.role == 'admin':
            continue  # 禁止对管理员操作
        if action == 'enable':
            user.is_active = True
        elif action == 'disable':
            user.is_active = False
        elif action == 'delete':
            db.session.delete(user)
    db.session.commit()
    # 记录日志
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='update',
        description=f'批量{action}用户: {user_ids}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '操作成功'})

@admin_api.route('/api/admin/users/<int:user_id>/toggle_active', methods=['POST'])
@admin_required
def api_toggle_user_active(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'code': 1, 'msg': '禁止对管理员操作'})
    user.is_active = not user.is_active
    db.session.commit()
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='update',
        description=f'切换用户状态: {user.username} -> {"启用" if user.is_active else "禁用"}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '操作成功', 'is_active': user.is_active})

@admin_api.route('/api/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def api_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'code': 1, 'msg': '禁止对管理员操作'})
    db.session.delete(user)
    db.session.commit()
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='delete',
        description=f'删除用户: {user.username}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '删除成功'})

@admin_api.route('/api/admin/users/<int:user_id>/reset_password', methods=['POST'])
@admin_required
def api_reset_password(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        return jsonify({'code': 1, 'msg': '禁止对管理员操作'})
    user.set_password('123456')
    db.session.commit()
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='update',
        description=f'重置密码: {user.username}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '密码已重置为123456'})

@admin_api.route('/api/admin/logs/batch_delete', methods=['POST'])
@admin_required
def api_batch_delete_logs():
    """批量删除日志，支持按操作类型、用户名、角色过滤"""
    data = request.get_json() or {}
    operation = data.get('operation')  # 操作类型，可选
    username = data.get('username')    # 用户名，可选
    role = data.get('role')            # 角色，可选
    start_date = data.get('start_date')
    end_date = data.get('end_date')

    query = SystemLog.query
    if operation:
        query = query.filter(SystemLog.operation == operation)
    if username:
        query = query.filter(SystemLog.username == username)
    if role:
        # 通过用户名查找用户角色
        user_ids = [u.user_id for u in User.query.filter_by(role=role).all()]
        query = query.filter(SystemLog.user_id.in_(user_ids))
    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        query = query.filter(SystemLog.create_time.between(start, end))

    logs_to_delete = query.all()
    count = len(logs_to_delete)
    for log in logs_to_delete:
        db.session.delete(log)
    db.session.commit()
    # 记录操作日志
    log = SystemLog(
        user_id=session.get('user_id'),
        username=session.get('username'),
        operation='delete',
        description=f'批量删除日志: 条数={count}, 操作类型={operation}, 用户名={username}, 角色={role}',
        ip=request.remote_addr,
        create_time=datetime.now()
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({'code': 0, 'msg': f'已删除{count}条日志'})

def init_admin_routes(app):
    @app.route('/admin')
    @admin_required
    def admin_index():
        # 统计数据
        user_count = User.query.count()
        patient_count = User.query.filter_by(role='patient').count()
        doctor_count = User.query.filter_by(role='doctor').count()
        
        # 从PageVisit表获取今日访问量
        today = datetime.now().date()
        today_visits = PageVisit.query.filter(PageVisit.visited_at >= today).count()
        # 新增预约和会话统计
        appointment_count = Appointment.query.count()
        pending_appointments = Appointment.query.filter_by(status=AppointmentStatus.PENDING).count()
        active_sessions = ChatSession.query.filter_by(is_active=True).count()
        total_sessions = ChatSession.query.count()
        
        return render_template("admin/index.html", 
                               current_user=User.query.get(session.get('user_id')),
                               user_count=user_count,
                               patient_count=patient_count,
                               doctor_count=doctor_count,
                               today_visits=today_visits,
                               appointment_count=appointment_count,
                               pending_appointments=pending_appointments,
                               active_sessions=active_sessions,
                               total_sessions=total_sessions,
                               datetime=datetime)

    @app.route('/admin/users')
    @admin_required
    def admin_user_list():
        users = User.query.all()
        return render_template("admin/user_list.html", 
                              users=users,
                              current_user=User.query.get(session.get('user_id')))

    @app.route('/admin/users/add', methods=['GET', 'POST'])
    @admin_required
    def admin_user_add():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            real_name = request.form.get('real_name')
            id_card = request.form.get('id_card')
            email = request.form.get('email')
            phone = request.form.get('phone')
            role = request.form.get('role')

            # 检查用户名是否已存在
            if User.query.filter_by(username=username).first():
                flash('用户名已存在', 'error')
                return redirect(url_for('admin_user_add'))

            # 创建新用户
            new_user = User(
                username=username,
                real_name=real_name,
                id_card=id_card,
                email=email,
                phone=phone,
                role=role,
                registration_date=datetime.now(),
                is_active=True
            )
            new_user.set_password(password)

            # 如果是患者角色，创建对应的患者记录
            if role == 'patient':
                patient = Patient(
                    name=real_name,
                    contact_info=phone,
                    status='新患者'
                )
                db.session.add(patient)
                db.session.flush()  # 获取patient_id
                new_user.patient_id = patient.patient_id

            db.session.add(new_user)
            
            # 记录操作日志
            log = SystemLog(
                user_id=session.get('user_id'),
                username=session.get('username'),
                operation='create',
                description=f'创建用户: {username}',
                ip=request.remote_addr,
                create_time=datetime.now()
            )
            db.session.add(log)
            
            db.session.commit()
            flash('用户添加成功', 'success')
            return redirect(url_for('admin_user_list'))

        return render_template("admin/user_add.html", 
                              current_user=User.query.get(session.get('user_id')))

    @app.route('/admin/users/edit/<int:user_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_user_edit(user_id):
        user = User.query.get_or_404(user_id)
        
        if request.method == 'POST':
            user.real_name = request.form.get('real_name')
            user.id_card = request.form.get('id_card')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.role = request.form.get('role')
            user.is_active = 'is_active' in request.form

            # 如果修改了密码
            new_password = request.form.get('password')
            if new_password:
                user.set_password(new_password)

            # 记录操作日志
            log = SystemLog(
                user_id=session.get('user_id'),
                username=session.get('username'),
                operation='update',
                description=f'更新用户: {user.username}',
                ip=request.remote_addr,
                create_time=datetime.now()
            )
            db.session.add(log)
            
            db.session.commit()
            flash('用户信息更新成功', 'success')
            return redirect(url_for('admin_user_list'))

        return render_template("admin/user_edit.html", 
                              user=user,
                              current_user=User.query.get(session.get('user_id')))

    @app.route('/admin/users/delete/<int:user_id>', methods=['POST'])
    @admin_required
    def admin_user_delete(user_id):
        user = User.query.get_or_404(user_id)
        
        # 不允许删除自己的账号
        if user_id == session.get('user_id'):
            flash('不能删除当前登录的账号', 'error')
            return redirect(url_for('admin_user_list'))
        
        # 记录被删除的用户名
        deleted_username = user.username
            
        db.session.delete(user)
        
        # 记录操作日志
        log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='delete',
            description=f'删除用户: {deleted_username}',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(log)
        
        db.session.commit()
        flash('用户删除成功', 'success')
        return redirect(url_for('admin_user_list'))
    
    @app.route('/admin/users/reset-password/<int:user_id>', methods=['POST'])
    @admin_required
    def admin_reset_password(user_id):
        user = User.query.get_or_404(user_id)
        
        # 设置默认密码123456
        user.set_password('123456')
        
        # 记录操作日志
        log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='update',
            description=f'重置密码: {user.username}',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(log)
        
        db.session.commit()
        flash(f'用户 {user.username} 密码已重置为: 123456', 'success')
        return redirect(url_for('admin_user_list'))

    @app.route('/admin/system-config', methods=['GET', 'POST'])
    @admin_required
    def admin_system_config():
        # 获取系统配置
        config = SystemConfig.query.first()
        if not config:
            # 如果没有配置，创建默认配置
            config = SystemConfig(
                system_name='医疗影像平台',
                system_description='基于Flask开发的医疗影像管理系统',
                system_logo='/static/img/logo.png',
                system_version='1.0.0',
                system_status=True
            )
            db.session.add(config)
            db.session.commit()
            
        success_message = None
        error_message = None
            
        if request.method == 'POST':
            try:
                # 处理系统配置更新
                config.system_name = request.form.get('system_name', config.system_name)
                config.system_description = request.form.get('system_description', config.system_description)
                config.system_logo = request.form.get('system_logo', config.system_logo)
                config.system_version = request.form.get('system_version', config.system_version)
                config.system_status = 'system_status' in request.form
                
                # 记录操作日志
                log = SystemLog(
                    user_id=session.get('user_id'),
                    username=session.get('username'),
                    operation='update',
                    description='更新系统配置',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)
                
                db.session.commit()
                flash('系统配置更新成功', 'success')
                success_message = '系统配置更新成功'
            except Exception as e:
                db.session.rollback()
                error_message = f'系统配置更新失败: {str(e)}'
                flash(error_message, 'error')
                
            return redirect(url_for('admin_system_config'))
            
        return render_template("admin/system_config.html", 
                              config=config,
                              success_message=success_message,
                              error_message=error_message,
                              current_user=User.query.get(session.get('user_id')))

    @app.route('/admin/logs')
    @admin_required
    def admin_logs():
        # 获取查询参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        operation = request.args.get('operation_type')
        username = request.args.get('username')
        
        # 基本查询
        query = SystemLog.query
        
        # 应用过滤条件
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')  # 使用当天结束时间
            query = query.filter(SystemLog.create_time.between(start, end))
        
        if operation:
            query = query.filter(SystemLog.operation == operation)
            
        if username:
            query = query.filter(SystemLog.username.like(f'%{username}%'))
        
        # 获取分页参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('limit', 10, type=int)
        
        # 执行查询
        pagination = query.order_by(SystemLog.create_time.desc()).paginate(
            page=page, per_page=per_page)
        logs = pagination.items
        
        return render_template("admin/logs.html", 
                              logs=logs,
                              pagination=pagination,
                              current_user=User.query.get(session.get('user_id')))

    @app.route('/admin/logs/export')
    @admin_required
    def admin_logs_export():
        """导出日志为CSV或Excel格式"""
        export_format = request.args.get('format', 'csv')
        
        # 获取过滤参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        operation = request.args.get('operation_type')
        username = request.args.get('username')
        
        # 基本查询
        query = SystemLog.query
        
        # 应用过滤条件
        if start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')  # 使用当天结束时间
            query = query.filter(SystemLog.create_time.between(start, end))
        
        if operation:
            query = query.filter(SystemLog.operation == operation)
            
        if username:
            query = query.filter(SystemLog.username.like(f'%{username}%'))
        
        # 执行查询并获取所有日志
        logs = query.order_by(SystemLog.create_time.desc()).all()
        
        # 准备数据
        data = []
        for log in logs:
            data.append({
                'ID': log.log_id,
                '用户ID': log.user_id,
                '用户名': log.username,
                '操作类型': log.operation,
                '操作描述': log.description,
                'IP地址': log.ip,
                '操作时间': log.create_time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
        # 记录导出操作
        export_log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='download',
            description=f'导出操作日志: {export_format}格式',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(export_log)
        db.session.commit()
        
        # 根据请求的格式导出
        if export_format == 'csv':
            # 创建CSV
            df = pd.DataFrame(data)
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            
            return send_file(
                output, 
                as_attachment=True,
                download_name=f'system_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                mimetype='text/csv'
            )
        elif export_format == 'excel':
            # 创建Excel
            df = pd.DataFrame(data)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='操作日志')
                # 调整列宽
                worksheet = writer.sheets['操作日志']
                for i, col in enumerate(df.columns):
                    max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                    worksheet.set_column(i, i, max_length)
            
            output.seek(0)
            
            return send_file(
                output,
                as_attachment=True,
                download_name=f'system_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx',
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            flash('不支持的导出格式', 'error')
            return redirect(url_for('admin_logs'))

    @app.route('/admin/logs/detail')
    @admin_required
    def admin_log_detail():
        """获取单条日志的详细信息"""
        log_id = request.args.get('log_id', type=int)
        if not log_id:
            return jsonify({'code': 1, 'msg': '缺少参数'})
            
        log = SystemLog.query.get(log_id)
        if not log:
            return jsonify({'code': 1, 'msg': '日志不存在'})
            
        # 返回日志详情
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'log_id': log.log_id,
                'user_id': log.user_id,
                'username': log.username,
                'operation': log.operation,
                'description': log.description,
                'ip': log.ip,
                'create_time': log.create_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        })

    @app.route('/admin/logs/stats')
    @admin_required
    def admin_log_stats():
        """获取日志统计数据"""
        # 统计操作类型分布
        operation_stats = db.session.query(
            SystemLog.operation, 
            func.count(SystemLog.log_id)
        ).group_by(SystemLog.operation).all()
        
        operation_types = [
            {'name': op[0], 'count': op[1]} 
            for op in operation_stats
        ]
        
        # 统计用户操作排行（取前10名）
        user_stats = db.session.query(
            SystemLog.username,
            func.count(SystemLog.log_id)
        ).filter(SystemLog.username != None).group_by(
            SystemLog.username
        ).order_by(func.count(SystemLog.log_id).desc()).limit(10).all()
        
        users = [
            {'username': user[0], 'count': user[1]}
            for user in user_stats
        ]
        
        # 统计每日操作趋势（最近30天）
        thirty_days_ago = datetime.now() - timedelta(days=30)
        
        # 查询数据库获取每日日志数量
        daily_logs = db.session.query(
            func.date(SystemLog.create_time).label('date'),
            func.count(SystemLog.log_id).label('count')
        ).filter(
            SystemLog.create_time >= thirty_days_ago
        ).group_by(
            func.date(SystemLog.create_time)
        ).order_by(
            func.date(SystemLog.create_time)
        ).all()
        
        # 处理日期数据
        trends = [
            {'date': log[0].strftime('%Y-%m-%d'), 'count': log[1]} 
            for log in daily_logs
        ]
        
        return jsonify({
            'code': 0,
            'msg': 'success',
            'data': {
                'operation_types': operation_types,
                'user_stats': users,
                'trends': trends
            }
        })
        
    @app.route('/admin/backup', methods=['GET', 'POST'])
    @admin_required
    def admin_backup():
        backups_dir = os.path.join(app.root_path, 'backups')
        # 确保备份目录存在
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)
            
        if request.method == 'POST':
            # 创建备份
            backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f'backup_{backup_time}.sql'
            backup_path = os.path.join(backups_dir, backup_name)
            
            # 备份数据库
            try:
                # 获取数据库连接信息
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
                
                if db_uri.startswith('sqlite:///'):
                    # SQLite数据库备份
                    db_path = db_uri.replace('sqlite:///', '')
                    # 复制数据库文件
                    shutil.copy2(db_path, backup_path.replace('.sql', '.db'))
                    backup_name = backup_name.replace('.sql', '.db')
                    backup_path = backup_path.replace('.sql', '.db')
                elif db_uri.startswith(('mysql://', 'mysql+pymysql://')):
                    # 用 SQLAlchemy 反射导出所有表结构和数据
                    engine = create_engine(db_uri)
                    meta = MetaData()
                    meta.reflect(bind=engine)
                    output = io.StringIO()
                    for table in meta.sorted_tables:
                        # 导出表结构
                        output.write(str(table.compile(dialect=engine.dialect)) + ';')
                        # 导出数据
                        conn = engine.connect()
                        rows = conn.execute(table.select()).fetchall()
                        if rows:
                            columns = ', '.join([c.name for c in table.columns])
                            for row in rows:
                                values = ', '.join([repr(v) for v in row])
                                output.write(f'INSERT INTO {table.name} ({columns}) VALUES ({values});\n')
                        conn.close()
                    with open(backup_path, 'w', encoding='utf-8') as f:
                        f.write(output.getvalue())
                    # 检查文件大小
                    if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
                        flash('备份失败: 生成的SQL文件为空', 'error')
                        logging.error('python-sqlalchemy导出SQL为空')
                        return redirect(url_for('admin_backup'))
                else:
                    flash('不支持的数据库类型', 'error')
                    return redirect(url_for('admin_backup'))
                
                # 记录操作日志
                log = SystemLog(
                    user_id=session.get('user_id'),
                    username=session.get('username'),
                    operation='backup',
                    description=f'创建数据库备份: {backup_name}',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)
                db.session.commit()
                
                flash('数据库备份成功', 'success')
            except Exception as e:
                logging.error(f"备份失败: {str(e)}")
                flash(f'备份失败: {str(e)}', 'error')
                
            return redirect(url_for('admin_backup'))
        
        # 获取所有备份
        backups = []
        for filename in os.listdir(backups_dir):
            if filename.startswith(('backup_', 'auto_')) and (filename.endswith('.db') or filename.endswith('.sql')):
                file_path = os.path.join(backups_dir, filename)
                file_stats = os.stat(file_path)
                backups.append({
                    'filename': filename,
                    'size': round(file_stats.st_size / (1024 * 1024), 2),  # 转换为MB
                    'create_time': datetime.fromtimestamp(file_stats.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                })
        
        # 按创建时间降序排序
        backups.sort(key=lambda x: x['create_time'], reverse=True)
        
        # 获取备份设置
        backup_settings = BackupSettings.query.first()
            
        return render_template("admin/backup.html", 
                              backups=backups,
                              backup_settings=backup_settings,
                              current_user=User.query.get(session.get('user_id')))
    
    @app.route('/admin/backup/settings', methods=['POST'])
    @admin_required
    def admin_backup_settings():
        """保存自动备份设置"""
        try:
            # 获取表单数据
            logging.info('开始处理备份设置请求')
            logging.info('请求表单数据: %s', request.form)
            
            enable_auto_backup = 'enable_auto_backup' in request.form
            backup_frequency = request.form.get('backup_frequency', 'daily')
            keep_backups = request.form.get('keep_backups', 5, type=int)
            
            logging.info('解析后的设置: enable_auto_backup=%s, backup_frequency=%s, keep_backups=%s',
                        enable_auto_backup, backup_frequency, keep_backups)
            
            # 更新或创建设置
            settings = BackupSettings.query.first()
            if not settings:
                logging.info('创建新的备份设置')
                settings = BackupSettings(
                    enable_auto_backup=enable_auto_backup,
                    backup_frequency=backup_frequency,
                    keep_backups=keep_backups
                )
                db.session.add(settings)
            else:
                logging.info('更新现有备份设置')
                settings.enable_auto_backup = enable_auto_backup
                settings.backup_frequency = backup_frequency
                settings.keep_backups = keep_backups
                settings.update_time = datetime.now()
            
            # 记录操作日志
            log = SystemLog(
                user_id=session.get('user_id'),
                username=session.get('username'),
                operation='update',
                description='更新自动备份设置',
                ip=request.remote_addr,
                create_time=datetime.now()
            )
            db.session.add(log)
            
            # 提交事务
            db.session.commit()
            logging.info('备份设置保存成功')
            
            # 构造详细提示
            freq_map = {'daily': '每天', 'weekly': '每周', 'monthly': '每月'}
            if enable_auto_backup:
                msg = f"启用自动备份成功，频率：{freq_map.get(backup_frequency, backup_frequency)}，保留数量：{keep_backups}"
            else:
                msg = "关闭自动备份成功"
            
            # 支持AJAX弹窗和页面跳转
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                logging.info('返回AJAX响应: %s', msg)
                return jsonify({'code': 0, 'msg': msg})
            else:
                flash(msg, 'success')
                return redirect(url_for('admin_backup'))
                
        except Exception as e:
            logging.error('保存备份设置时发生错误: %s', str(e), exc_info=True)
            error_msg = f'保存设置失败: {str(e)}'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'code': 1, 'msg': error_msg})
            else:
                flash(error_msg, 'error')
                return redirect(url_for('admin_backup'))
    
    @app.route('/admin/backup/delete-all', methods=['POST'])
    @admin_required
    def admin_delete_all_backups():
        """删除所有备份文件"""
        backups_dir = os.path.join(app.root_path, 'backups')
        deleted_count = 0
        
        for filename in os.listdir(backups_dir):
            if (filename.startswith('backup_') or filename.startswith('auto_')) and (filename.endswith('.db') or filename.endswith('.sql')):
                file_path = os.path.join(backups_dir, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"删除备份 {filename} 失败: {str(e)}")
        
        # 记录操作日志
        log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='delete',
            description=f'删除所有备份文件: {deleted_count} 个文件',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'已删除 {deleted_count} 个备份文件', 'success')
        return redirect(url_for('admin_backup'))
    
    @app.route('/admin/backup/delete-old', methods=['POST'])
    @admin_required
    def admin_delete_old_backups():
        """删除旧备份文件，保留最新的几个"""
        keep_count = request.form.get('keep_count', 3, type=int)
        if keep_count < 1:
            keep_count = 1
            
        backups_dir = os.path.join(app.root_path, 'backups')
        backups = []
        
        for filename in os.listdir(backups_dir):
            if (filename.startswith('backup_') or filename.startswith('auto_')) and (filename.endswith('.db') or filename.endswith('.sql')):
                file_path = os.path.join(backups_dir, filename)
                file_stats = os.stat(file_path)
                backups.append({
                    'filename': filename,
                    'path': file_path,
                    'create_time': datetime.fromtimestamp(file_stats.st_ctime)
                })
        
        # 按创建时间降序排序
        backups.sort(key=lambda x: x['create_time'], reverse=True)
        
        # 删除旧备份
        deleted_count = 0
        for i, backup in enumerate(backups):
            if i >= keep_count:
                try:
                    os.remove(backup['path'])
                    deleted_count += 1
                except Exception as e:
                    logging.error(f"删除备份 {backup['filename']} 失败: {str(e)}")
        
        # 记录操作日志
        log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='delete',
            description=f'删除旧备份文件: {deleted_count} 个文件, 保留 {keep_count} 个最新备份',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        flash(f'已删除 {deleted_count} 个旧备份文件，保留 {keep_count} 个最新备份', 'success')
        return redirect(url_for('admin_backup'))
    
    @app.route('/admin/backup/compare', methods=['POST'])
    @admin_required
    def admin_compare_backups():
        """比较两个备份文件的差异"""
        backup_a = request.form.get('backup_a')
        backup_b = request.form.get('backup_b')
        
        if not backup_a or not backup_b:
            flash('请选择要比较的备份文件', 'error')
            return redirect(url_for('admin_backup'))
            
        backups_dir = os.path.join(app.root_path, 'backups')
        file_a_path = os.path.join(backups_dir, backup_a)
        file_b_path = os.path.join(backups_dir, backup_b)
        
        if not os.path.exists(file_a_path) or not os.path.exists(file_b_path):
            flash('选择的备份文件不存在', 'error')
            return redirect(url_for('admin_backup'))
            
        # 比较文件大小
        file_a_size = os.path.getsize(file_a_path)
        file_b_size = os.path.getsize(file_b_path)
        size_diff = abs(file_a_size - file_b_size)
        size_diff_percent = round((size_diff / max(file_a_size, file_b_size)) * 100, 2)
        
        # 比较创建时间
        file_a_time = os.path.getctime(file_a_path)
        file_b_time = os.path.getctime(file_b_path)
        time_diff = abs(file_a_time - file_b_time)
        time_diff_days = round(time_diff / (60 * 60 * 24), 2)
        
        # 更详细的比较需要根据数据库类型和内容进行
        comparison_result = {
            'backup_a': backup_a,
            'backup_b': backup_b,
            'file_a_size': round(file_a_size / (1024 * 1024), 2),  # MB
            'file_b_size': round(file_b_size / (1024 * 1024), 2),  # MB
            'size_diff': round(size_diff / (1024 * 1024), 2),  # MB
            'size_diff_percent': size_diff_percent,
            'file_a_time': datetime.fromtimestamp(file_a_time).strftime('%Y-%m-%d %H:%M:%S'),
            'file_b_time': datetime.fromtimestamp(file_b_time).strftime('%Y-%m-%d %H:%M:%S'),
            'time_diff_days': time_diff_days
        }
        
        # 记录操作日志
        log = SystemLog(
            user_id=session.get('user_id'),
            username=session.get('username'),
            operation='compare',
            description=f'比较备份文件: {backup_a} 和 {backup_b}',
            ip=request.remote_addr,
            create_time=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        
        return render_template("admin/backup_compare.html",
                              comparison=comparison_result,
                              current_user=User.query.get(session.get('user_id')))
    
    @app.route('/admin/backup/auto', methods=['GET'])
    @admin_required
    def admin_trigger_auto_backup():
        """触发自动备份（用于测试自动备份功能）"""
        backups_dir = os.path.join(app.root_path, 'backups')
        if not os.path.exists(backups_dir):
            os.makedirs(backups_dir)
        # 创建自动备份
        backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'auto_{backup_time}.sql'
        backup_path = os.path.join(backups_dir, backup_name)
        try:
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                shutil.copy2(db_path, backup_path.replace('.sql', '.db'))
                backup_name = backup_name.replace('.sql', '.db')
                backup_path = backup_path.replace('.sql', '.db')
            elif db_uri.startswith(('mysql://', 'mysql+pymysql://')):
                # 用 SQLAlchemy 反射导出所有表结构和数据
                engine = create_engine(db_uri)
                meta = MetaData()
                meta.reflect(bind=engine)
                output = io.StringIO()
                for table in meta.sorted_tables:
                    output.write(str(table.compile(dialect=engine.dialect)) + ';')
                    conn = engine.connect()
                    rows = conn.execute(table.select()).fetchall()
                    if rows:
                        columns = ', '.join([c.name for c in table.columns])
                        for row in rows:
                            values = ', '.join([repr(v) for v in row])
                            output.write(f'INSERT INTO {table.name} ({columns}) VALUES ({values});\n')
                    conn.close()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(output.getvalue())
                if not os.path.exists(backup_path) or os.path.getsize(backup_path) == 0:
                    flash('自动备份失败: 生成的SQL文件为空', 'error')
                    logging.error('python-sqlalchemy导出SQL为空')
                    return redirect(url_for('admin_backup'))
            else:
                flash('不支持的数据库类型', 'error')
                return redirect(url_for('admin_backup'))
            settings = BackupSettings.query.first()
            if settings:
                settings.last_backup_time = datetime.now()
                db.session.commit()
            log = SystemLog(
                user_id=session.get('user_id'),
                username=session.get('username'),
                operation='backup',
                description=f'触发自动备份: {backup_name}',
                ip=request.remote_addr,
                create_time=datetime.now()
            )
            db.session.add(log)
            db.session.commit()
            clean_old_backups(app, settings.keep_backups if settings else 5)
            flash('自动备份成功', 'success')
        except Exception as e:
            logging.error(f"自动备份失败: {str(e)}")
            flash(f'自动备份失败: {str(e)}', 'error')
        return redirect(url_for('admin_backup'))
        
    @app.route('/admin/backup/download/<filename>')
    @admin_required
    def admin_download_backup(filename):
        backups_dir = os.path.join(app.root_path, 'backups')
        file_path = os.path.join(backups_dir, filename)
        
        if os.path.exists(file_path):
            # 记录操作日志
            log = SystemLog(
                user_id=session.get('user_id'),
                username=session.get('username'),
                operation='download',
                description=f'下载数据库备份: {filename}',
                ip=request.remote_addr,
                create_time=datetime.now()
            )
            db.session.add(log)
            db.session.commit()
            
            return send_file(file_path, as_attachment=True)
        else:
            flash('备份文件不存在', 'error')
            return redirect(url_for('admin_backup'))
    
    @app.route('/admin/backup/restore/<filename>', methods=['POST'])
    @admin_required
    def admin_restore_backup(filename):
        backups_dir = os.path.join(app.root_path, 'backups')
        backup_path = os.path.join(backups_dir, filename)
        
        if os.path.exists(backup_path):
            try:
                # 获取数据库连接信息
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
                
                if filename.endswith('.db') and db_uri.startswith('sqlite:///'):
                    # SQLite数据库恢复
                    db_path = db_uri.replace('sqlite:///', '')
                    
                    # 关闭数据库连接
                    db.session.close()
                    
                    # 备份当前数据库
                    current_backup = f'pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
                    current_backup_path = os.path.join(backups_dir, current_backup)
                    shutil.copy2(db_path, current_backup_path)
                    
                    # 恢复数据库
                    shutil.copy2(backup_path, db_path)
                    
                    # 重新建立数据库连接
                    db.engine.dispose()
                    
                elif filename.endswith('.sql') and db_uri.startswith(('mysql://', 'mysql+pymysql://')):
                    # MySQL数据库恢复
                    # 解析连接字符串
                    if 'mysql+pymysql://' in db_uri:
                        parts = db_uri.replace('mysql+pymysql://', '').split('@')
                    else:
                        parts = db_uri.replace('mysql://', '').split('@')
                    
                    user_pass = parts[0].split(':')
                    host_db = parts[1].split('/')
                    
                    username = user_pass[0]
                    password = user_pass[1].split('@')[0]
                    host = host_db[0]
                    database = host_db[1].split('?')[0]
                    
                    # 使用mysql命令恢复
                    cmd = f"mysql -u{username} -p{password} -h{host} {database} < {backup_path}"
                    subprocess.run(cmd, shell=True, check=True)
                else:
                    flash('备份文件与当前数据库类型不匹配', 'error')
                    return redirect(url_for('admin_backup'))
                
                flash('数据库恢复成功', 'success')
                
                # 记录操作日志 (需要在新的会话中)
                log = SystemLog(
                    user_id=session.get('user_id'),
                    username=session.get('username'),
                    operation='restore',
                    description=f'恢复数据库备份: {filename}',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)
                db.session.commit()
                
            except Exception as e:
                logging.error(f"恢复失败: {str(e)}")
                flash(f'恢复失败: {str(e)}', 'error')
        else:
            flash('备份文件不存在', 'error')
            
        return redirect(url_for('admin_backup'))
    
    @app.route('/admin/backup/delete/<filename>', methods=['POST'])
    @admin_required
    def admin_delete_backup(filename):
        backups_dir = os.path.join(app.root_path, 'backups')
        file_path = os.path.join(backups_dir, filename)
        
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                
                # 记录操作日志
                log = SystemLog(
                    user_id=session.get('user_id'),
                    username=session.get('username'),
                    operation='delete',
                    description=f'删除数据库备份: {filename}',
                    ip=request.remote_addr,
                    create_time=datetime.now()
                )
                db.session.add(log)
                db.session.commit()
                
                flash('备份文件删除成功', 'success')
            except Exception as e:
                flash(f'删除失败: {str(e)}', 'error')
        else:
            flash('备份文件不存在', 'error')
            
        return redirect(url_for('admin_backup'))
        
    @app.route('/admin/stats')
    @admin_required
    def admin_stats():
        """管理员仪表盘的统计数据API"""
        stats = {
            'total_users': User.query.count(),
            'patient_count': User.query.filter_by(role='patient').count(),
            'doctor_count': User.query.filter_by(role='doctor').count(),
            'admin_count': User.query.filter_by(role='admin').count(),
            'active_users': User.query.filter_by(is_active=True).count()
        }
        
        # 获取最近注册的用户
        recent_users = User.query.order_by(User.registration_date.desc()).limit(10).all()
        recent_user_data = [{
            'id': user.user_id,
            'username': user.username,
            'real_name': user.real_name,
            'role': user.role,
            'registration_date': user.registration_date.strftime('%Y-%m-%d %H:%M')
        } for user in recent_users]
        
        return jsonify({
            'status': 'success',
            'stats': stats,
            'recent_users': recent_user_data
        })

def clean_old_backups(app, keep_count=5):
    """清理过期的自动备份文件，保留最新的几个"""
    if keep_count < 1:
        keep_count = 1
        
    backups_dir = os.path.join(app.root_path, 'backups')
    backups = []
    
    for filename in os.listdir(backups_dir):
        if filename.startswith('auto_') and (filename.endswith('.db') or filename.endswith('.sql')):
            file_path = os.path.join(backups_dir, filename)
            file_stats = os.stat(file_path)
            backups.append({
                'filename': filename,
                'path': file_path,
                'create_time': datetime.fromtimestamp(file_stats.st_ctime)
            })
    
    # 按创建时间降序排序
    backups.sort(key=lambda x: x['create_time'], reverse=True)
    
    # 删除旧备份
    for i, backup in enumerate(backups):
        if i >= keep_count:
            try:
                os.remove(backup['path'])
                logging.info(f"已删除过期自动备份: {backup['filename']}")
            except Exception as e:
                logging.error(f"删除过期自动备份 {backup['filename']} 失败: {str(e)}") 