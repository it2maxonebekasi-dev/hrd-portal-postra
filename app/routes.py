# ==============================================================
#  app/routes.py – Blueprint utama untuk Dashboard HR Portal
# ==============================================================

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from sqlalchemy import func, literal
from app.models import Employee, Client, Assignment, Attendance, User

# 🔹 Inisialisasi Blueprint utama
main_bp = Blueprint('main', __name__)

# -------------------------------------------------------------
# 🏠  DASHBOARD UTAMA
# -------------------------------------------------------------
@main_bp.route('/')
@login_required
def dashboard():
    """Dashboard utama dengan visualisasi data lintas modul."""
    from app import db
    today = date.today()

    # ---- Angka ringkasan utama ----
    try:
        total_employees = Employee.query.count()
        active_employees = Employee.query.filter_by(status='aktif').count()
        total_clients = Client.query.count()
        total_assignments = Assignment.query.filter_by(status='aktif').count()
        total_karyawan = User.query.filter_by(role='employee').count()

        # ============================================================
        # JUMLAH HADIR HARI INI
        # ============================================================
        hadir_hari_ini = Attendance.query.filter(
            Attendance.date == today,
            func.trim(func.lower(Attendance.status)) == literal('hadir')
        ).count()

        # ============================================================
        # GRAFIK 1 — STATUS KARYAWAN (tabel Employee)
        # ============================================================
        emp_status = (
            db.session.query(Employee.status, func.count(Employee.id))
            .group_by(Employee.status)
            .all()
        )
        status_labels = [s[0].capitalize() for s in emp_status] if emp_status else []
        status_counts = [s[1] for s in emp_status] if emp_status else []

        # ============================================================
        # GRAFIK 2 — ABSENSI HARI INI (tabel Attendance)
        # ============================================================
        att_labels = ['Hadir', 'Izin', 'Sakit', 'Alpha']
        att_counts = [
            Attendance.query.filter(
                Attendance.date == today,
                func.trim(func.lower(Attendance.status)) == literal('hadir')
            ).count(),
            Attendance.query.filter(
                Attendance.date == today,
                func.trim(func.lower(Attendance.status)) == literal('izin')
            ).count(),
            Attendance.query.filter(
                Attendance.date == today,
                func.trim(func.lower(Attendance.status)) == literal('sakit')
            ).count(),
            Attendance.query.filter(
                Attendance.date == today,
                func.trim(func.lower(Attendance.status)) == literal('alpha')
            ).count(),
        ]
    except Exception as e:
        print(f"⚠️ Error loading dashboard data: {e}")
        # Nilai default jika tabel belum ada/error
        total_employees = 0
        active_employees = 0
        total_clients = 0
        total_assignments = 0
        total_karyawan = 0
        hadir_hari_ini = 0
        status_labels = []
        status_counts = []
        att_labels = []
        att_counts = []

    # ------------------------------------------------------------
    # Render template dashboard.html
    # ------------------------------------------------------------
    return render_template(
        'dashboard.html',
        title='Dashboard - HR Portal',
        user=current_user,
        today=today,
        total_employees=total_employees,
        active_employees=active_employees,
        total_clients=total_clients,
        total_assignments=total_assignments,
        total_karyawan=total_karyawan,
        hadir_hari_ini=hadir_hari_ini,
        status_labels=status_labels,
        status_counts=status_counts,
        att_labels=att_labels,
        att_counts=att_counts
    )


# ==============================================================
# 🆘 ROUTE DARURAT: FIX DATABASE (WAJIB ADA DI RENDER + SQLITE)
# ==============================================================
@main_bp.route('/fix-db-manual')
def fix_db_manual():
    """
    Route ini dipanggil manual lewat browser untuk memaksa pembuatan
    tabel dan akun admin jika database terhapus/reset.
    URL: https://namadomain.com/fix-db-manual
    """
    from app import db
    try:
        # 1. Pastikan semua tabel dibuat
        db.create_all()
        
        # 2. Cek apakah admin ada
        admin = User.query.filter_by(username='admin').first()
        
        messages = []
        messages.append("✅ Database Tables Checked/Created.")

        if not admin:
            # Buat Admin Baru
            admin = User(username='admin', role='admin', active=True)
            admin.set_password('admin123') # Password default
            db.session.add(admin)
            messages.append("✅ Akun ADMIN berhasil dibuat ulang (User: admin, Pass: admin123).")
        else:
            # Reset password untuk memastikan bisa login
            admin.set_password('admin123')
            messages.append("ℹ️ Akun ADMIN sudah ada. Password di-reset ke 'admin123'.")

        db.session.commit()
        
        return f"""
        <div style="font-family: sans-serif; text-align: center; padding-top: 50px;">
            <h1 style="color: green;">Perbaikan Database Berhasil!</h1>
            <p>{'<br>'.join(messages)}</p>
            <br>
            <a href="/auth/login" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                Klik Disini Untuk Login
            </a>
        </div>
        """
    
    except Exception as e:
        return f"<h1 style='color:red'>Error: {str(e)}</h1>"