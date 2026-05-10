from flask_sqlalchemy import SQLAlchemy
from datetime import date, datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from werkzeug.security import check_password_hash, generate_password_hash
import enum
from db_config import get_sqlalchemy_uri, DB_CONFIG

db = SQLAlchemy()
ph = PasswordHasher()


# 数据库

# 用户表
class User(db.Model):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)  # 登录用户名
    password_hash = db.Column(db.String(1024), nullable=False)  # 加密密码
    real_name = db.Column(db.String(50), nullable=False)  # 真实姓名
    id_card = db.Column(db.String(18), unique=True, nullable=False)  # 身份证号
    email = db.Column(db.String(100))  # 电子邮箱
    phone = db.Column(db.String(20))  # 手机号码
    registration_date = db.Column(db.DateTime, default=datetime.now)  # 注册时间
    last_login = db.Column(db.DateTime)  # 最后登录时间
    is_active = db.Column(db.Boolean, default=True)  # 账户是否激活
    role = db.Column(db.String(20), default='patient')  # 用户角色: patient, doctor, admin 等
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=True)  # 关联患者ID
    # 与患者表建立一对一关系
    patient = db.relationship('Patient', foreign_keys=[patient_id], backref=db.backref('user', uselist=False))

    # 密码处理方法
    def set_password(self, password):
        self.password_hash = ph.hash(password)

    def check_password(self, password):
        try:
            return ph.verify(self.password_hash, password)
        except VerifyMismatchError:
            return False


class Patient(db.Model):
    __tablename__ = 'patient'

    patient_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.Enum('男', '女'))
    address = db.Column(db.String(255))
    contact_info = db.Column(db.String(100))
    blood_type = db.Column(db.Enum('A', 'B', 'AB', 'O'), nullable=True)  # 修改为可为空
    emergency_contact = db.Column(db.String(100))
    status = db.Column(db.String(20), default='新患者')  # 状态: 新患者, 待就诊, 就诊中, 随访中, 治疗完成
    doctor_advice = db.Column(db.Text)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.user_id'))

    # 与其他表建立一对多关系（反向引用 patient）
    medical_history = db.relationship('MedicalHistory', backref='patient', lazy=True)
    physical_exams = db.relationship('PhysicalExam', backref='patient', lazy=True)
    medication_records = db.relationship('MedicationRecord', backref='patient', lazy=True)
    mental_health_records = db.relationship('MentalHealth', backref='patient', lazy=True)
    brain_ct_scans = db.relationship('BrainCTScan', backref='patient', lazy=True)
    neurological_assessments = db.relationship('NeurologicalAssessment', backref='patient', lazy=True)
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref='patients_treated')
    appointments = db.relationship('Appointment', back_populates='patient', lazy=True)
    imaging_reports = db.relationship('ImagingReport', back_populates='patient', lazy=True)
    medical_images = db.relationship('MedicalImaging', back_populates='patient', lazy=True)

    # 通过关系表获取关联的医生
    doctors = db.relationship('User',
                              secondary='doctor_patient_relation',
                              primaryjoin='Patient.patient_id==DoctorPatientRelation.patient_id',
                              secondaryjoin='User.user_id==DoctorPatientRelation.doctor_id',
                              backref=db.backref('associated_patients', lazy='dynamic'),
                              lazy='dynamic')


# 新增：医患关系表
class DoctorPatientRelation(db.Model):
    __tablename__ = 'doctor_patient_relation'

    relation_id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.now)  # 关系开始时间
    is_active = db.Column(db.Boolean, default=True)  # 关系是否活跃
    relation_type = db.Column(db.String(20), default='主治')  # 关系类型: 主治, 会诊, 转诊
    patient_group = db.Column(db.String(20), default='常规患者')  # 患者分组: 常规患者, 重点随访, VIP
    last_visit_date = db.Column(db.DateTime)  # 最近就诊日期
    next_visit_date = db.Column(db.DateTime)  # 下次随访日期
    notes = db.Column(db.Text)  # 医生备注

    # 定义复合唯一约束
    __table_args__ = (
        db.UniqueConstraint('doctor_id', 'patient_id', name='uix_doctor_patient'),
    )

    # 关联关系
    doctor = db.relationship('User', foreign_keys=[doctor_id], overlaps="associated_patients,doctors")
    patient = db.relationship('Patient', foreign_keys=[patient_id], overlaps="associated_patients,doctors")


