# ============================================================
# Import & Setup
# ============================================================
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
import os, uuid, traceback, logging
from datetime import date, datetime
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
from app.hr.routes import hr_bp
from app import db
from app.models import (
    Employee, Attendance, ActivityLog, Client,
    Assignment, EmployeePersonalDetail
)
from app.role_check import role_required

employee_bp = Blueprint("employee", __name__)

# ============================================================
# 🔒 Validasi Employee untuk setiap Request
# ============================================================
def ensure_employee_exists(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        emp = Employee.query.filter_by(user_id=current_user.id).first()
        if not emp:
            flash("⚠️ Akun ini tidak memiliki data karyawan.", "warning")
            return redirect(url_for("auth.logout"))
        return func(*args, **kwargs)
    return wrapper


@employee_bp.route("/employee/check")
def employee_check():
    return "✅ Blueprint employee_bp aktif."


# ============================================================
# 👤 EMPLOYEE SELF DASHBOARD
# ============================================================
@employee_bp.route("/dashboard_employee", methods=["GET", "POST"])
@login_required
@role_required("employee")
@ensure_employee_exists
def dashboard_employee():
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    today = date.today()

    attendance_today = Attendance.query.filter_by(
        employee_id=employee.id, date=today
    ).first()

    return render_template(
        "employee/dashboard_employee.html",
        employee=employee,
        today=today,
        attendance_today=attendance_today,
    )


# ============================================================
# 📝 UPLOAD AKTIVITAS HARIAN (foto + lokasi)
# ============================================================
@employee_bp.route("/upload_activity", methods=["POST"])
@login_required
@role_required("employee")
@ensure_employee_exists
def upload_activity():
    try:
        employee = Employee.query.filter_by(user_id=current_user.id).first()

        description = request.form.get("description")
        latitude_val = request.form.get("latitude")
        longitude_val = request.form.get("longitude")

        # helper konversi aman ke float
        def safe_float(val):
            try:
                return float(val) if val not in (None, "", "null") else None
            except ValueError:
                return None

        latitude = safe_float(latitude_val)
        longitude = safe_float(longitude_val)

        file = request.files.get("photo")
        stored_path = None
        if file and file.filename:
            upload_folder = os.path.join(current_app.root_path, "static", "uploads")
            os.makedirs(upload_folder, exist_ok=True)
            ext = file.filename.rsplit(".", 1)[1].lower()
            if ext in {"jpg", "jpeg", "png"}:
                filename = secure_filename(f"{uuid.uuid4()}.{ext}")
                file.save(os.path.join(upload_folder, filename))
                stored_path = f"uploads/{filename}"
            else:
                flash("⚠️ Format foto tidak diperbolehkan (hanya JPG/PNG).", "warning")

        new_log = ActivityLog(
            employee_id=employee.id,
            description=description,
            latitude=latitude,
            longitude=longitude,
            image=stored_path,
            created_at=datetime.now(),
        )
        db.session.add(new_log)
        db.session.commit()
        flash("✅ Aktivitas harian berhasil disimpan.", "success")

    except Exception as e:
        db.session.rollback()
        traceback.print_exc()
        flash(f"🚨 Terjadi kesalahan saat menyimpan aktivitas: {e}", "danger")

    return redirect(url_for("employee.dashboard_employee"))


# ============================================================
# ⏱️ ABSENSI (Clock In / Clock Out)
# ============================================================
@employee_bp.route("/do_attendance", methods=["POST"])
@login_required
@role_required("employee")
@ensure_employee_exists
def do_attendance():
    today = date.today()
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    action = request.form.get("action")
    current_time = datetime.now().time()

    attendance = Attendance.query.filter_by(
        employee_id=employee.id, date=today
    ).first()

    if not attendance:
        attendance = Attendance(employee_id=employee.id, date=today, status="hadir")
        db.session.add(attendance)
        db.session.commit()

    if action == "clock_in" and not attendance.check_in:
        attendance.check_in = current_time
        flash("✅ Absen masuk berhasil!", "success")

    elif action == "clock_out" and not attendance.check_out:
        attendance.check_out = current_time
        flash("👋 Absen pulang berhasil!", "info")

    db.session.commit()
    return redirect(url_for("employee.dashboard_employee"))



@login_required
@role_required('admin', 'hr')
def edit_employee(id):
    """Edit seluruh data karyawan + personal detail dengan konversi aman tipe data."""
    from datetime import datetime  # pastikan import ada di atas file

    employee = Employee.query.get_or_404(id)
    clients = Client.query.all()

    # pastikan relasi personal_detail tersedia
    if not employee.personal_detail:
        employee.personal_detail = EmployeePersonalDetail(employee_id=id)
        db.session.add(employee.personal_detail)
        db.session.flush()

    if request.method == 'POST':
        pd = employee.personal_detail

        # ==================================================
        # A. DATA UTAMA EMPLOYEE
        # ==================================================
        employee.name      = request.form.get('name')
        employee.position  = request.form.get('position')
        employee.job_type  = request.form.get('job_type')
        employee.status    = request.form.get('status')
        employee.client_id = request.form.get('client_id')

        # ==================================================
        # B. IDENTITAS DIRI (konversi sesuai tipe kolom)
        # ==================================================
        pd.nik          = request.form.get('nik')
        pd.full_name    = employee.name
        pd.nickname     = request.form.get('nama_panggilan')
        pd.gender       = request.form.get('jenis_kelamin')
        pd.birth_place  = request.form.get('tempat_lahir')

        # konversi tanggal lahir
        birth_str = request.form.get('tanggal_lahir')
        if birth_str:
            try:
                pd.birth_date = datetime.strptime(birth_str, "%Y-%m-%d").date()
            except ValueError:
                pd.birth_date = None
        else:
            pd.birth_date = None

        pd.address_ktp     = request.form.get('alamat_ktp')
        pd.address_current = request.form.get('alamat_sekarang')
        pd.education       = request.form.get('pendidikan')
        pd.last_job        = request.form.get('pekerjaan_terakhir')
        pd.blood_type      = request.form.get('gol_darah')

        # pastikan angka tersimpan sebagai integer
        pd.height_cm    = int(request.form.get('tinggi_badan') or 0)
        pd.weight_kg    = int(request.form.get('berat_badan') or 0)
        pd.shirt_size   = request.form.get('ukuran_kemeja')
        pd.shoe_size    = int(request.form.get('ukuran_sepatu') or 0)

        # ==================================================
        # C. STATUS KELUARGA
        # ==================================================
        pd.marital_status = request.form.get('status_pernikahan')
        pd.spouse_name    = request.form.get('nama_pasangan')
        pd.spouse_job     = request.form.get('pekerjaan_pasangan')
        pd.num_children   = int(request.form.get('jumlah_anak') or 0)

        # ==================================================
        # D. ASURANSI
        # ==================================================
        pd.bpjs_ketenagakerjaan = request.form.get('bpjs_ket')
        pd.bpjs_kesehatan       = request.form.get('bpjs_kes')
        pd.bpjs_kis             = request.form.get('bpjs_kis')
        pd.jamkesda             = request.form.get('jamkesda')

        # ==================================================
        # E. KONTAK DARURAT
        # ==================================================
        pd.emergency_contact_name = request.form.get('emergency_nama')
        pd.emergency_phone        = request.form.get('emergency_hp')
        pd.emergency_relation     = request.form.get('emergency_hubungan')
        pd.emergency_address      = request.form.get('emergency_alamat')

        # ==================================================
        # F. FOTO PROFIL
        # ==================================================
        file_photo = request.files.get('photo')
        if file_photo and allowed_file(file_photo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = file_photo.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file_photo.save(os.path.join(UPLOAD_FOLDER, filename))
            employee.photo = filename

        # ==================================================
        # G. DOKUMEN TAMBAHAN
        # ==================================================
        doc_fields = {"ktp": "KTP", "ijazah": "Ijazah"}
        for field_name, label in doc_fields.items():
            file_doc = request.files.get(field_name)
            if file_doc and allowed_file(file_doc.filename):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                ext = file_doc.filename.rsplit('.', 1)[1].lower()
                fname = f"{uuid.uuid4().hex}.{ext}"
                file_doc.save(os.path.join(UPLOAD_FOLDER, fname))
                new_doc = EmployeeDocument(
                    employee_id=employee.id,
                    document_type=label,
                    file_path=f"uploads/{fname}",
                )
                db.session.add(new_doc)

        # ==================================================
        # H. SIMPAN PERUBAHAN
        # ==================================================
        db.session.commit()
        flash(f"✅ Data lengkap {employee.name} berhasil diperbarui!", "success")

        # Setelah simpan, kembali ke halaman detail agar bisa langsung terlihat hasilnya
        return redirect(url_for('hr.employee_details', id=id))

    # jika GET → tampilkan form edit
    return render_template('hr/edit_employee.html', employee=employee, clients=clients)

# ============================================================
# Logging & Registrasi Route HR
# ============================================================
logging.basicConfig(level=logging.INFO)
logging.info("✅ employee/routes.py loaded successfully")

# --------------- PERBAIKAN RINGAN --------------------
# Daftarkan route edit_employee ke HR blueprint dengan aman
# Hanya dijalankan setelah semua blueprint selesai dimuat
def _register_hr_route_late(app=None):
    try:
        # Flask akan memanggil fungsi after_app_request setelah app siap
        if app is None:
            from flask import current_app
            app = current_app
        if app and not any(
            getattr(f, "__name__", "") == "edit_employee" for f in hr_bp.deferred_functions
        ):
            hr_bp.add_url_rule(
                '/employees/edit/<int:id>',
                view_func=edit_employee,
                methods=['GET', 'POST']
            )
            logging.info("✅ edit_employee route berhasil ditautkan ke hr_bp")
    except Exception as e:
        logging.error(f"⚠️ Gagal menautkan route HR secara manual: {e}")

# daftar penundaan setelah Flask app dibuat
try:
    from flask import current_app
    if current_app:
        _register_hr_route_late(current_app)
except Exception:
    pass
# ------------------------------------------------------