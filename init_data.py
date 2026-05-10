#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta, date
from random import choice, randint, uniform, sample, shuffle
from collections import defaultdict
import os
import sys
import argparse

from db_model import db, User, Patient, DoctorPatientRelation, ImagingReport, ChatSession, ChatMessage
from db_model import MedicalHistory, Appointment, PhysicalExam, BrainCTScan, CTFollowUp
from db_model import NeurologicalAssessment, MedicationRecord, MentalHealth, SystemLog, SystemConfig, Notification
from db_config import get_sqlalchemy_uri

# 创建Flask应用上下文以使用数据库
from flask import Flask


# 解析命令行参数
def parse_args():
    parser = argparse.ArgumentParser(description='初始化医疗系统测试数据')
    parser.add_argument('-y', '--yes', action='store_true', help='自动确认所有操作，不提示')
    return parser.parse_args()


args = parse_args()

# 交互式选择数据库连接
print("\n===== 系统测试数据初始化工具 =====")
print("请选择要连接的数据库:")
print("1. 本地数据库 (localhost:3306)")
print("2. 远程Sealos数据库 (dbconn.sealosbja.site:37152)")

while True:
    db_choice = input("请输入选项 (1/2): ").strip()
    if db_choice in ['1', '2']:
        break
    print("无效选项，请重新输入")

# 创建Flask应用
app = Flask(__name__)

# 根据选择设置数据库连接
if db_choice == '2':
    print("使用远程Sealos数据库...")
    app.config['SQLALCHEMY_DATABASE_URI'] = get_sqlalchemy_uri('remote')
else:
    print("使用本地数据库...")
    app.config['SQLALCHEMY_DATABASE_URI'] = get_sqlalchemy_uri('local')

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 示例数据
doctor_usernames = [f"doctor{i}" for i in range(1, 6)]
patient_usernames = [f"patient{i}" for i in range(1, 11)]

# 科室列表
departments = ["neurology", "radiology", "cardiology", "orthopedics", "internal", "neurosurgery",
               "neurology_internal"]  # 使用英文枚举值

# 药物列表
medications = [
    "阿司匹林", "硝苯地平", "单硝酸异山梨酯", "氯沙坦钾", "美托洛尔",
    "辛伐他汀", "阿托伐他汀", "瑞舒伐他汀", "氯氮平", "利培酮",
    "卡马西平", "丙戊酸钠", "拉莫三嗪", "左乙拉西坦", "托吡酯",
    "多奈哌齐", "美金刚", "利凡诺尔", "加兰他敏", "阿可拉定",
    "奥氮平", "氟西汀", "帕罗西汀", "文拉法辛", "舍曲林",
    "甲磺酸倍他司汀", "盐酸氟桂利嗪", "尼莫地平", "依达拉奉", "甘露醇"
]


def create_admin():
    """创建管理员账号"""
    print("创建管理员账号...")

    admin = User(
        username="admin",
        real_name="系统管理员",
        id_card="000000000000000000",
        email="admin@example.com",
        phone="13900000000",
        registration_date=datetime.now() - timedelta(days=500),
        last_login=datetime.now() - timedelta(hours=2),
        is_active=True,
        role='admin'
    )
    admin.set_password("123456")
    db.session.add(admin)

    db.session.commit()
    print("管理员账号创建完成")


def create_test_data():
    """创建测试数据"""
    print("\n开始创建测试数据...")
    
    # 创建管理员账号
    create_admin()
    
    # 创建测试用户
    create_users()
    
    # 创建患者信息
    create_patients()
    
    # 创建医患关系
    create_doctor_patient_relations()
    
    # 创建医疗历史记录
    create_medical_histories()
    
    # 创建体检记录
    create_physical_exams()
    
    # 创建预约记录
    create_appointments()
    
    # 创建影像报告
    create_imaging_reports()
    
    # 创建脑部CT扫描记录
    create_brain_ct_scans()
    
    # 创建CT随访记录
    create_ct_follow_ups()
    
    # 创建神经系统评估记录
    create_neurological_assessments()
    
    # 创建药物治疗记录
    create_medication_records()
    
    # 创建心理健康评估记录
    create_mental_health_records()
    
    # 创建聊天会话和消息
    create_chat_sessions_and_messages()
    
    # 创建系统日志
    create_system_logs()
    
    # 创建系统配置
    create_system_config()
    
    # 创建通知数据
    create_notifications()
    
    print("\n所有测试数据创建完成！")


def clear_all_tables():
    """清空所有表数据"""
    print("清空数据库表...")

    # 禁用外键约束检查
    print("\n开始创建测试数据...")
    
    # 先删除所有表并重新创建
    print("\n删除所有表并重新创建...")
    db.drop_all()
    db.create_all()
    print("表结构重建完成")
    
    # 创建管理员账号
    create_admin()
    
    # 创建测试用户
    create_users()
    
    # 创建患者信息
    create_patients()
    
    # 创建医患关系
    create_doctor_patient_relations()
    
    # 创建医疗历史记录
    create_medical_histories()
    
    # 创建体检记录
    create_physical_exams()
    
    # 创建预约记录
    create_appointments()
    
    # 创建影像报告
    create_imaging_reports()
    
    # 创建脑部CT扫描记录
    create_brain_ct_scans()
    
    # 创建CT随访记录
    create_ct_follow_ups()
    
    # 创建神经系统评估记录
    create_neurological_assessments()
    
    # 创建药物治疗记录
    create_medication_records()
    
    # 创建心理健康评估记录
    create_mental_health_records()
    
    # 创建聊天会话和消息
    create_chat_sessions_and_messages()
    
    # 创建系统日志
    create_system_logs()
    
    # 创建系统配置
    create_system_config()
    
    # 创建通知数据
    create_notifications()
    
    print("\n所有测试数据创建完成！")