class MedicalImaging(db.Model):
    """医学影像诊断记录表"""
    __tablename__ = 'medical_imaging'
    imaging_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True) # 操作医生
    image_type = db.Column(db.String(50), nullable=False)  # 影像类型, 如"大脑", "肝脏"等
    file_path = db.Column(db.String(255), nullable=False)  # 原始图像文件路径
    result_path = db.Column(db.String(255))  # 预测结果文件路径
    result_text = db.Column(db.Text)  # 预测结果文本描述
    tumor_volume = db.Column(db.Float)  # 肿瘤体积，单位mm³
    created_at = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    notes = db.Column(db.Text)  # 备注

    # 新增关系
    reports = db.relationship('ImagingReport', backref='imaging_record', lazy=True)
    patient = db.relationship('Patient', back_populates='medical_images')


class ImagingReport(db.Model):
    __tablename__ = 'imaging_report'
    report_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    imaging_id = db.Column(db.Integer, db.ForeignKey('medical_imaging.imaging_id'), nullable=True)
    report_type = db.Column(db.String(50), nullable=False)  # 如 "CT", "MRI", "AI辅助诊断"
    report_date = db.Column(db.Date, nullable=False)
    analysis_result = db.Column(db.Text)  # 分析结果原文
    conclusion = db.Column(db.Text)  # 结论和建议（可选）
    source_image_url = db.Column(db.String(255))  # 原始图像链接
    created_at = db.Column(db.DateTime, default=datetime.now)
    health_advice = db.Column(db.Text)
    patient = db.relationship('Patient', back_populates='imaging_reports')


class ChatSession(db.Model):
    """聊天会话表"""
    session_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False)  # 关联用户ID
    title = db.Column(db.String(100), nullable=False)  # 会话标题
    created_at = db.Column(db.DateTime, default=datetime.now)  # 创建时间
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间
    is_active = db.Column(db.Boolean, default=True)  # 是否活跃

    # 与用户表建立多对一关系
    user = db.relationship('User', backref=db.backref('chat_sessions', lazy=True))
    # 与消息表建立一对多关系
    messages = db.relationship('ChatMessage', backref='session', lazy=True, cascade="all, delete-orphan")


class ChatMessage(db.Model):
    """聊天消息表"""
    message_id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.session_id'), nullable=False)  # 关联会话ID
    role = db.Column(db.String(10), nullable=False)  # 消息角色：user 或 bot
    content = db.Column(db.Text, nullable=False)  # 消息内容
    image_path = db.Column(db.String(255))  # 图片路径，如果有的话
    created_at = db.Column(db.DateTime, default=datetime.now)  # 创建时间


# ---------------- 病史记录表 ----------------
class MedicalHistory(db.Model):
    __tablename__ = 'medical_history'

    history_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    allergy_info = db.Column(db.Text)
    family_history = db.Column(db.Text)  # 家族病史
    previous_head_injuries = db.Column(db.Text)  # 既往头部创伤史
    neurological_conditions = db.Column(db.Text)  # 神经系统疾病史


# ---------------- 预约记录表 ----------------
class AppointmentStatus(enum.Enum):
    PENDING = 'pending'  # 待确认
    CONFIRMED = 'confirmed'  # 已确认
    COMPLETED = 'completed'  # 已完成
    CANCELLED = 'cancelled'  # 已取消
    MISSED = 'missed'  # 未到诊
    REJECTED = 'rejected'  # 已拒绝

    @property
    def display_name(self):
        return {
            'pending': '待确认',
            'confirmed': '已确认',
            'completed': '已完成',
            'cancelled': '已取消',
            'missed': '未到诊',
            'rejected': '已拒绝'
        }[self.value]

