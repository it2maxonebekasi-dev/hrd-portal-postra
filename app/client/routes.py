from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import date
from app.models import Client, Assignment, Attendance
from app.role_check import role_required

# ==========================================================
# 🏢  DASHBOARD KHUSUS CLIENT
# ==========================================================
client_bp = Blueprint("client", __name__)

# ==========================================================
# 📊 DASHBOARD CLIENT (Role = client)
# ==========================================================
@client_bp.route("/dashboard", methods=["GET"])
@login_required
@role_required("client")
def dashboard_client():
    """
    Dashboard khusus akun client.
    Menampilkan daftar karyawan yang bekerja di perusahaan mereka
    beserta status kehadiran harian.
    """
    client = Client.query.filter_by(user_id=current_user.id).first_or_404()

    # Assignment aktif → karyawan yang sedang bekerja untuk client ini
    assignments = Assignment.query.filter_by(client_id=client.id, status="aktif").all()

    # Kehadiran hari ini
    attendance_today = {
        a.employee_id: a for a in Attendance.query.filter_by(date=date.today()).all()
    }

    return render_template(
        "client/dashboard_client.html",
        client=client,
        assignments=assignments,
        attendance_today=attendance_today,
        today=date.today(),
    )