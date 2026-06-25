from app import db
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


# ============================================================
# 1️⃣ HR DEVELOPMENT — Data Karyawan
# ============================================================
class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    position = db.Column(db.String(100))
    job_type = db.Column(db.String(50))
    join_date = db.Column(db.Date, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default="aktif")
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"))
    photo = db.Column(db.String(255), default="default_user.png")

    # Akun login (relasi ke tabel users)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    user = db.relationship("User", backref="employee_account", uselist=False)

    # Relasi lain (DITAMBAHKAN: cascade="all, delete-orphan")
    # Ini mencegah error "NOT NULL constraint" saat menghapus karyawan
    assignments = db.relationship("Assignment", backref="employee", lazy=True, cascade="all, delete-orphan")
    attendance_records = db.relationship("Attendance", backref="employee", lazy=True, cascade="all, delete-orphan")
    personal_detail = db.relationship("EmployeePersonalDetail", backref="employee", uselist=False, cascade="all, delete-orphan")
    documents = db.relationship("EmployeeDocument", backref="employee", lazy=True, cascade="all, delete-orphan")
    activity_log = db.relationship("ActivityLog", backref="employee", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Employee {self.name} ({self.job_type})>"


# ============================================================
# 2️⃣ CLIENT — Perusahaan pengguna jasa
# ============================================================
class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    address = db.Column(db.String(255))
    contact_person = db.Column(db.String(100))
    phone = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    user = db.relationship("User", back_populates="client_account")

    # Client jarang dihapus, tapi jika dihapus, kontrak/karyawan/assignment ikut terhapus
    contracts = db.relationship("Contract", backref="client", lazy=True, cascade="all, delete-orphan")
    employees = db.relationship("Employee", backref="client", lazy=True) # Karyawan tidak dihapus, hanya client_id jadi NULL (default)
    assignments = db.relationship("Assignment", backref="client", lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Client {self.name}>"


# ============================================================
# 3️⃣ CONTRACT — Hubungan kerja sama
# ============================================================
class Contract(db.Model):
    __tablename__ = "contracts"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    value = db.Column(db.Float)
    status = db.Column(db.String(20), default="aktif")

    def __repr__(self):
        return f"<Contract Client={self.client_id} Value={self.value}>"


# ============================================================
# 4️⃣ ATTENDANCE — Kehadiran
# ============================================================
class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    date = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20))
    check_in = db.Column(db.Time)
    check_out = db.Column(db.Time)
    overtime_hours = db.Column(db.Float, default=0.0)

    def __repr__(self):
        return f"<Attendance Emp={self.employee_id} {self.date} {self.status}>"


# ============================================================
# 5️⃣ ASSIGNMENT — Penugasan
# ============================================================
class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    location = db.Column(db.String(150))
    shift = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="aktif")

    def __repr__(self):
        return f"<Assignment Emp={self.employee_id} Loc={self.location}>"


# ============================================================
# 6️⃣ USER — Akun login
# ============================================================
class User(db.Model, UserMixin):
    id: int
    username: str
    role: str
    active: bool
    password_hash: str

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False, default="")
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True)

    client_account = db.relationship("Client", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


# ============================================================
# 7️⃣ ACTIVITY LOG — Aktivitas pekerjaan harian
# ============================================================
class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    description = db.Column(db.Text)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    image = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ActivityLog Emp={self.employee_id} Desc={self.description[:10]}>"


# ============================================================
# 8️⃣ EMPLOYEE PERSONAL DETAIL — Data pribadi karyawan
# ============================================================
class EmployeePersonalDetail(db.Model):
    __tablename__ = "employee_personal_details"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False, unique=True)

    # ===== Identitas Diri =====
    nik = db.Column(db.String(50))
    full_name = db.Column(db.String(150))
    nickname = db.Column(db.String(100))
    gender = db.Column(db.String(10))
    birth_place = db.Column(db.String(100))
    birth_date = db.Column(db.Date)
    address_ktp = db.Column(db.Text)
    address_current = db.Column(db.Text)
    education = db.Column(db.String(50))
    last_job = db.Column(db.String(150))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    blood_type = db.Column(db.String(5))
    height_cm = db.Column(db.Integer)
    weight_kg = db.Column(db.Integer)
    shirt_size = db.Column(db.String(5))
    shoe_size = db.Column(db.Integer)

    # ===== Status Keluarga =====
    marital_status = db.Column(db.String(20))
    spouse_name = db.Column(db.String(150))
    spouse_job = db.Column(db.String(150))
    num_children = db.Column(db.Integer, default=0)

    # ===== Asuransi (BPJS dsb.) =====
    bpjs_ketenagakerjaan = db.Column(db.String(50))
    bpjs_kesehatan = db.Column(db.String(50))
    bpjs_kis = db.Column(db.String(50))
    jamkesda = db.Column(db.String(50))

    # ===== Orang Tua / Saudara =====
    parents_name = db.Column(db.String(150))
    parents_address = db.Column(db.Text)
    num_siblings = db.Column(db.Integer)
    note_health = db.Column(db.Text)

    # ===== Kontak Darurat =====
    emergency_contact_name = db.Column(db.String(150))
    emergency_phone = db.Column(db.String(50))
    emergency_relation = db.Column(db.String(100))
    emergency_address = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmployeePersonalDetail EmpID={self.employee_id}>"


# ============================================================
# 9️⃣ EMPLOYEE DOCUMENT — Dokumen pribadi (PDF, foto, dll)
# ============================================================
class EmployeeDocument(db.Model):
    __tablename__ = "employee_documents"

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id"), nullable=False)
    document_type = db.Column(db.String(100))
    file_path = db.Column(db.String(255))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EmployeeDocument Emp={self.employee_id} {self.document_type}>"