class NotificationType(enum.Enum):
    APPOINTMENT_NEW = 'appointment_new'
    APPOINTMENT_CONFIRMED = 'appointment_confirmed'
    APPOINTMENT_CANCELLED = 'appointment_cancelled'
    APPOINTMENT_COMPLETED = 'appointment_completed'
    APPOINTMENT_REMINDER = 'appointment_reminder'
    REPORT_READY = 'report_ready'
    SYSTEM_ALERT = 'system_alert'
    CHAT_MESSAGE = 'chat_message'
    GENERAL = 'general'

    @property
    def display_name(self):
        return {
            'appointment_new': '新预约',
            'appointment_confirmed': '预约确认',
            'appointment_cancelled': '预约取消',
            'appointment_completed': '就诊完成',
            'appointment_reminder': '预约提醒',
            'report_ready': '报告就绪',
            'system_alert': '系统警告',
            'chat_message': '新消息',
            'general': '通知'
        }.get(self.value, '通知')

class AppointmentType(enum.Enum):
    REGULAR = 'regular'  # 常规检查
    FOLLOWUP = 'followup'  # 复诊随访
    SPECIALIST = 'specialist'  # 专科预约
    EMERGENCY = 'emergency'  # 加急预约
    SPECIAL = 'special'  # 特需门诊

    @property
    def display_name(self):
        return {
            'regular': '常规检查',
            'followup': '复诊随访',
            'specialist': '专科预约',
            'emergency': '加急预约',
            'special': '特需门诊'
        }[self.value]

class Department(enum.Enum):
    NEUROLOGY = 'neurology'  # 神经科
    RADIOLOGY = 'radiology'  # 放射科
    CARDIOLOGY = 'cardiology'  # 心脏科
    ORTHOPEDICS = 'orthopedics'  # 骨科
    INTERNAL = 'internal'  # 内科
    NEUROSURGERY = 'neurosurgery'  # 神经外科
    NEUROLOGY_INTERNAL = 'neurology_internal'  # 神经内科

    @property
    def display_name(self):
        return {
            'neurology': '神经科',
            'radiology': '放射科',
            'cardiology': '心脏科',
            'orthopedics': '骨科',
            'internal': '内科',
            'neurosurgery': '神经外科',
            'neurology_internal': '神经内科'
        }[self.value]

class TimeSlot(enum.Enum):
    MORNING = 'morning'  # 上午
    AFTERNOON = 'afternoon'  # 下午

    @property
    def display_name(self):
        return {
            'morning': '上午 (8:00-12:00)',
            'afternoon': '下午 (14:00-17:30)'
        }[self.value]