def clear_all_tables():
    """清空所有表数据"""
    print("清空数据库表...")

    # 禁用外键约束检查
    db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 0;"))
    db.session.commit()

    try:
        # 按顺序删除所有表数据
        Notification.query.delete()
        ChatMessage.query.delete()
        ChatSession.query.delete()
        SystemLog.query.delete()
        CTFollowUp.query.delete()
        BrainCTScan.query.delete()
        NeurologicalAssessment.query.delete()
        MedicationRecord.query.delete()
        MentalHealth.query.delete()
        PhysicalExam.query.delete()
        ImagingReport.query.delete()
        Appointment.query.delete()
        MedicalHistory.query.delete()
        DoctorPatientRelation.query.delete()

        # 需要处理User和Patient之间的循环依赖
        # 先解除关联
        for user in User.query.all():
            user.patient_id = None
        db.session.commit()

        Patient.query.delete()
        User.query.delete()
        SystemConfig.query.delete()

        db.session.commit()
        print("数据库表已清空")
    finally:
        # 重新启用外键约束检查
        db.session.execute(db.text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.session.commit()


def create_users():
    """创建医生用户"""
    print("创建医生用户...")
    doctor_names = ["张伟", "王芳", "李强", "刘洋", "陈磊", "杨静", "赵磊", "黄敏", "周杰", "吴婷"]
    for i in range(10):
        doctor = User(
            username=f"doctor{i + 1}",
            real_name=doctor_names[i],
            id_card=f"1{'%016d' % (i + 1)}",
            email=f"doctor{i + 1}@hospital.com",
            phone=f"138{randint(10000000, 99999999)}",
            registration_date=datetime.now() - timedelta(days=randint(100, 500)),
            last_login=datetime.now() - timedelta(hours=randint(1, 48)),
            is_active=True,
            role='doctor'
        )
        doctor.set_password("123456")
        db.session.add(doctor)
    db.session.commit()
    print("已创建10名医生用户")
    # 医生用户创建完成


def create_patients():
    """创建50名患者及其用户账号"""
    print("创建患者数据...")
    genders = ['男', '女']
    blood_types = ['A', 'B', 'AB', 'O']
    status_options = ['新患者', '待就诊', '就诊中', '随访中', '治疗完成']
    address_prefix = "北京市朝阳区健康路"
    patient_names = [
        "王小明", "李红", "张三", "刘四", "赵五", "钱六", "孙七", "周八", "吴九", "郑十",
        "冯十一", "陈十二", "褚十三", "卫十四", "蒋十五", "沈十六", "韩十七", "杨十八", "朱十九", "秦二十",
        "尤二一", "许二二", "何二三", "吕二四", "施二五", "张二六", "孔二七", "曹二八", "严二九", "华三十",
        "金三一", "魏三二", "陶三三", "姜三四", "戚三五", "谢三六", "邹三七", "喻三八", "柏三九", "水四十",
        "窦四一", "章四二", "云四三", "苏四四", "潘四五", "葛四六", "奚四七", "范四八", "彭四九", "郎五十"
    ]
    for i in range(50):
        patient = Patient(
            name=patient_names[i],
            age=randint(18, 85),
            gender=choice(genders),
            address=f"{address_prefix}{randint(1, 200)}号",
            contact_info=f"139{randint(10000000, 99999999)}",
            blood_type=choice(blood_types),
            emergency_contact=f"{choice(['张', '王', '李', '赵', '刘', '陈'])}先生: 135{randint(10000000, 99999999)}",
            status=choice(status_options),
            doctor_advice=choice([None, "建议定期复查", "注意饮食", "加强锻炼"]),
            doctor_id=None
        )
        db.session.add(patient)
        db.session.flush()
        patient_user = User(
            username=f"patient{i + 1}",
            real_name=patient_names[i],
            id_card=f"2{'%016d' % (i + 1)}",
            email=f"patient{i + 1}@mail.com",
            phone=f"139{randint(10000000, 99999999)}",
            registration_date=datetime.now() - timedelta(days=randint(1, 100)),
            last_login=datetime.now() - timedelta(hours=randint(1, 24)),
            is_active=True,
            role='patient',
            patient_id=patient.patient_id
        )
        patient_user.set_password("123456")
        db.session.add(patient_user)
    db.session.commit()
    print("已创建50名患者及其用户账号")


def create_doctor_patient_relations():
    """均匀分配医患关系"""
    print("创建医患关系...")
    doctors = User.query.filter_by(role='doctor').all()
    patients = Patient.query.all()
    all_relations = []
    for patient in patients:
        doctor_count = randint(1, 3)
        shuffled_doctors = doctors[:]
        shuffle(shuffled_doctors)
        selected_doctors = shuffled_doctors[:doctor_count]
        for doctor in selected_doctors:
            all_relations.append((doctor, patient))
    doctor_patient_map = defaultdict(list)
    for doctor, patient in all_relations:
        doctor_patient_map[doctor.user_id].append(patient)
    for doctor in doctors:
        plist = doctor_patient_map[doctor.user_id]
        if len(plist) < 5:
            candidates = [p for p in patients if p not in plist]
            for p in sample(candidates, 5 - len(plist)):
                all_relations.append((doctor, p))
        elif len(plist) > 20:
            to_remove = sample(plist, len(plist) - 20)
            all_relations = [(d, p) for d, p in all_relations if not (d.user_id == doctor.user_id and p in to_remove)]
    seen = set()
    for doctor, patient in all_relations:
        key = (doctor.user_id, patient.patient_id)
        if key in seen:
            continue
        seen.add(key)
        relation = DoctorPatientRelation(
            doctor_id=doctor.user_id,
            patient_id=patient.patient_id,
            start_date=datetime.now() - timedelta(days=randint(1, 90)),
            is_active=True,
            relation_type=choice(['主治', '会诊', '转诊']),
            patient_group=choice(['常规患者', '重点随访', 'VIP']),
            last_visit_date=datetime.now() - timedelta(days=randint(0, 30)),
            next_visit_date=datetime.now() + timedelta(days=randint(1, 60)),
            notes=choice([None, "需定期复诊", "注意血压", "心理疏导"])
        )
        db.session.add(relation)
    db.session.commit()
    print("医患关系创建完成")


def create_medical_histories():
    """创建患者医疗历史记录"""
    print("创建医疗历史记录...")

    allergies = [None, "青霉素过敏", "对花粉过敏", "对海鲜过敏", "乳糖不耐受", "对某些药物过敏", "对尘螨过敏",
                 "对花生过敏"]
    family_histories = [
        None,
        "家族中有高血压病史",
        "父亲有冠心病",
        "母亲患有2型糖尿病",
        "有家族心脏病史",
        "家族中有阿尔茨海默病患者",
        "家族中有多人患有癌症",
        "祖父母有脑卒中史",
        "家族中有自身免疫性疾病"
    ]
    head_injuries = [
        None,
        "10年前曾发生车祸导致轻微脑震荡",
        "儿童时期曾摔伤头部",
        "无头部创伤史",
        "5年前工作时意外跌倒导致头部受伤",
        "运动中曾多次轻微头部撞击",
        "3年前摔倒后头部碰撞，未做详细检查"
    ]
    neurological_conditions = [
        None,
        "偏头痛",
        "无神经系统疾病",
        "轻度癫痫",
        "有短暂性脑缺血发作史",
        "诊断有早期帕金森病",
        "面神经麻痹史",
        "周围神经炎",
        "多发性硬化症初期表现",
        "三叉神经痛"
    ]

    # 获取所有患者
    patients = Patient.query.all()

    # 为每个患者创建医疗历史
    for patient in patients:
        history = MedicalHistory(
            patient_id=patient.patient_id,
            allergy_info=choice(allergies),
            family_history=choice(family_histories),
            previous_head_injuries=choice(head_injuries),
            neurological_conditions=choice(neurological_conditions)
        )
        db.session.add(history)

    db.session.commit()
    print("医疗历史记录创建完成")


def create_physical_exams():
    """创建患者体检记录"""
    print("创建体检记录...")

    # 获取所有患者
    patients = Patient.query.all()

    # 为每个患者创建1-3条体检记录
    for patient in patients:
        exam_count = randint(1, 3)

        for i in range(exam_count):
            # 根据患者年龄和性别生成相对合理的体检值
            age = patient.age
            is_male = patient.gender == '男'

            # 基础心率（年龄越大基础值越低）
            base_heart_rate = 80 - (age // 10)
            heart_rate = randint(base_heart_rate - 5, base_heart_rate + 15)

            # 呼吸频率
            respiratory_rate = randint(14, 20)

            # 血压（年龄越大越容易偏高）
            base_systolic = 110 + (age // 5)
            systolic = randint(base_systolic - 10, base_systolic + 20)
            diastolic = randint(65, 85)

            # 体温
            temperature = round(uniform(36.3, 37.2), 1)

            # 体重（男性基础值偏高）
            base_weight = 60 + (10 if is_male else 0)
            weight = round(uniform(base_weight - 10, base_weight + 20), 1)

            # 身高（男性基础值偏高）
            base_height = 160 + (10 if is_male else 0)
            height = round(uniform(base_height - 10, base_height + 15), 1)

            # 创建体检记录
            exam_date = datetime.now() - timedelta(days=i * 30 + randint(0, 10))

            exam = PhysicalExam(
                patient_id=patient.patient_id,
                heart_rate=heart_rate,
                respiratory_rate=respiratory_rate,
                blood_pressure_systolic=systolic,
                blood_pressure_diastolic=diastolic,
                temperature=temperature,
                weight=weight,
                height=height,
                exam_date=exam_date
            )
            db.session.add(exam)

    db.session.commit()
    print("体检记录创建完成")


def create_appointments():
    """创建预约记录"""
    print("创建预约记录...")

    appointment_types = ["regular", "followup", "specialist", "emergency", "special"]  # 使用英文枚举值
    time_slots = ["morning", "afternoon"]  # 使用英文枚举值

    # 根据业务场景选择合理的状态
    past_statuses = ["completed", "cancelled", "rejected", "missed"]  # 使用英文枚举值
    future_statuses = ["pending", "confirmed"]  # 使用英文枚举值

    cancel_reasons = [
        "患者临时有事",
        "医生调休",
        "患者身体不适无法前来",
        "医院设备维护",
        "医生有紧急手术"
    ]
    symptoms = [
        "头痛、头晕，持续一周",
        "间歇性胸闷、气短",
        "颈部僵硬，活动受限",
        "夜间多汗，睡眠质量差",
        "视力模糊，阅读困难",
        "记忆力下降，思维迟缓",
        "右侧肢体麻木",
        "言语不清，表达困难",
        "平衡能力下降，行走不稳",
        "情绪起伏大，焦虑明显",
        "血压波动较大",
        "突发性耳鸣",
        "经常性腰背痛",
        "关节疼痛，尤其在阴雨天",
        "反复发热，原因不明"
    ]

    # 获取所有医生和患者
    doctors = User.query.filter_by(role='doctor').all()
    patients = Patient.query.all()

    today = date.today()

    # 为每个患者创建5-8条预约记录，增加数量以显示更好的图表数据
    for patient in patients:
        # 历史预约数量(过去的预约)
        past_appointment_count = randint(4, 6)

        # 未来预约数量(未来的预约)
        future_appointment_count = randint(1, 2)

        # 创建历史预约记录(已完成/已取消的预约)
        for i in range(past_appointment_count):
            # 选择医生
            doctor = choice(doctors)

            # 过去的预约日期，确保在过去30天内有更多的记录，以便图表能够显示趋势
            # 70%的预约在过去30天内，30%在更早时间
            if randint(1, 10) <= 7:
                days_ago = randint(1, 30)  # 过去30天内
            else:
                days_ago = randint(31, 180)  # 更早的时间

            appt_date = today - timedelta(days=days_ago)

            # 确保大部分历史预约状态是"已完成"，以便有足够数据显示图表
            if randint(1, 10) <= 8:  # 80%的几率
                status = "completed"
            else:
                status = choice(["cancelled", "rejected", "missed"])

            # 预约创建时间（总是在预约日期前5-30天）
            created_days_before = min(days_ago, randint(5, 30))
            created_at = datetime.combine(
                appt_date - timedelta(days=created_days_before),
                datetime.min.time()
            ) + timedelta(hours=randint(8, 17), minutes=randint(0, 59))

            # 对状态相关的字段进行处理
            checked_in_at = None
            completed_at = None
            follow_up_required = False
            follow_up_date = None
            follow_up_notes = None
            cancelled_at = None
            cancelled_by = None
            cancel_reason = None
            notes = None

            if status == "completed":
                # 签到时间是预约当天的上午或下午
                time_slot = choice(time_slots)
                if time_slot == "morning":
                    hour = randint(8, 11)
                else:
                    hour = randint(13, 16)

                checked_in_at = datetime.combine(appt_date, datetime.min.time()) + timedelta(hours=hour,
                                                                                             minutes=randint(0, 59))
                # 完成时间是签到后20-90分钟
                completed_at = checked_in_at + timedelta(minutes=randint(20, 90))

                # 部分病例需要随访
                follow_up_required = randint(0, 1) == 1
                if follow_up_required:
                    follow_up_date = appt_date + timedelta(days=randint(10, 90))
                    follow_up_notes = f"请在{follow_up_date.strftime('%Y-%m-%d')}进行复查。"

                notes = "检查顺利完成，患者状况稳定。" if randint(0, 1) else None

            elif status in ["cancelled", "rejected"]:
                # 取消时间通常在预约日期前1-3天，但必须在创建时间之后
                cancel_days_before = min(days_ago - 1, randint(1, 3))
                cancelled_at = datetime.combine(
                    appt_date - timedelta(days=cancel_days_before),
                    datetime.min.time()
                ) + timedelta(hours=randint(8, 17), minutes=randint(0, 59))

                # 确保取消时间在创建时间之后
                if cancelled_at < created_at:
                    cancelled_at = created_at + timedelta(hours=randint(1, 48))

                cancelled_by = choice(["patient", "doctor", "admin"])
                cancel_reason = choice(cancel_reasons)

            # 创建预约编号 - 格式：APPT+年月日+4位随机数
            code = f"APPT{appt_date.strftime('%Y%m%d')}{randint(1000, 9999)}"

            # 确保预约类型分布更加均匀，以便图表能够显示所有类型
            # 使用患者ID和迭代索引来均匀分布预约类型
            appt_type_index = (patient.patient_id + i) % len(appointment_types)

            # 创建历史预约记录
            appointment = Appointment(
                patient_id=patient.patient_id,
                doctor_id=doctor.user_id,
                appointment_type=appointment_types[appt_type_index],
                department=choice(departments),
                appointment_date=appt_date,
                time_slot=time_slot if 'time_slot' in locals() else choice(time_slots),
                symptoms=choice(symptoms),
                status=status,
                created_at=created_at,
                checked_in_at=checked_in_at,
                completed_at=completed_at,
                follow_up_required=follow_up_required,
                follow_up_date=follow_up_date,
                follow_up_notes=follow_up_notes,
                cancelled_at=cancelled_at,
                cancelled_by=cancelled_by,
                cancel_reason=cancel_reason,
                notes=notes,
                code=code
            )
            db.session.add(appointment)

        # 创建未来预约记录(待确认/已确认的预约)
        for i in range(future_appointment_count):
            # 选择医生
            doctor = choice(doctors)

            # 未来的预约日期，1-30天后
            days_later = randint(1, 30)
            appt_date = today + timedelta(days=days_later)

            # 未来的预约状态只能是待确认或已确认
            status = choice(future_statuses)

            # 创建时间是现在到过去30天内的随机时间，但必须早于预约日期
            days_created_ago = randint(1, min(30, days_later))
            created_at = datetime.combine(
                today - timedelta(days=days_created_ago),
                datetime.min.time()
            ) + timedelta(hours=randint(8, 17), minutes=randint(0, 59))

            # 对于已确认状态，设置确认时间
            # 这里不设置其他状态相关字段，因为预约还未发生
            notes = None
            if status == "confirmed":
                notes = "请按时到院就诊，提前准备好相关资料。" if randint(0, 1) else None

            # 创建预约编号 - 格式：APPT+年月日+4位随机数
            code = f"APPT{appt_date.strftime('%Y%m%d')}{randint(1000, 9999)}"

            # 创建未来预约记录
            appointment = Appointment(
                patient_id=patient.patient_id,
                doctor_id=doctor.user_id,
                appointment_type=appointment_types[(patient.patient_id + i) % len(appointment_types)],
                department=choice(departments),
                appointment_date=appt_date,
                time_slot=choice(time_slots),
                symptoms=choice(symptoms),
                status=status,
                created_at=created_at,
                notes=notes,
                code=code
            )
            db.session.add(appointment)

    db.session.commit()
    print("预约记录创建完成")


def create_imaging_reports():
    """创建影像报告"""
    print("创建影像报告...")

    report_types = ["脑部MRI", "脑部CT", "颈椎X射线", "胸部CT", "脊髓MRI", "腹部B超", "骨密度检测", "血管造影"]

    # 分析结果模板
    analysis_templates = [
        "扫描显示{part}结构正常，未见明显异常信号。脑室系统大小及形态正常，脑沟及脑池未见异常扩大。",
        "{part}区域可见异常信号，大小约为{size}mm，边界{boundary}，T1加权像呈{t1}信号，T2加权像呈{t2}信号。",
        "{part}可见多发斑点状异常信号，分布于{distribution}。脑白质区域可见轻度{white_matter}改变。",
        "影像学检查显示{part}区域有{density}密度/信号影，考虑为{consideration}可能。",
        "{part}未见明确病变，脑实质内未见异常信号。脑沟回分布正常，灰白质分界清晰。",
        "检查显示{part}区域密度{density}，边界{boundary}，大小约{size}mm，形态不规则，周围组织无明显压迫改变。",
        "{part}区域未见明确病变，邻近结构平扫未见明显异常。建议结合临床综合评估。",
        "扫描发现{part}区域有{size}mm的{density}影，边界{boundary}，考虑{consideration}可能，建议临床随访或增强扫描进一步确定。"
    ]

    # 结论模板
    conclusion_templates = [
        "未见明显异常，建议定期复查。",
        "考虑为{diagnosis}，建议结合临床进一步检查及随访。",
        "{part}区域异常，符合{diagnosis}表现，建议临床治疗。",
        "扫描结果提示可能存在{diagnosis}，需进一步检查以明确诊断。",
        "影像学表现不典型，建议结合临床及实验室检查综合分析。",
        "影像学检查显示{part}区域有{diagnosis}表现，建议{timeline}后复查。",
        "本次扫描与既往检查相比，病灶{change}，考虑{diagnosis_state}。",
        "检查结果显示脑白质区多发异常信号，考虑{diagnosis}可能性大。"
    ]

    # 健康建议模板
    advice_templates = [
        "建议保持规律作息，避免过度疲劳。定期体检，{timeline}后复查。",
        "需控制{risk_factor}等危险因素，建议低盐低脂饮食，规律运动。",
        "建议遵医嘱服药，保持良好生活习惯，避免剧烈运动。",
        "建议定期复查，密切观察症状变化，如有不适及时就医。",
        "目前无需特殊处理，建议{timeline}复查，如症状加重请及时就医。",
        "针对当前情况，建议{treatment}，并{timeline}后进行复查评估。",
        "建议完善{exam}检查，明确诊断后再制定进一步治疗方案。",
        "考虑到患者症状，建议结合{treatment}同时密切随访观察。"
    ]

    # 填充模板的值
    parts = ["额叶", "颞叶", "顶叶", "枕叶", "基底节", "小脑", "脑干", "丘脑", "海马", "胼胝体", "侧脑室", "第三脑室"]
    sizes = ["5", "8", "10", "12", "15", "20", "3", "7", "25", "18"]
    boundaries = ["清晰", "模糊", "不规则", "毛糙", "光整", "部分清晰部分模糊", "密度不均"]
    signals = ["低", "等", "高", "混杂", "稍高", "稍低", "显著高", "明显低"]
    distributions = ["皮层下", "脑室周围", "深部白质", "基底节区", "皮质区", "半卵圆中心", "小脑半球", "脑桥"]
    white_matter_changes = ["脱髓鞘", "缺血", "水肿", "变性", "软化", "钙化", "萎缩"]
    densities = ["低", "高", "混杂", "等", "稍低", "稍高", "明显增高", "显著减低", "不均匀"]
    considerations = ["缺血性病变", "脱髓鞘病变", "肿瘤", "血管畸形", "炎症", "感染", "外伤后改变", "退行性变",
                      "代谢性疾病"]
    diagnoses = ["缺血性改变", "小血管病", "脱髓鞘病变", "早期退行性改变", "良性肿瘤", "动脉瘤", "脑萎缩",
                 "多发性腔隙性脑梗死", "颅内占位性病变"]
    changes = ["较前缩小", "较前增大", "无明显变化", "密度增高", "信号减低", "范围扩大", "数量增多", "已基本消失"]
    diagnosis_states = ["疾病进展", "治疗有效", "基本稳定", "部分好转", "情况恶化", "需要手术干预", "可继续保守治疗"]
    risk_factors = ["高血压", "高血脂", "高血糖", "吸烟", "饮酒", "肥胖", "缺乏运动", "压力过大"]
    timelines = ["三个月", "六个月", "一年", "两年", "一个月", "两周", "定期"]
    treatments = ["药物治疗", "手术干预", "物理治疗", "心理疏导", "康复训练", "生活方式调整", "减轻体重", "控制血压"]
    exams = ["脑电图", "脑脊液检查", "神经心理测试", "基因检测", "血管造影", "功能性MRI", "PET-CT", "血液生化"]

    # 获取所有患者
    patients = Patient.query.all()

    # 为80%的患者创建影像报告，增加数量
    for patient in patients:
        # 80%的患者有影像报告
        if randint(1, 10) <= 8:
            report_count = randint(1, 4)  # 1-4份报告

            for _ in range(report_count):
                report_type = choice(report_types)
                report_date = date.today() - timedelta(days=randint(1, 180))

                # 生成分析结果
                analysis_template = choice(analysis_templates)
                analysis_result = analysis_template.format(
                    part=choice(parts),
                    size=choice(sizes),
                    boundary=choice(boundaries),
                    t1=choice(signals),
                    t2=choice(signals),
                    distribution=choice(distributions),
                    white_matter=choice(white_matter_changes),
                    density=choice(densities),
                    consideration=choice(considerations)
                )

                # 生成结论
                conclusion_template = choice(conclusion_templates)
                if "{diagnosis}" in conclusion_template and "{part}" in conclusion_template:
                    conclusion = conclusion_template.format(
                        diagnosis=choice(diagnoses),
                        part=choice(parts),
                        timeline=choice(timelines),
                        change=choice(changes),
                        diagnosis_state=choice(diagnosis_states)
                    )
                elif "{diagnosis}" in conclusion_template:
                    conclusion = conclusion_template.format(
                        diagnosis=choice(diagnoses),
                        timeline=choice(timelines),
                        change=choice(changes),
                        diagnosis_state=choice(diagnosis_states)
                    )
                elif "{part}" in conclusion_template:
                    conclusion = conclusion_template.format(
                        part=choice(parts),
                        timeline=choice(timelines)
                    )
                else:
                    conclusion = conclusion_template

                # 生成健康建议
                advice_template = choice(advice_templates)
                if "{timeline}" in advice_template and "{risk_factor}" in advice_template:
                    health_advice = advice_template.format(
                        timeline=choice(timelines),
                        risk_factor=choice(risk_factors),
                        treatment=choice(treatments),
                        exam=choice(exams)
                    )
                elif "{timeline}" in advice_template:
                    health_advice = advice_template.format(
                        timeline=choice(timelines),
                        treatment=choice(treatments),
                        exam=choice(exams)
                    )
                elif "{risk_factor}" in advice_template:
                    health_advice = advice_template.format(
                        risk_factor=choice(risk_factors),
                        treatment=choice(treatments),
                        exam=choice(exams)
                    )
                elif "{treatment}" in advice_template:
                    health_advice = advice_template.format(
                        treatment=choice(treatments),
                        timeline=choice(timelines),
                        exam=choice(exams)
                    )
                elif "{exam}" in advice_template:
                    health_advice = advice_template.format(
                        exam=choice(exams),
                        treatment=choice(treatments)
                    )
                else:
                    health_advice = advice_template

                # 设置图像URL（模拟）
                image_url = f"/static/images/scans/{report_type.lower().replace(' ', '_')}_{randint(1, 8)}.jpg"

                report = ImagingReport(
                    patient_id=patient.patient_id,
                    report_type=report_type,
                    report_date=report_date,
                    analysis_result=analysis_result,
                    conclusion=conclusion,
                    health_advice=health_advice,
                    source_image_url=image_url,
                    created_at=datetime.combine(report_date, datetime.min.time()) + timedelta(hours=randint(1, 8))
                )
                db.session.add(report)

    db.session.commit()
    print("影像报告创建完成")


def create_brain_ct_scans():
    """创建脑部CT扫描记录"""
    print("创建脑部CT扫描记录...")

    scan_types = ['平扫', '增强', '全脑灌注']
    technicians = ["王技师", "李技师", "张技师", "刘技师"]
    radiologists = ["赵医师", "钱医师", "孙医师", "周医师", "吴医师"]

    scan_reasons = [
        "头痛",
        "头晕",
        "意识障碍",
        "跌倒后头部外伤",
        "视物不清",
        "认知功能下降",
        "神经系统检查异常",
        "癫痫发作后评估",
        "日常体检"
    ]

    brain_structures = [
        "脑结构整体对称，各脑叶形态正常",
        "脑沟回分布正常，脑实质密度无明显异常",
        "脑沟回分布符合年龄特点，脑实质形态基本正常",
        "基底节区结构清晰，丘脑形态和密度正常"
    ]

    ventricle_statuses = [
        "脑室系统形态位置正常，大小适中",
        "侧脑室轻度扩大，第三、四脑室未见异常",
        "脑室系统无扩大或移位",
        "侧脑室前角稍大，其余脑室系统未见异常"
    ]

    skull_conditions = [
        "颅骨完整，无骨折线",
        "颅骨密度均匀，骨质无破坏",
        "颅骨结构正常，蝶窦气化良好",
        "颅骨形态正常，缝隙清晰"
    ]

    lesion_descriptions = [
        "未见明确占位性病变",
        "右侧颞叶见类圆形低密度影，边界清楚，大小约10mm×12mm",
        "左侧顶叶皮层下可见片状低密度区，无明显占位效应",
        "双侧基底节区见多发点状低密度影",
        "额叶白质区可见密度不均影，边界不清"
    ]

    hemorrhage_statuses = [
        "未见明确出血灶",
        "右侧基底节区可见高密度影，考虑少量出血",
        "脑室系统无出血征象",
        "颅内未见异常高密度影，无蛛网膜下腔出血证据"
    ]

    ischemia_statuses = [
        "未见明确缺血性病变",
        "左侧大脑半球可见低密度区，考虑缺血性改变",
        "基底节区见陈旧性腔隙性脑梗死",
        "右侧颞叶皮层下可见片状低密度影，考虑近期缺血"
    ]

    atrophy_statuses = [
        "无明显脑萎缩表现",
        "轻度脑萎缩，符合年龄改变",
        "双侧颞叶萎缩较为明显",
        "脑沟回增宽，脑室系统代偿性扩大，考虑脑萎缩"
    ]

    density_abnormalities = [
        "脑实质密度基本正常",
        "双侧侧脑室旁白质区可见密度减低",
        "右侧基底节区见斑片状低密度",
        "左侧枕叶皮层下密度不均"
    ]

    conclusions = [
        "未见明显异常",
        "考虑缺血性改变",
        "多发腔隙性脑梗死",
        "轻度脑萎缩，符合年龄相关改变",
        "大脑白质疏松症",
        "右侧额叶异常密度，建议结合临床进一步检查"
    ]

    # 获取所有患者
    patients = Patient.query.all()

    # 为50%的患者创建脑部CT扫描记录
    for patient in patients:
        if randint(0, 1) == 1:  # 50%几率
            scan_count = randint(1, 2)  # 1-2份CT记录

            for i in range(scan_count):
                # 扫描日期（过去的记录）
                scan_date = datetime.now() - timedelta(days=randint(10, 180))

                # 是否需要随访
                follow_up_recommended = randint(0, 10) < 3  # 30%几率需要随访

                scan = BrainCTScan(
                    patient_id=patient.patient_id,
                    scan_date=scan_date,
                    scan_type=choice(scan_types),
                    technician=choice(technicians),
                    radiologist=choice(radiologists),
                    scan_reason=choice(scan_reasons),
                    brain_structure=choice(brain_structures),
                    ventricle_status=choice(ventricle_statuses),
                    skull_condition=choice(skull_conditions),
                    lesion_description=choice(lesion_descriptions),
                    hemorrhage_status=choice(hemorrhage_statuses),
                    ischemia_status=choice(ischemia_statuses),
                    atrophy_status=choice(atrophy_statuses),
                    density_abnormalities=choice(density_abnormalities),
                    image_path=f"/static/images/ct_scans/patient_{patient.patient_id}_scan_{i + 1}.jpg",
                    conclusion=choice(conclusions),
                    follow_up_recommended=follow_up_recommended
                )
                db.session.add(scan)

    db.session.commit()
    print("脑部CT扫描记录创建完成")


def create_ct_follow_ups():
    """创建CT随访记录"""
    print("创建CT随访记录...")

    comparison_results = [
        "与原始扫描相比，病变无明显变化",
        "比较原始扫描，病变范围有所缩小",
        "较前次检查，出血灶已大部分吸收",
        "与原始CT比较，低密度区范围扩大约5mm",
        "较首次检查，脑萎缩程度有所加重"
    ]

    disease_progressions = [
        "疾病稳定，无明显进展",
        "病情有所改善，炎症反应减轻",
        "与初次检查相比，缺血区域部分恢复",
        "病变较前次扩大，考虑疾病进展",
        "病变范围稳定，但密度有所变化"
    ]

    treatment_responses = [
        "治疗反应良好，病变明显缩小",
        "治疗效果一般，病变仅小幅度改善",
        "对当前治疗反应不明显，建议调整方案",
        "治疗后水肿减轻，但原发病灶变化不大",
        "治疗反应符合预期，继续现有治疗方案"
    ]

    # 获取所有需要随访的CT扫描记录
    scans = BrainCTScan.query.filter_by(follow_up_recommended=True).all()
    today = date.today()

    # 为需要随访的CT扫描创建随访记录
    for scan in scans:
        # 部分扫描有后续随访记录
        if randint(0, 10) < 7:  # 70%几率有随访记录
            # 获取原始扫描日期
            original_scan_date = scan.scan_date.date()

            # 随访日期：必须晚于原始扫描日期，但不晚于今天
            # 通常在原始扫描后30-180天
            max_days_after = min(180, (today - original_scan_date).days)

            # 如果原始扫描太近(小于30天)，没有足够时间进行随访，则跳过
            if max_days_after < 30:
                continue

            # 随访日期在原始扫描后30天到max_days_after之间
            days_after = randint(30, max_days_after)
            follow_up_date = original_scan_date + timedelta(days=days_after)

            # 下次随访日期：如果设置，则必须安排在将来
            # 50%的几率安排下次随访
            next_follow_up = None
            if randint(0, 1) == 1:
                # 下次随访安排在今天之后的30-180天
                next_follow_up = today + timedelta(days=randint(30, 180))

            follow_up = CTFollowUp(
                original_scan_id=scan.scan_id,
                follow_up_date=follow_up_date,
                comparison_results=choice(comparison_results),
                disease_progression=choice(disease_progressions),
                treatment_response=choice(treatment_responses),
                next_follow_up=next_follow_up
            )
            db.session.add(follow_up)

    db.session.commit()
    print("CT随访记录创建完成")


def create_neurological_assessments():
    """创建神经系统评估记录"""
    print("创建神经系统评估记录...")

    motor_functions = [
        "肢体运动功能正常，肌力5级",
        "左侧上肢肌力4级，其余肢体正常",
        "下肢肌力对称，约4+级",
        "右侧肢体肌力较左侧稍弱，约4级",
        "四肢肌力正常，但右手精细动作欠协调",
        "左侧肢体肌张力增高，肌力3级",
        "双下肢肌力减退，约3级，近端优于远端",
        "四肢近端肌力4级，远端3级，考虑周围神经病变",
        "右侧面部表情肌无力，口角歪斜",
        "双手肌间萎缩，精细动作障碍"
    ]

    sensory_functions = [
        "感觉功能正常，各种感觉未见异常",
        "右侧面部轻触觉略减退",
        "左侧下肢远端温度觉减退",
        "双侧肢体本体感觉良好",
        "右手指尖触觉轻度减退",
        "臀部以下痛觉减退",
        "左侧身体痛温觉减退，界限清楚在T10水平",
        "四肢远端手套袜套样感觉减退",
        "双足振动觉减退",
        "右侧三叉神经分布区痛觉过敏"
    ]

    reflex_statuses = [
        "腱反射正常，病理征阴性",
        "双侧腱反射活跃，病理征阴性",
        "右侧膝反射亢进，踝反射减弱",
        "左侧Babinski征阳性，Hoffmann征阴性",
        "颈部强直，脑膜刺激征阴性",
        "双下肢腱反射亢进，Babinski征阳性",
        "右侧Hoffmann征和Babinski征均阳性",
        "腹壁反射消失，提示中枢神经系统病变",
        "膝反射减弱，踝反射消失，提示周围神经病变",
        "颈项强直，Kernig征阳性，脑膜刺激征阳性"
    ]

    coordinations = [
        "协调性良好，指鼻试验与跟膝胫试验正常",
        "左侧指鼻试验欠协调，跟膝胫试验正常",
        "右侧轻度共济失调，行走时轻度不稳",
        "指鼻试验双侧轻微欠协调，步态稳定",
        "精细动作协调性下降，但大动作协调正常",
        "闭眼站立时身体明显摇晃，Romberg征阳性",
        "步态不稳，小脑性共济失调明显",
        "快速轮替运动障碍，提示锥体外系损害",
        "右侧指鼻及跟膝胫试验均表现共济失调",
        "步态呈现明显的蹒跚，宽基底步态特征"
    ]

    cranial_nerve_exams = [
        "脑神经检查无异常",
        "右侧面部感觉略减退，余脑神经检查正常",
        "左侧眼球外展受限，余脑神经功能正常",
        "双侧瞳孔等大等圆，对光反射灵敏",
        "右侧周围性面瘫，其余脑神经检查正常",
        "双侧视乳头水肿，视力下降",
        "右侧听力下降，Weber试验偏向左侧",
        "双侧嗅觉减退，提示嗅神经损害",
        "舌肌萎缩，伸舌偏左，提示舌下神经损害",
        "软腭抬高不良，吞咽困难，提示迷走神经损害"
    ]

    performed_by_names = ["王主任", "李副主任", "张主治医师", "刘医师", "陈副院长", "杨医师", "赵主治医师", "吴医师"]

    # 获取所有患者
    patients = Patient.query.all()

    # 为70%的患者创建神经系统评估记录，增加比例
    for patient in patients:
        if randint(1, 10) <= 7:  # 70%几率
            assessment_count = randint(1, 3)  # 1-3份评估记录

            for i in range(assessment_count):
                # 评估日期（过去的记录）
                assessment_date = datetime.now() - timedelta(days=randint(5, 150))

                # 格拉斯哥昏迷评分(GCS)，正常为15分
                gcs_score = 15
                if randint(1, 10) <= 2:  # 20%几率有异常
                    gcs_score = randint(9, 14)

                # 简易精神状态检查(MMSE)分数，满分30分
                mmse_score = randint(24, 30)  # 正常或轻度异常
                if patient.age > 70 and randint(1, 10) <= 3:  # 年龄大且30%几率有明显异常
                    mmse_score = randint(15, 23)  # 中度认知障碍

                # 蒙特利尔认知评估(MoCA)分数，满分30分，正常≥26分
                moca_score = randint(26, 30)  # 正常
                if mmse_score < 26:  # MMSE已显示认知障碍
                    moca_score = randint(15, 25)  # 也有认知障碍

                assessment = NeurologicalAssessment(
                    patient_id=patient.patient_id,
                    assessment_date=assessment_date,
                    motor_function=choice(motor_functions),
                    sensory_function=choice(sensory_functions),
                    reflex_status=choice(reflex_statuses),
                    coordination=choice(coordinations),
                    cranial_nerve_exam=choice(cranial_nerve_exams),
                    gcs_score=gcs_score,
                    mmse_score=mmse_score,
                    moca_score=moca_score,
                    assessment_notes=f"患者{patient.name}{choice(['需进一步随访观察', '症状有所改善', '症状相对稳定', '治疗后效果显著', '需调整治疗方案', '建议完善相关检查'])}" if randint(
                        0, 1) else None,
                    performed_by=choice(performed_by_names)
                )
                db.session.add(assessment)

    db.session.commit()
    print("神经系统评估记录创建完成")


def create_medication_records():
    """创建药物治疗记录"""
    print("创建药物治疗记录...")

    dosages = ["25mg", "50mg", "100mg", "75mg", "200mg", "5mg", "10mg", "20mg", "30mg", "40mg", "60mg", "80mg", "250mg",
               "500mg"]
    frequencies = ["每日一次", "每日两次", "每日三次", "每周一次", "每晚一次", "需要时服用", "每日四次", "隔日一次",
                   "每日早晚各一次"]
    routes = ["口服", "静脉注射", "肌肉注射", "舌下含服", "透皮贴剂", "口腔崩解片", "缓释片", "控释片", "鼻喷"]
    indications = [
        "高血压",
        "头痛",
        "睡眠障碍",
        "焦虑",
        "癫痫",
        "帕金森症状",
        "认知障碍",
        "脑部缺血",
        "脑外伤后遗症",
        "抑郁症",
        "精神分裂症",
        "中风后遗症",
        "肌张力障碍",
        "眩晕",
        "痴呆",
        "脑血管痉挛",
        "颅内压增高",
        "血管性头痛",
        "神经痛",
        "神经炎症"
    ]
    side_effects = [
        "无明显不良反应",
        "轻度头晕",
        "恶心",
        "嗜睡",
        "食欲不振",
        "皮疹",
        "腹泻",
        "口干",
        "低血压",
        "肝酶升高",
        "白细胞减少",
        "心动过缓",
        "心悸",
        "体重增加",
        "视物模糊",
        "便秘",
        "记忆力减退",
        "肌肉酸痛",
        None
    ]
    effectiveness = [
        "效果良好，症状明显缓解",
        "效果一般，症状部分缓解",
        "暂未见明显效果，需继续观察",
        "症状得到有效控制",
        "服药后头痛基本消失",
        "血压控制在理想范围",
        "癫痫发作频率明显减少",
        "睡眠质量改善明显",
        "抑郁症状有所好转",
        "认知功能有轻度改善",
        "眩晕症状基本消失",
        "神经痛有明显缓解",
        "疼痛强度显著降低",
        "病情稳定，无明显进展",
        "需要调整剂量以获得更好效果"
    ]

    # 获取所有患者
    patients = Patient.query.all()

    # 为每个患者创建药物治疗记录
    for patient in patients:
        # 每个患者有2-5种药物记录，增加数量
        medication_count = randint(2, 5)

        # 用药周期通常不同，避免所有药物同时开始和结束
        for i in range(medication_count):
            # 选择一种药物
            medication = choice(medications)

            # 开始用药日期（过去的日期）
            start_date = date.today() - timedelta(days=randint(10, 200))

            # 结束用药日期（可能尚未结束）
            end_date = None
            if randint(0, 10) < 7:  # 70%的几率药物有结束日期
                # 用药周期在10天到180天之间，增加用药时长
                end_date = start_date + timedelta(days=randint(10, 180))

            # 创建更详细的备注
            notes = None
            if randint(0, 1):
                note_templates = [
                    f"患者服用{medication}情况{choice(['良好', '一般', '较好', '需观察'])}，{choice(['无明显不良反应', '有轻微副作用但可耐受', '效果显著', '考虑调整剂量'])}。",
                    f"{medication}治疗{choice(indications)}，病情{choice(['已得到控制', '有所缓解', '基本稳定', '仍需观察'])}。",
                    f"患者对{medication}耐受性{choice(['良好', '一般', '较差'])}，{choice(['建议继续当前方案', '考虑更换药物', '可能需要调整剂量'])}。",
                    f"{medication}用于控制{choice(indications)}，{choice(['效果明显', '效果一般', '需要评估疗效', '与其他药物联合使用效果更佳'])}。"
                ]
                notes = choice(note_templates)

            # 创建药物记录
            record = MedicationRecord(
                patient_id=patient.patient_id,
                medication_name=medication,
                dosage=choice(dosages),
                frequency=choice(frequencies),
                administration_route=choice(routes),
                start_date=start_date,
                end_date=end_date,
                indication=choice(indications),
                side_effects=choice(side_effects),
                effectiveness=choice(effectiveness),
                notes=notes
            )
            db.session.add(record)

    db.session.commit()
    print("药物治疗记录创建完成")


def create_mental_health_records():
    """创建心理健康评估记录"""
    print("创建心理健康评估记录...")

    status_summaries = [
        "患者情绪稳定，思维清晰，无明显心理问题",
        "患者存在轻度焦虑情绪，对疾病预后有担忧",
        "患者有抑郁表现，情绪低落，兴趣减退",
        "患者情绪起伏较大，存在适应障碍",
        "患者对自身状况较为悲观，有自伤想法但无行动",
        "患者心理状态良好，对治疗持积极态度",
        "患者表现出轻度强迫症状，对某些事物过度关注",
        "患者有社交回避倾向，不愿与他人交流",
        "患者存在创伤后应激反应，对类似事件有过度警觉",
        "患者表现出轻微偏执思维，对治疗存疑虑",
        "患者情绪波动明显，有情绪失控史",
        "患者表现出轻度认知障碍，记忆力和注意力下降",
        "患者自我评价低，缺乏自信，对未来感到迷茫",
        "患者有轻度幻觉体验，但能辨别现实",
        "患者心理状态稳定，家庭支持良好，康复信心足"
    ]

    sleep_qualities = [
        "睡眠质量良好，无明显入睡困难",
        "入睡困难，夜间易醒，睡眠质量差",
        "需要借助药物入睡，但睡眠维持正常",
        "睡眠时间充足但醒后不解乏",
        "早醒，总睡眠时间减少",
        "睡眠规律，偶有噩梦",
        "深睡眠时间明显减少，多梦",
        "睡眠周期紊乱，昼夜颠倒",
        "睡眠呈周期性波动，与情绪变化相关",
        "睡眠中有惊厥样表现，需进一步评估",
        "睡眠时有呼吸暂停现象，或有打鼾史",
        "睡眠过程中有异常行为，如梦游、磨牙等",
        "入睡潜伏期延长，平均需要30分钟以上",
        "夜间多次醒来，需频繁如厕",
        "服用催眠药后睡眠质量有明显改善"
    ]

    recommended_actions = [
        "建议定期随访，暂无需特殊干预",
        "建议心理疏导，教授放松技巧",
        "建议咨询精神科医生，考虑药物治疗",
        "建议参加团体心理治疗",
        "需要进一步心理评估和干预",
        "建议改善睡眠环境，养成良好作息习惯",
        "建议开展认知行为治疗",
        "推荐正念减压疗法，缓解焦虑情绪",
        "建议家庭治疗，改善家庭支持系统",
        "推荐职业疗法，增强社会功能",
        "建议进行放松训练，学习应对压力的方法",
        "推荐阅读相关心理健康书籍，增强自我认知",
        "建议适当运动，有助于改善情绪",
        "推荐社交技能训练，改善人际关系",
        "建议保持规律生活，避免过度劳累"
    ]

    # 社会支持评估
    social_supports = [
        "家庭支持良好，有稳定的社交圈",
        "主要依靠配偶提供支持，社交圈较小",
        "家庭关系紧张，社会支持系统薄弱",
        "独居，缺乏日常社会交往",
        "有稳定工作和同事关系，但家庭支持有限",
        "退休后社交活动减少，主要靠子女支持",
        "有良好的邻里关系，但缺乏亲密关系",
        "社交回避，主动减少社会交往",
        "有稳定伴侣关系，但缺乏更广泛的社会支持",
        "居住在养老机构，与家人联系不频繁"
    ]

    # 应对策略评估
    coping_strategies = [
        "积极寻求解决问题的方法，面对压力保持乐观",
        "倾向于回避问题，情绪调节能力有限",
        "过度依赖他人帮助，自我效能感低",
        "有良好的情绪调节能力，能理性分析问题",
        "应对压力时容易情绪化，自我调节困难",
        "善于寻求社会支持，但独立解决问题能力弱",
        "有明确的人生目标，面对挫折能坚持不懈",
        "对问题有洞察力，但行动力不足",
        "倾向于宗教信仰来应对困难",
        "通过体育锻炼和爱好排解压力"
    ]

    # 生活质量评估
    life_qualities = [
        "生活质量良好，能独立完成日常活动",
        "受疾病影响，生活质量有所下降",
        "需要他人部分协助完成日常活动",
        "生活自理能力良好，但社会活动参与减少",
        "工作能力受到限制，但家庭生活基本正常",
        "生活质量严重受损，需要大量支持",
        "疾病影响睡眠和饮食，但基本活动不受限",
        "经济困难影响治疗和生活质量",
        "居住环境良好，有利于康复",
        "亲友支持充分，提高了生活质量"
    ]

    # 获取所有患者
    patients = Patient.query.all()

    # 为85%的患者创建心理健康评估记录，增加比例
    for patient in patients:
        if randint(1, 20) <= 17:  # 85%几率
            assessment_count = randint(1, 3)  # 1-3份评估记录，增加数量

            for i in range(assessment_count):
                # 评估日期（过去的记录）
                assessment_date = date.today() - timedelta(days=randint(5, 150))

                # 焦虑和抑郁程度(1-10)
                anxiety_level = randint(1, 10)
                depression_level = randint(1, 10)

                # 创建心理健康评估记录，增加更多字段
                mental_health = MentalHealth(
                    patient_id=patient.patient_id,
                    assessment_date=assessment_date,
                    status_summary=choice(status_summaries),
                    anxiety_level=anxiety_level,
                    depression_level=depression_level,
                    sleep_quality=choice(sleep_qualities),
                    recommended_action=choice(recommended_actions)
                )
                db.session.add(mental_health)

    db.session.commit()
    print("心理健康评估记录创建完成")


def create_chat_sessions_and_messages():
    """创建聊天会话和消息"""
    print("创建聊天会话和消息...")

    # 聊天会话标题模板
    session_titles = [
        "关于{symptom}的咨询",
        "询问{disease}治疗方案",
        "检查结果解读",
        "用药指导咨询",
        "治疗后随访",
        "影像结果咨询",
        "术后康复建议"
    ]

    # 症状和疾病列表，用于生成会话标题
    symptoms = ["头痛", "头晕", "失眠", "记忆力下降", "视力模糊", "手抖", "行走不稳"]
    diseases = ["高血压", "脑梗", "帕金森", "阿尔茨海默", "癫痫", "脑肿瘤", "蛛网膜下腔出血"]

    # 用户消息模板
    user_messages = [
        "医生，我最近{symptom}，这是怎么回事？",
        "请问我的检查结果有什么问题吗？",
        "这个药物有什么副作用需要注意的？",
        "我需要进一步检查吗？",
        "这种情况严重吗？需要住院治疗吗？",
        "为什么我服药后会感到{side_effect}？",
        "我的{disease}能治好吗？",
        "这种治疗方案的成功率有多高？",
        "我想了解一下我的CT结果代表什么意思。"
    ]

    # 机器人（医生）消息模板
    bot_messages = [
        "您好，根据您描述的症状，可能与{possible_cause}有关。建议您{recommendation}。",
        "您的检查结果显示{finding}，这提示可能存在{diagnosis}。建议您{next_step}。",
        "这种药物的常见副作用包括{side_effects}。如果症状严重，请立即就医。",
        "根据您的情况，建议进行{exam}检查，以明确诊断。",
        "您的情况{severity}，{treatment_suggestion}。",
        "服药后出现{side_effect}属于正常现象，通常会在{time_period}后缓解。如持续不适，请联系医生。",
        "关于{disease}，目前的治疗方法可以{prognosis}。请保持积极心态，规律治疗。",
        "这种治疗方案的成功率约为{success_rate}%，但具体效果因人而异。",
        "您的CT检查显示{ct_finding}，这意味着{interpretation}。建议您{follow_up}。"
    ]

    # 症状副作用
    side_effects = ["头晕", "恶心", "乏力", "嗜睡", "食欲不振", "皮疹", "心悸"]
    # 可能病因
    possible_causes = ["颈椎病", "高血压", "焦虑症", "贫血", "前庭功能障碍", "药物副作用"]
    # 建议
    recommendations = ["近期复查", "增加运动", "调整用药", "保持规律作息", "进行颈椎牵引", "控制饮食"]
    # 检查发现
    findings = ["血压偏高", "血糖不稳定", "肝功能轻度异常", "脑白质疏松改变", "颈椎退行性改变"]
    # 诊断
    diagnoses = ["高血压", "糖尿病前期", "药物性肝损伤", "脑小血管病", "颈椎病"]
    # 下一步建议
    next_steps = ["定期监测血压", "调整饮食结构", "暂停可疑药物", "进行脑部MRI检查", "进行颈椎牵引治疗"]
    # 推荐检查
    exams = ["头颅MRI", "颈椎CT", "心电图", "血常规", "肝功能", "甲状腺功能"]
    # 严重程度
    severities = ["比较轻微", "需要重视但不必过度担忧", "相对严重", "属于急性发作", "处于恢复期"]
    # 治疗建议
    treatment_suggestions = ["建议口服药物治疗", "需要短期住院观察", "可以门诊保守治疗", "需要手术干预", "建议物理治疗"]
    # 时间周期
    time_periods = ["1-2天", "一周左右", "2-3周", "一个月", "用药初期"]
    # 预后
    prognoses = ["有效控制症状", "延缓病情进展", "显著改善生活质量", "部分患者可以治愈", "控制不适症状"]
    # 成功率
    success_rates = ["60-70", "75-85", "50-60", "80-90", "65-75"]
    # CT发现
    ct_findings = ["脑室系统正常", "局部低密度影", "多发腔隙性脑梗死", "轻度脑萎缩", "无明显异常"]
    # CT解释
    interpretations = ["目前脑部结构正常", "存在缺血性改变", "有慢性脑血管病变", "符合年龄相关改变", "无急性病变"]
    # 随访建议
    follow_ups = ["六个月后复查", "调整降压药物", "定期监测认知功能", "进行颈动脉超声检查", "规律服药"]

    # 获取所有用户
    users = User.query.all()

    # 为每个用户创建1-3个聊天会话
    for user in users:
        # 确定会话数量
        session_count = randint(1, 3)

        for i in range(session_count):
            # 创建会话标题
            title_template = choice(session_titles)
            if "{symptom}" in title_template:
                title = title_template.format(symptom=choice(symptoms))
            elif "{disease}" in title_template:
                title = title_template.format(disease=choice(diseases))
            else:
                title = title_template

            # 创建会话记录
            created_at = datetime.now() - timedelta(days=randint(1, 60))
            chat_session = ChatSession(
                user_id=user.user_id,
                title=title,
                created_at=created_at,
                updated_at=created_at + timedelta(minutes=randint(10, 120)),
                is_active=randint(0, 10) > 2  # 80%的会话是活跃的
            )
            db.session.add(chat_session)
            db.session.flush()  # 获取session_id

            # 为每个会话创建3-10条消息
            message_count = randint(3, 10)

            # 初始消息时间
            message_time = chat_session.created_at

            # 用户先发消息
            is_user_turn = True

            for j in range(message_count):
                # 确定消息内容
                if is_user_turn:
                    # 用户消息
                    msg_template = choice(user_messages)
                    if "{symptom}" in msg_template:
                        content = msg_template.format(symptom=choice(symptoms))
                    elif "{disease}" in msg_template:
                        content = msg_template.format(disease=choice(diseases))
                    elif "{side_effect}" in msg_template:
                        content = msg_template.format(side_effect=choice(side_effects))
                    else:
                        content = msg_template

                    role = "user"
                else:
                    # 机器人（医生）消息
                    msg_template = choice(bot_messages)

                    # 根据模板中的占位符填充内容
                    if "{possible_cause}" in msg_template:
                        content = msg_template.format(
                            possible_cause=choice(possible_causes),
                            recommendation=choice(recommendations)
                        )
                    elif "{finding}" in msg_template:
                        content = msg_template.format(
                            finding=choice(findings),
                            diagnosis=choice(diagnoses),
                            next_step=choice(next_steps)
                        )
                    elif "{side_effects}" in msg_template:
                        content = msg_template.format(
                            side_effects=", ".join(sample(side_effects, randint(2, 4)))
                        )
                    elif "{exam}" in msg_template:
                        content = msg_template.format(exam=choice(exams))
                    elif "{severity}" in msg_template:
                        content = msg_template.format(
                            severity=choice(severities),
                            treatment_suggestion=choice(treatment_suggestions)
                        )
                    elif "{side_effect}" in msg_template:
                        content = msg_template.format(
                            side_effect=choice(side_effects),
                            time_period=choice(time_periods)
                        )
                    elif "{disease}" in msg_template:
                        content = msg_template.format(
                            disease=choice(diseases),
                            prognosis=choice(prognoses)
                        )
                    elif "{success_rate}" in msg_template:
                        content = msg_template.format(success_rate=choice(success_rates))
                    elif "{ct_finding}" in msg_template:
                        content = msg_template.format(
                            ct_finding=choice(ct_findings),
                            interpretation=choice(interpretations),
                            follow_up=choice(follow_ups)
                        )
                    else:
                        content = msg_template

                    role = "bot"

                # 创建消息记录
                message = ChatMessage(
                    session_id=chat_session.session_id,
                    role=role,
                    content=content,
                    image_path=None,  # 简化起见，不添加图片
                    created_at=message_time
                )
                db.session.add(message)

                # 更新时间和下一条消息的发送者
                message_time = message_time + timedelta(minutes=randint(1, 10))
                is_user_turn = not is_user_turn

    db.session.commit()
    print("聊天会话和消息创建完成")


def create_system_logs():
    """创建系统日志记录"""
    print("创建系统日志...")

    operations = ["login", "logout", "create", "update", "delete", "backup", "restore"]
    ip_addresses = [
        "192.168.1.100", "192.168.1.101", "192.168.1.102",
        "10.0.0.1", "10.0.0.2", "172.16.0.1",
        "127.0.0.1"
    ]

    # 针对不同操作类型的描述模板
    description_templates = {
        "login": ["用户登录系统", "成功登录", "登录成功，IP地址: {ip}"],
        "logout": ["用户登出系统", "成功登出", "安全退出系统"],
        "create": ["创建{resource}记录", "新增{resource}数据", "添加新的{resource}"],
        "update": ["更新{resource}记录", "修改{resource}信息", "编辑{resource}数据"],
        "delete": ["删除{resource}记录", "移除{resource}数据", "永久删除{resource}信息"],
        "backup": ["系统数据备份", "创建数据库备份", "备份完成，文件大小: {size}MB"],
        "restore": ["系统数据恢复", "从备份恢复数据", "数据恢复完成"]
    }

    # 可以操作的资源类型
    resources = ["患者", "预约", "医生", "检查报告", "医疗记录", "用户账号", "系统配置", "影像数据"]

    # 备份大小范围(MB)
    backup_sizes = [10, 15, 20, 25, 30, 35, 40, 45, 50]

    # 获取所有用户
    users = User.query.all()

    # 创建系统日志记录
    log_count = 100  # 创建100条系统日志

    for _ in range(log_count):
        # 随机选择一个用户（或系统操作）
        user = choice(users) if randint(0, 10) > 1 else None  # 90%的日志有关联用户

        # 选择操作类型
        operation = choice(operations)

        # 生成日志描述
        description_template = choice(description_templates[operation])

        if "{resource}" in description_template:
            description = description_template.format(resource=choice(resources))
        elif "{ip}" in description_template:
            description = description_template.format(ip=choice(ip_addresses))
        elif "{size}" in description_template:
            description = description_template.format(size=choice(backup_sizes))
        else:
            description = description_template

        # 创建日志记录
        log = SystemLog(
            user_id=user.user_id if user else None,
            username=user.username if user else "系统",
            operation=operation,
            description=description,
            ip=choice(ip_addresses),
            create_time=datetime.now() - timedelta(days=randint(0, 30), hours=randint(0, 23), minutes=randint(0, 59))
        )
        db.session.add(log)

    db.session.commit()
    print("系统日志创建完成")


def create_system_config():
    """创建系统配置"""
    print("创建系统配置...")

    config = SystemConfig(
        system_name="医疗影像智能分析与预约管理系统",
        system_description="一个集成深度学习医学影像分析、智能诊断、医患沟通、预约管理、患者全周期管理等功能的综合医疗服务平台。",
        system_logo="/static/images/logo.png",
        system_version="1.0.0",
        system_status=True,
        update_time=datetime.now()
    )
    db.session.add(config)

    db.session.commit()
    print("系统配置创建完成")


def create_notifications():
    """创建示例通知数据"""
    print("\n创建通知数据...")
    
    # 获取所有医生和患者
    doctors = User.query.filter_by(role='doctor').all()
    patients = User.query.filter_by(role='patient').all()
    
    # 系统通知
    system_notifications = [
        {
            'title': '系统维护通知',
            'message': '系统将于今晚22:00-23:00进行例行维护，请提前做好相关准备。',
            'type': 'system',
            'priority': 1,
            'status': 'active'
        },
        {
            'title': '新功能上线',
            'message': '在线问诊功能已上线，欢迎体验使用。',
            'type': 'system',
            'priority': 0,
            'status': 'active'
        }
    ]
    
    # 为所有用户创建系统通知
    for notification in system_notifications:
        # 给所有医生发送
        for doctor in doctors:
            new_notification = Notification(
                receiver_type='doctor',
                receiver_id=doctor.user_id,
                title=notification['title'],
                message=notification['message'],
                type=notification['type'],
                priority=notification['priority'],
                status=notification['status'],
                created_at=datetime.now() - timedelta(days=randint(1, 5))
            )
            db.session.add(new_notification)
        
        # 给所有患者发送
        for patient in patients:
            new_notification = Notification(
                receiver_type='patient',
                receiver_id=patient.user_id,
                title=notification['title'],
                message=notification['message'],
                type=notification['type'],
                priority=notification['priority'],
                status=notification['status'],
                created_at=datetime.now() - timedelta(days=randint(1, 5))
            )
            db.session.add(new_notification)
    
    # 预约相关通知
    appointments = Appointment.query.all()
    for appointment in appointments:
        # 给患者发送预约通知
        patient_notification = Notification(
            receiver_type='patient',
            receiver_id=appointment.patient_id,
            title='预约提醒',
            message=f'您有一个{appointment.appointment_type.display_name}预约，时间：{appointment.appointment_date} {appointment.time_slot.display_name}',
            type='appointment',
            related_id=appointment.appointment_id,
            priority=1,
            status='active',
            created_at=appointment.created_at
        )
        db.session.add(patient_notification)
        
        # 给医生发送预约通知
        doctor_notification = Notification(
            receiver_type='doctor',
            receiver_id=appointment.doctor_id,
            title='新预约提醒',
            message=f'您有一个新的{appointment.appointment_type.display_name}预约，患者：{appointment.patient.name}，时间：{appointment.appointment_date} {appointment.time_slot.display_name}',
            type='appointment',
            related_id=appointment.appointment_id,
            priority=1,
            status='active',
            created_at=appointment.created_at
        )
        db.session.add(doctor_notification)
    
    # 聊天消息通知
    chat_messages = ChatMessage.query.all()
    for message in chat_messages:
        if message.role == 'bot':  # 只处理AI助手的回复
            session = ChatSession.query.get(message.session_id)
            if session:
                notification = Notification(
                    receiver_type='patient' if session.user.role == 'patient' else 'doctor',
                    receiver_id=session.user_id,
                    title='新消息提醒',
                    message=f'您收到一条新的AI助手回复：{message.content[:50]}...',
                    type='chat',
                    related_id=message.message_id,
                    priority=0,
                    status='active',
                    created_at=message.created_at
                )
                db.session.add(notification)
    
    try:
        db.session.commit()
        print("通知数据创建成功")
    except Exception as e:
        db.session.rollback()
        print(f"创建通知数据失败: {e}")


if __name__ == "__main__":
    with app.app_context():
        create_test_data()

        # 在测试数据创建完成后输出账号信息
        print("\n========== 账号信息 ==========")
        print("管理员账号：admin (密码: 123456)")

        print("\n医生账号:")
        doctors = User.query.filter_by(role='doctor').all()
        for doctor in doctors:
            print(f"- {doctor.username} (密码: 123456) - {doctor.real_name}")

        print("\n患者账号:")
        patients = User.query.filter_by(role='patient').all()
        for patient in patients:
            print(f"- {patient.username} (密码: 123456) - {patient.real_name}")

        print("\n注意：所有账号的默认密码均为123456")
