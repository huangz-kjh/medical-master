from flask import Blueprint, render_template, jsonify, request, session
from db_model import db, Appointment, AppointmentStatus, User, Department
from datetime import datetime, timedelta
from sqlalchemy import func, case, extract, and_, or_
from router.auth import login_required, admin_required
import calendar
import json

# 创建蓝图
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/dashboard')
@login_required
@admin_required
def analytics_dashboard():
    """管理员数据分析仪表盘页面"""
    return render_template('admin/analytics_dashboard.html')

@analytics_bp.route('/api/analytics/summary')
@login_required
@admin_required
def get_analytics_summary():
    """获取预约统计概要数据"""
    # 获取时间范围参数，默认过去30天
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    # 获取所有预约统计
    total_appointments = Appointment.query.filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).count()

    # 按状态统计预约数量
    status_counts = db.session.query(
        Appointment.status,
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).group_by(Appointment.status).all()

    # 构建状态计数字典
    status_data = {}
    for status, count in status_counts:
        # 将Enum值转换为字符串
        status_key = status.value if hasattr(status, 'value') else str(status)
        status_data[status_key] = count

    # 计算各种比率
    completed_count = status_data.get('completed', 0)
    confirmed_count = status_data.get('confirmed', 0)
    cancelled_count = status_data.get('cancelled', 0)
    rejected_count = status_data.get('rejected', 0)
    pending_count = status_data.get('pending', 0)

    # 计算完成率、取消率等
    completion_rate = round(completed_count / total_appointments * 100, 2) if total_appointments > 0 else 0
    cancellation_rate = round((cancelled_count + rejected_count) / total_appointments * 100, 2) if total_appointments > 0 else 0
    confirmation_rate = round(confirmed_count / (pending_count + confirmed_count) * 100, 2) if (pending_count + confirmed_count) > 0 else 0

    # 获取今日预约数
    today = datetime.now().date()
    today_appointments = Appointment.query.filter(
        Appointment.appointment_date == today
    ).count()

    # 获取本周预约数
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    week_appointments = Appointment.query.filter(
        Appointment.appointment_date.between(start_of_week, end_of_week)
    ).count()

    return jsonify({
        "status": "success",
        "data": {
            "total_appointments": total_appointments,
            "status_counts": status_data,
            "completion_rate": completion_rate,
            "cancellation_rate": cancellation_rate,
            "confirmation_rate": confirmation_rate,
            "today_appointments": today_appointments,
            "week_appointments": week_appointments,
            "time_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            }
        }
    })

@analytics_bp.route('/api/analytics/department-workload')
@login_required
@admin_required
def get_department_workload():
    """获取各科室工作量数据"""
    # 获取时间范围参数，默认过去30天
    days = request.args.get('days', 30, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    # 按科室统计预约数量
    department_counts = db.session.query(
        Appointment.department,
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).group_by(Appointment.department).all()

    # 按科室统计已完成预约数量
    completed_counts = db.session.query(
        Appointment.department,
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date),
        Appointment.status == AppointmentStatus.COMPLETED
    ).group_by(Appointment.department).all()

    # 构建科室数据
    departments_data = []
    department_map = {}

    for dept, count in department_counts:
        # 将Enum值转换为可读名称
        dept_name = dept.display_name if hasattr(dept, 'display_name') else str(dept)
        dept_value = dept.value if hasattr(dept, 'value') else str(dept)
        
        # 找到该科室已完成的预约数
        completed = 0
        for completed_dept, completed_count in completed_counts:
            if completed_dept == dept:
                completed = completed_count
                break
        
        # 计算完成率
        completion_rate = round(completed / count * 100, 2) if count > 0 else 0
        
        dept_data = {
            "department": dept_name,
            "department_value": dept_value,
            "total": count,
            "completed": completed,
            "completion_rate": completion_rate
        }
        
        departments_data.append(dept_data)
        department_map[dept_value] = dept_data
    
    # 按总数排序
    departments_data.sort(key=lambda x: x["total"], reverse=True)
    
    return jsonify({
        "status": "success",
        "data": {
            "departments": departments_data,
            "department_map": department_map,
            "time_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            }
        }
    })