class Appointment(db.Model):
    __tablename__ = 'appointment'

    appointment_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False, index=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=False, index=True)
    appointment_type = db.Column(db.Enum(AppointmentType), nullable=False)
    department = db.Column(db.Enum(Department), nullable=False)
    appointment_date = db.Column(db.Date, nullable=False, index=True)
    time_slot = db.Column(db.Enum(TimeSlot), nullable=False)
    symptoms = db.Column(db.Text)
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.PENDING, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now)
    checked_in_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    follow_up_required = db.Column(db.Boolean, default=False)
    follow_up_date = db.Column(db.Date)
    follow_up_notes = db.Column(db.Text)
    cancelled_at = db.Column(db.DateTime)
    cancelled_by = db.Column(db.String(20))  # patient, doctor, admin
    cancel_reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    code = db.Column(db.String(20))

    # 显式定义与Patient的双向关系
    patient = db.relationship('Patient', back_populates='appointments')
    doctor = db.relationship('User', backref=db.backref('appointments', lazy='dynamic'))

    def to_dict(self, lang='zh'):
        """转换为字典，支持中英文显示"""
        return {
            'id': self.appointment_id,
            'patient_id': self.patient_id,
            'doctor_id': self.doctor_id,
            'appointment_type': self.appointment_type.value,
            'appointment_type_display': self.appointment_type.display_name if lang == 'zh' else self.appointment_type.value,
            'department': self.department.value,
            'department_display': self.department.display_name if lang == 'zh' else self.department.value,
            'appointment_date': self.appointment_date.strftime('%Y-%m-%d'),
            'time_slot': self.time_slot.value,
            'time_slot_display': self.time_slot.display_name if lang == 'zh' else self.time_slot.value,
            'symptoms': self.symptoms,
            'status': self.status.value,
            'status_display': self.status.display_name if lang == 'zh' else self.status.value,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'checked_in_at': self.checked_in_at.strftime('%Y-%m-%d %H:%M:%S') if self.checked_in_at else None,
            'completed_at': self.completed_at.strftime('%Y-%m-%d %H:%M:%S') if self.completed_at else None,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date.strftime('%Y-%m-%d') if self.follow_up_date else None,
            'follow_up_notes': self.follow_up_notes,
            'cancelled_at': self.cancelled_at.strftime('%Y-%m-%d %H:%M:%S') if self.cancelled_at else None,
            'cancelled_by': self.cancelled_by,
            'cancel_reason': self.cancel_reason,
            'notes': self.notes,
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S') if self.updated_at else None,
            'code': self.code
        }

    def update_status(self, new_status, cancelled_by=None, cancel_reason=None):
        """更新预约状态，包含状态流转验证"""
        if not isinstance(new_status, AppointmentStatus):
            try:
                new_status = AppointmentStatus(new_status)
            except ValueError:
                raise ValueError(f"Invalid status: {new_status}")

        # 状态流转验证
        valid_transitions = {
            AppointmentStatus.PENDING: [AppointmentStatus.CONFIRMED, AppointmentStatus.REJECTED, AppointmentStatus.CANCELLED],
            AppointmentStatus.CONFIRMED: [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.MISSED],
            AppointmentStatus.COMPLETED: [],
            AppointmentStatus.CANCELLED: [],
            AppointmentStatus.MISSED: [],
            AppointmentStatus.REJECTED: []
        }

        if new_status not in valid_transitions[self.status]:
            raise ValueError(f"Cannot transition from {self.status.value} to {new_status.value}")

        # 更新状态
        self.status = new_status
        self.updated_at = datetime.now()

        # 处理取消相关字段
        if new_status == AppointmentStatus.CANCELLED:
            self.cancelled_at = datetime.now()
            self.cancelled_by = cancelled_by
            self.cancel_reason = cancel_reason

        # 处理完成相关字段
        if new_status == AppointmentStatus.COMPLETED:
            self.completed_at = datetime.now()

        return True


# ---------------- 体检报告表 ----------------
class PhysicalExam(db.Model):
    __tablename__ = 'physical_exam'

    exam_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    heart_rate = db.Column(db.Integer)  # 心率（次/分钟）
    respiratory_rate = db.Column(db.Integer)  # 呼吸频率（次/分钟）
    blood_pressure_systolic = db.Column(db.Integer)  # 收缩压
    blood_pressure_diastolic = db.Column(db.Integer)  # 舒张压
    temperature = db.Column(db.Float)  # 体温（℃）
    weight = db.Column(db.Float)  # 体重（kg）
    height = db.Column(db.Float)  # 身高（cm）
    exam_date = db.Column(db.DateTime, default=datetime.now)


# ---------------- 脑部CT扫描记录表 ----------------
class BrainCTScan(db.Model):
    __tablename__ = 'brain_ct_scan'

    scan_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    scan_date = db.Column(db.DateTime, default=datetime.now)  # 扫描日期时间
    scan_type = db.Column(db.Enum('平扫', '增强', '全脑灌注'))  # CT扫描类型
    technician = db.Column(db.String(50))  # 技术员
    radiologist = db.Column(db.String(50))  # 放射科医师
    scan_reason = db.Column(db.Text)  # 扫描原因

    # CT结果数据
    brain_structure = db.Column(db.Text)  # 脑结构形态描述
    ventricle_status = db.Column(db.Text)  # 脑室状态
    skull_condition = db.Column(db.Text)  # 颅骨状况
    lesion_description = db.Column(db.Text)  # 病变描述
    hemorrhage_status = db.Column(db.Text)  # 出血状态
    ischemia_status = db.Column(db.Text)  # 缺血情况
    atrophy_status = db.Column(db.Text)  # 萎缩情况
    density_abnormalities = db.Column(db.Text)  # 密度异常
    image_path = db.Column(db.String(255))  # CT图像路径
    conclusion = db.Column(db.Text)  # 诊断结论
    follow_up_recommended = db.Column(db.Boolean, default=False)  # 是否建议随访

    # 建立与随访记录的关系
    follow_ups = db.relationship('CTFollowUp', backref='original_scan', lazy=True)


# ---------------- CT随访记录表 ----------------
class CTFollowUp(db.Model):
    __tablename__ = 'ct_follow_up'

    follow_up_id = db.Column(db.Integer, primary_key=True)
    original_scan_id = db.Column(db.Integer, db.ForeignKey('brain_ct_scan.scan_id'), nullable=False)
    follow_up_date = db.Column(db.Date)  # 随访日期
    comparison_results = db.Column(db.Text)  # 与原始扫描比较结果
    disease_progression = db.Column(db.Text)  # 疾病进展情况
    treatment_response = db.Column(db.Text)  # 治疗反应
    next_follow_up = db.Column(db.Date)  # 下次随访日期


# ---------------- 神经系统评估表 ----------------
class NeurologicalAssessment(db.Model):
    __tablename__ = 'neurological_assessment'

    assessment_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.now)
    # 神经功能评估
    motor_function = db.Column(db.Text)  # 运动功能
    sensory_function = db.Column(db.Text)  # 感觉功能
    reflex_status = db.Column(db.Text)  # 反射状态
    coordination = db.Column(db.Text)  # 协调性
    cranial_nerve_exam = db.Column(db.Text)  # 脑神经检查
    gcs_score = db.Column(db.Integer)  # 格拉斯哥昏迷评分(GCS)

    # 认知评估
    mmse_score = db.Column(db.Integer)  # 简易精神状态检查(MMSE)分数
    moca_score = db.Column(db.Integer)  # 蒙特利尔认知评估(MoCA)分数

    assessment_notes = db.Column(db.Text)  # 评估备注
    performed_by = db.Column(db.String(50))  # 评估医师


# ---------------- 药物治疗记录表 ----------------
class MedicationRecord(db.Model):
    __tablename__ = 'medication_record'

    record_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    medication_name = db.Column(db.String(100))  # 药物名称
    dosage = db.Column(db.String(50))  # 用药剂量
    frequency = db.Column(db.String(50))  # 用药频率
    administration_route = db.Column(db.String(50))  # 给药途径
    start_date = db.Column(db.Date)  # 开始用药时间
    end_date = db.Column(db.Date)  # 结束用药时间
    indication = db.Column(db.Text)  # 用药指征
    side_effects = db.Column(db.Text)  # 副作用记录
    effectiveness = db.Column(db.Text)  # 药效评估
    notes = db.Column(db.Text)  # 用药说明或备注


# ---------------- 心理健康评估表 ----------------
class MentalHealth(db.Model):
    __tablename__ = 'mental_health'

    mental_id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patient.patient_id'), nullable=False)
    assessment_date = db.Column(db.Date, default=date.today)
    status_summary = db.Column(db.Text)  # 心理状态总结
    anxiety_level = db.Column(db.Integer)  # 焦虑程度(1-10)
    depression_level = db.Column(db.Integer)  # 抑郁程度(1-10)
    sleep_quality = db.Column(db.Text)  # 睡眠质量描述
    recommended_action = db.Column(db.Text)  # 建议措施