@analytics_bp.route('/api/analytics/time-distribution')
@login_required
@admin_required
def get_time_distribution():
    """获取预约时间分布数据"""
    # 获取时间范围参数，默认过去90天
    days = request.args.get('days', 90, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    # 按日期统计预约数量
    daily_counts = db.session.query(
        Appointment.appointment_date,
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).group_by(Appointment.appointment_date).all()

    # 按星期几统计预约数量
    weekday_counts = db.session.query(
        extract('dow', Appointment.appointment_date),  # 0是星期日，1是星期一
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).group_by(extract('dow', Appointment.appointment_date)).all()

    # 构建日期数据
    daily_data = []
    for date, count in daily_counts:
        daily_data.append({
            "date": date.strftime('%Y-%m-%d'),
            "count": count
        })

    # 转换为星期数据，调整为周一为1的格式
    weekday_data = [0] * 7  # 初始化为7天全0
    for dow, count in weekday_counts:
        # 确保星期一是索引0，星期日是索引6
        index = (int(dow) - 1) % 7  # 将数据库返回的0-6(周日-周六)转为1-7(周一-周日)，然后再转到0-6的索引
        weekday_data[index] = count
    
    # 创建星期几标签
    weekday_labels = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    return jsonify({
        "status": "success",
        "data": {
            "daily": daily_data,
            "weekday": {
                "labels": weekday_labels,
                "data": weekday_data
            },
            "time_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            }
        }
    })

@analytics_bp.route('/api/analytics/patient-frequency')
@login_required
@admin_required
def get_patient_frequency():
    """获取患者就诊频率分析数据"""
    # 获取时间范围参数，默认过去365天
    days = request.args.get('days', 365, type=int)
    start_date = datetime.now().date() - timedelta(days=days)
    end_date = datetime.now().date()

    # 按患者ID统计预约次数
    patient_counts = db.session.query(
        Appointment.patient_id,
        func.count(Appointment.appointment_id)
    ).filter(
        Appointment.appointment_date.between(start_date, end_date)
    ).group_by(Appointment.patient_id).all()

    # 分组统计：只来过1次，2-3次，4-6次，7-10次，10次以上
    frequency_groups = {
        "once": 0,           # 1次
        "few": 0,            # 2-3次
        "regular": 0,        # 4-6次
        "frequent": 0,       # 7-10次
        "very_frequent": 0   # 10次以上
    }

    # 获取高频患者数据（大于等于4次）
    frequent_patients = []

    for patient_id, count in patient_counts:
        # 更新频率分组计数
        if count == 1:
            frequency_groups["once"] += 1
        elif count <= 3:
            frequency_groups["few"] += 1
        elif count <= 6:
            frequency_groups["regular"] += 1
            # 添加到常规患者列表
            patient = db.session.query(
                Appointment.patient_id,
                User.real_name
            ).join(
                User, User.patient_id == Appointment.patient_id
            ).filter(
                Appointment.patient_id == patient_id
            ).first()
            
            if patient:
                frequent_patients.append({
                    "patient_id": patient_id,
                    "name": patient[1],
                    "visit_count": count
                })
        elif count <= 10:
            frequency_groups["frequent"] += 1
            # 添加到高频患者列表
            patient = db.session.query(
                Appointment.patient_id,
                User.real_name
            ).join(
                User, User.patient_id == Appointment.patient_id
            ).filter(
                Appointment.patient_id == patient_id
            ).first()
            
            if patient:
                frequent_patients.append({
                    "patient_id": patient_id,
                    "name": patient[1],
                    "visit_count": count
                })
        else:
            frequency_groups["very_frequent"] += 1
            # 添加到高频患者列表
            patient = db.session.query(
                Appointment.patient_id,
                User.real_name
            ).join(
                User, User.patient_id == Appointment.patient_id
            ).filter(
                Appointment.patient_id == patient_id
            ).first()
            
            if patient:
                frequent_patients.append({
                    "patient_id": patient_id,
                    "name": patient[1],
                    "visit_count": count
                })

    # 计算平均就诊次数
    total_patients = len(patient_counts)
    total_visits = sum(count for _, count in patient_counts)
    avg_visits = round(total_visits / total_patients, 2) if total_patients > 0 else 0

    # 排序高频患者数据
    frequent_patients.sort(key=lambda x: x["visit_count"], reverse=True)
    # 只保留前10名
    frequent_patients = frequent_patients[:10]

    return jsonify({
        "status": "success",
        "data": {
            "frequency_groups": frequency_groups,
            "total_patients": total_patients,
            "total_visits": total_visits,
            "avg_visits": avg_visits,
            "frequent_patients": frequent_patients,
            "time_range": {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "days": days
            }
        }
    })

@analytics_bp.route('/api/analytics/monthly-trend')
@login_required
@admin_required
def get_monthly_trend():
    """获取月度预约趋势数据"""
    # 获取时间范围参数，默认过去12个月
    months = request.args.get('months', 12, type=int)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=months*30)  # 近似值
    
    # 构建月份范围
    current_month = end_date.replace(day=1)
    month_ranges = []
    
    for i in range(months):
        month = current_month.month
        year = current_month.year
        last_day = calendar.monthrange(year, month)[1]
        month_end = current_month.replace(day=last_day)
        month_ranges.append((current_month, month_end, f"{year}-{month:02d}"))
        
        # 上个月
        if month == 1:
            current_month = current_month.replace(year=year-1, month=12, day=1)
        else:
            current_month = current_month.replace(month=month-1, day=1)
    
    # 反转，使最早的月份在前
    month_ranges.reverse()
    
    # 查询每个月的预约数量
    monthly_data = []
    
    for month_start, month_end, month_label in month_ranges:
        # 当月总预约数
        total_count = Appointment.query.filter(
            Appointment.appointment_date.between(month_start, month_end)
        ).count()
        
        # 当月已完成预约数
        completed_count = Appointment.query.filter(
            Appointment.appointment_date.between(month_start, month_end),
            Appointment.status == AppointmentStatus.COMPLETED
        ).count()
        
        # 当月取消预约数
        cancelled_count = Appointment.query.filter(
            Appointment.appointment_date.between(month_start, month_end),
            Appointment.status == AppointmentStatus.CANCELLED
        ).count()
        
        monthly_data.append({
            "month": month_label,
            "total": total_count,
            "completed": completed_count,
            "cancelled": cancelled_count
        })
    
    # 提取月份标签和数据系列
    labels = [item["month"] for item in monthly_data]
    total_series = [item["total"] for item in monthly_data]
    completed_series = [item["completed"] for item in monthly_data]
    cancelled_series = [item["cancelled"] for item in monthly_data]
    
    return jsonify({
        "status": "success",
        "data": {
            "labels": labels,
            "series": {
                "total": total_series,
                "completed": completed_series,
                "cancelled": cancelled_series
            },
            "monthly_data": monthly_data,
            "time_range": {
                "months": months
            }
        }
    })

def init_analytics_routes(app):
    """初始化数据分析路由"""
    app.register_blueprint(analytics_bp, url_prefix='/analytics') 