# ---------------- 系统日志表 ----------------
class SystemLog(db.Model):
    __tablename__ = 'system_log'

    log_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True)  # 关联用户ID，允许为空（系统操作）
    username = db.Column(db.String(50))  # 用户名
    operation = db.Column(db.String(20))  # 操作类型：login, logout, create, update, delete, backup, restore
    description = db.Column(db.Text)  # 操作描述
    ip = db.Column(db.String(50))  # IP地址
    create_time = db.Column(db.DateTime, default=datetime.now)  # 创建时间

    # 关联用户
    user = db.relationship('User', backref=db.backref('logs', lazy=True))


# ---------------- 系统配置表 ----------------
class SystemConfig(db.Model):
    __tablename__ = 'system_config'

    config_id = db.Column(db.Integer, primary_key=True)
    system_name = db.Column(db.String(100), default='医疗影像平台')  # 系统名称
    system_description = db.Column(db.Text)  # 系统描述
    system_logo = db.Column(db.String(255))  # 系统Logo路径
    system_version = db.Column(db.String(20))  # 系统版本
    system_status = db.Column(db.Boolean, default=True)  # 系统状态：开启或关闭
    update_time = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)  # 更新时间


# ---------------- 消息通知表 ----------------
class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)

    # Recipient
    receiver_type = db.Column(db.Enum('patient', 'doctor', 'admin'), nullable=False)
    receiver_id = db.Column(db.Integer, nullable=False, index=True)

    # Sender (optional)
    sender_type = db.Column(db.Enum('user', 'system'), nullable=True, default='system')
    sender_id = db.Column(db.Integer, nullable=True)  # Could be a user_id for 'user' sender_type

    # Content
    type = db.Column(db.Enum(NotificationType), default=NotificationType.GENERAL, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

    # Metadata
    related_id = db.Column(db.Integer, nullable=True)        # 关联ID（如预约ID、聊天ID等）
    action_url = db.Column(db.String(255), nullable=True)    # 点击通知跳转的URL
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now, index=True)
    priority = db.Column(db.Integer, default=0)              # 优先级：0普通，1重要，2紧急
    status = db.Column(db.String(20), default='active')      # 状态：active, archived, deleted


# ---------------- 主程序入口 ----------------
# 用以测试数据库或添加数据
if __name__ == '__main__':
    from sqlalchemy import text, inspect
    from flask import Flask
    import pymysql
    import sys

    app = Flask(__name__)

    # 交互式选择数据库连接
    print("\n===== 数据库表操作工具 =====")
    print("请选择要连接的数据库:")
    print("1. 本地数据库 (localhost:3306)")
    print("2. 远程Sealos数据库 (dbconn.sealosbja.site:37152)")

    while True:
        db_choice = input("请输入选项 (1/2): ").strip()
        if db_choice in ['1', '2']:
            break
        print("无效选项，请重新输入")

    # 根据选择设置数据库连接
    if db_choice == '2':
        print("\n使用远程Sealos数据库连接...")
        conf = DB_CONFIG['remote']
        app.config['SQLALCHEMY_DATABASE_URI'] = get_sqlalchemy_uri('remote')
    else:
        print("\n使用本地数据库连接...")
        conf = DB_CONFIG['local']
        app.config['SQLALCHEMY_DATABASE_URI'] = get_sqlalchemy_uri('local')
    # 从配置获取连接参数，供后续数据库操作使用
    db_host = conf['host']
    db_port = conf['port']
    db_user = conf['user']
    db_password = conf['password']
    db_name = conf['database']
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    def check_table_structures():
        """检查关键表的结构"""
        # 根据选择使用对应的连接信息
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )

        cursor = connection.cursor()

        try:
            # 获取所有表
            cursor.execute('SHOW TABLES;')
            tables = [table[0] for table in cursor.fetchall()]
            print(f'\n数据库中的表 ({len(tables)}): {", ".join(tables)}')

            # 检查特定表的结构
            tables_to_check = ['appointment', 'doctor_patient_relation', 'user', 'patient', 'chat_message']

            for table in tables_to_check:
                if table in tables:
                    print(f'\n【{table}表字段】')
                    cursor.execute(f'DESCRIBE {table};')
                    fields = cursor.fetchall()
                    for field in fields:
                        field_name = field[0]
                        field_type = field[1]
                        nullable = "NULL" if field[2] == "YES" else "NOT NULL"
                        print(f'  • {field_name}: {field_type} {nullable}')
                else:
                    print(f'\n【{table}】表不存在')

        except Exception as e:
            print(f'检查表失败: {e}')
        finally:
            cursor.close()
            connection.close()

    def drop_all_tables():
        """删除所有表并重建"""
        connection = pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )

        cursor = connection.cursor()

        try:
            # 禁用外键约束
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

            # 获取所有表
            cursor.execute('SHOW TABLES;')
            tables = [table[0] for table in cursor.fetchall()]

            # 删除所有表
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table};")
                print(f"  • 已删除表: {table}")

            # 重新启用外键约束
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            connection.commit()

            print("\n所有表已成功删除")

        except Exception as e:
            print(f'删除表失败: {e}')
        finally:
            cursor.close()
            connection.close()

    def get_missing_tables():
        """获取缺失的表列表"""
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()

        # 获取预期表列表 (手动定义，确保包括所有模型)
        expected_tables = [
            'user', 'patient', 'doctor_patient_relation', 'medical_history',
            'appointment', 'physical_exam', 'brain_ct_scan', 'ct_follow_up',
            'neurological_assessment', 'medication_record', 'mental_health',
            'imaging_report', 'chat_session', 'chat_message',
            'system_log', 'system_config', 'notification'
        ]

        missing_tables = [table for table in expected_tables if table not in existing_tables]
        return missing_tables

    # 主程序流程
    with app.app_context():
        try:
            # 测试数据库连接
            db.session.execute(text('SELECT 1'))
            print(' 数据库连接成功！')

            # 选择操作
            print("\n请选择操作:")
            print("1. 只查看表结构配置")
            print("2. 删除所有表并重新创建")
            print("3. 仅创建缺失的表")
            print("4. 退出程序")

            while True:
                operation = input("\n请输入选项 (1/2/3/4): ").strip()
                if operation in ['1', '2', '3', '4']:
                    break
                print("无效选项，请重新输入")

            if operation == '1':
                # 只查看表结构
                print("\n查看表结构...")
                check_table_structures()

            elif operation == '2':
                # 删除所有表并重建
                confirm = input("\n警告: 此操作将删除所有表和数据! 确认继续? (y/n): ").lower()
                if confirm == 'y':
                    print("\n开始删除所有表...")
                    drop_all_tables()

                    print("\n开始创建新表...")
                    db.create_all()
                    print("所有表已重新创建成功")

                    # 查看新建表结构
                    check_table_structures()
                else:
                    print("操作已取消")

            elif operation == '3':
                # 只创建缺失的表
                missing_tables = get_missing_tables()

                if missing_tables:
                    print(f"\n发现以下缺失的表 ({len(missing_tables)}): {', '.join(missing_tables)}")
                    confirm = input("是否创建这些缺失的表? (y/n): ").lower()

                    if confirm == 'y':
                        print("\n开始创建缺失的表...")
                        db.create_all()
                        print("缺失的表已创建成功")

                        # 再次检查是否所有表都已创建
                        new_missing = get_missing_tables()
                        if new_missing:
                            print(f"\n警告: 以下表仍然缺失: {', '.join(new_missing)}")
                        else:
                            print("\n所有预期表已经创建完成")
                    else:
                        print("操作已取消")
                else:
                    print("\n数据库中已包含所有预期的表，无需创建新表")

            elif operation == '4':
                print("\n程序已退出")
                sys.exit(0)

        except Exception as e:
            print(f' 数据库操作失败：{e}')


class PageVisit(db.Model):
    __tablename__ = 'page_visit'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True)
    endpoint = db.Column(db.String(128))
    ip = db.Column(db.String(45))
    visited_at = db.Column(db.DateTime, default=datetime.now)
    # 关联用户
    user = db.relationship('User', backref=db.backref('page_visits', lazy=True))
