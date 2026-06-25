import os, uuid
import csv
import io
import random
import string
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, current_app, jsonify
from flask_login import login_required
from sqlalchemy import desc, extract, func
from app.models import Employee, Client, Attendance, Assignment, User, ActivityLog, EmployeePersonalDetail, EmployeeDocument
from app import db
from app.role_check import role_required
from xhtml2pdf import pisa

# ============================================================
# 🔧 KONFIGURASI BLUEPRINT
# ============================================================
hr_bp = Blueprint('hr', __name__)

UPLOAD_FOLDER = os.path.join('app', 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ============================================================
# ✳️  KELOLA KARYAWAN
# ============================================================
@hr_bp.route('/employees', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def manage_employees():
    clients = Client.query.all()

    if request.method == 'POST':
        name = request.form.get('name')
        position = request.form.get('position')
        job_type = request.form.get('job_type')
        client_id = request.form.get('client_id')
        file = request.files.get('photo')

        # --- LOGIKA BARU: Generate Akun Otomatis ---
        clean_name = name.split()[0].lower().replace(" ", "")
        random_digits = ''.join(random.choices(string.digits, k=3))
        username = f"{clean_name}{random_digits}"

        chars = string.ascii_letters + string.digits
        generated_password = ''.join(random.choices(chars, k=8))

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash(f"⚠️ Username '{username}' kebetulan sudah terpakai. Silakan coba Submit ulang.", "warning")
            return redirect(url_for('hr.manage_employees'))

        new_user = User(username=username, role='employee', active=True)
        new_user.set_password(generated_password)
        db.session.add(new_user)
        db.session.flush()

        filename = 'default_user.png'
        if file and allowed_file(file.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file.save(os.path.join(UPLOAD_FOLDER, filename))

        new_employee = Employee(
            name=name,
            position=position,
            job_type=job_type,
            client_id=client_id,
            join_date=date.today(),
            status='aktif',
            photo=filename,
            user_id=new_user.id
        )
        db.session.add(new_employee)
        db.session.flush()

        if client_id:
            new_assignment = Assignment(
                employee_id=new_employee.id,
                client_id=client_id,
                start_date=date.today(),
                status='aktif'
            )
            db.session.add(new_assignment)

        new_pd = EmployeePersonalDetail(employee_id=new_employee.id)
        db.session.add(new_pd)

        db.session.commit()
        
        flash(
            f"✅ Data karyawan '{name}' berhasil disimpan!<br>"
            f"---------------------------------------<br>"
            f"👤 Username: <b>{username}</b><br>"
            f"🔑 Password: <b>{generated_password}</b><br>"
            f"---------------------------------------<br>"
            f"Harap catat informasi login ini.",
            "success"
        )

        return redirect(url_for('hr.employee_details', id=new_employee.id))

    employees = Employee.query.order_by(Employee.id.desc()).all()
    return render_template('hr/employee_cards.html', employees=employees, clients=clients)


# ============================================================
# ✏️  EDIT DATA KARYAWAN
# ============================================================
@hr_bp.route('/employees/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    clients = Client.query.all()

    if not employee.personal_detail:
        employee.personal_detail = EmployeePersonalDetail(employee_id=id)
        db.session.add(employee.personal_detail)
        db.session.flush()

    if request.method == 'POST':
        pd = employee.personal_detail

        employee.name      = request.form.get('name')
        employee.position  = request.form.get('position')
        employee.job_type  = request.form.get('job_type')
        employee.status    = request.form.get('status')
        employee.client_id = request.form.get('client_id')

        pd.nik             = request.form.get('nik')
        pd.full_name       = employee.name
        pd.nickname        = request.form.get('nama_panggilan')
        pd.gender          = request.form.get('jenis_kelamin')
        pd.birth_place     = request.form.get('tempat_lahir')

        birth_str = request.form.get('tanggal_lahir')
        if birth_str:
            try:
                pd.birth_date = datetime.strptime(birth_str, '%Y-%m-%d').date()
            except ValueError:
                pd.birth_date = None
        else:
            pd.birth_date = None

        pd.address_ktp     = request.form.get('alamat_ktp')
        pd.address_current = request.form.get('alamat_sekarang')
        pd.education       = request.form.get('pendidikan')
        pd.last_job        = request.form.get('pekerjaan_terakhir')
        pd.blood_type      = request.form.get('gol_darah')
        pd.height_cm       = request.form.get('tinggi_badan')
        pd.weight_kg       = request.form.get('berat_badan')
        pd.shirt_size      = request.form.get('ukuran_kemeja')
        pd.shoe_size       = request.form.get('ukuran_sepatu')

        pd.marital_status  = request.form.get('status_pernikahan')
        pd.spouse_name     = request.form.get('nama_pasangan')
        pd.spouse_job      = request.form.get('pekerjaan_pasangan')
        pd.num_children    = request.form.get('jumlah_anak') or 0

        pd.bpjs_ketenagakerjaan = request.form.get('bpjs_ket')
        pd.bpjs_kesehatan       = request.form.get('bpjs_kes')
        pd.bpjs_kis             = request.form.get('bpjs_kis')
        pd.jamkesda             = request.form.get('jamkesda')

        pd.emergency_contact_name = request.form.get('emergency_nama')
        pd.emergency_phone        = request.form.get('emergency_hp')
        pd.emergency_relation     = request.form.get('emergency_hubungan')
        pd.emergency_address      = request.form.get('emergency_alamat')

        file_photo = request.files.get('photo')
        if file_photo and allowed_file(file_photo.filename):
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            ext = file_photo.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            file_photo.save(os.path.join(UPLOAD_FOLDER, filename))
            employee.photo = filename

        doc_fields = {"ktp": "KTP", "ijazah": "Ijazah"}
        for field_name, label in doc_fields.items():
            file_doc = request.files.get(field_name)
            if file_doc and allowed_file(file_doc.filename):
                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                ext = file_doc.filename.rsplit('.', 1)[1].lower()
                fname = f"{uuid.uuid4().hex}.{ext}"
                path = os.path.join(UPLOAD_FOLDER, fname)
                file_doc.save(path)
                new_doc = EmployeeDocument(
                    employee_id=employee.id,
                    document_type=label,
                    file_path=f"uploads/{fname}",
                )
                db.session.add(new_doc)

        db.session.commit()
        flash(f"✅ Data lengkap {employee.name} berhasil diperbarui!", "success")
        return redirect(url_for('hr.employee_details', id=id))

    return render_template('hr/edit_employee.html', employee=employee, clients=clients)


# ============================================================
# 👁️  DETAIL KARYAWAN
# ============================================================
@hr_bp.route('/employees/<int:id>/details')
@login_required
@role_required('admin', 'hr')
def employee_details(id):
    employee = (
        db.session.query(Employee)
        .filter_by(id=id)
        .options(
            db.joinedload(Employee.personal_detail),
            db.joinedload(Employee.documents),
            db.joinedload(Employee.client)
        )
        .first_or_404()
    )
    
    db.session.refresh(employee)

    attendance_records = (
        Attendance.query.filter_by(employee_id=id)
        .order_by(Attendance.date.desc())
        .limit(30).all()
    )
    work_logs = (
        ActivityLog.query.filter_by(employee_id=id)
        .order_by(ActivityLog.created_at.desc())
        .limit(20).all()
    )

    return render_template(
        "hr/employee_details.html",
        employee=employee,
        attendance_records=attendance_records,
        work_logs=work_logs,
    )

# ============================================================
# 🖨️  EXPORT DATA DIRI PDF (STYLE BANK/PROFESIONAL)
# ============================================================
@hr_bp.route('/employees/<int:id>/print_pdf')
@login_required
@role_required('admin', 'hr')
def print_employee_pdf(id):
    employee = Employee.query.get_or_404(id)
    
    if not employee.personal_detail:
        employee.personal_detail = EmployeePersonalDetail(employee_id=id)
        db.session.add(employee.personal_detail)

    photo_path = None
    if employee.photo and employee.photo != 'default_user.png':
        photo_path = os.path.join(current_app.root_path, 'static', 'uploads', employee.photo)
    
    html = render_template(
        'hr/pdf_bank_style.html', 
        employee=employee, 
        now=datetime.now(),
        photo_path=photo_path
    )

    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)

    if not pdf.err:
        response = make_response(result.getvalue())
        filename = f"Biodata_{employee.name.replace(' ', '_')}.pdf"
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename={filename}'
        return response
    
    flash("Gagal membuat PDF.", "danger")
    return redirect(url_for('hr.employee_details', id=id))

# ============================================================
# 🔐 RESET PASSWORD KARYAWAN
# ============================================================
@hr_bp.route('/employees/<int:id>/reset_password', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def reset_password(id):
    employee = Employee.query.get_or_404(id)
    
    if not employee.user:
        clean_name = employee.name.split()[0].lower().replace(" ", "")
        random_digits = ''.join(random.choices(string.digits, k=3))
        username = f"{clean_name}{random_digits}"
        
        new_user = User(username=username, role='employee', active=True)
        db.session.add(new_user)
        db.session.flush()
        employee.user_id = new_user.id
    
    chars = string.ascii_letters + string.digits
    new_password = ''.join(random.choices(chars, k=8))

    employee.user.set_password(new_password)
    db.session.commit()

    flash(
        f"🔄 Password untuk <b>{employee.name}</b> berhasil di-reset!<br>"
        f"---------------------------------------<br>"
        f"👤 Username: <b>{employee.user.username}</b><br>"
        f"🔑 Password Baru: <b>{new_password}</b><br>"
        f"---------------------------------------<br>"
        f"Segera berikan password ini ke karyawan.",
        "warning"
    )

    return redirect(url_for('hr.employee_details', id=id))


# ============================================================
# 🕒  DASHBOARD ABSENSI UMUM
# ============================================================
@hr_bp.route('/attendance')
@login_required
@role_required('admin', 'hr')
def attendance_dashboard():
    today = date.today()
    employees = Employee.query.join(Client).add_entity(Client).filter(Employee.status == 'aktif').all()
    attendance_today = {
        a.employee_id: a for a in Attendance.query.filter_by(date=today).all()
    }

    total_employee = len(employees)
    hadir = len([a for a in attendance_today.values() if a.status == 'hadir'])
    sakit = len([a for a in attendance_today.values() if a.status == 'sakit'])
    izin = len([a for a in attendance_today.values() if a.status == 'izin'])
    alfa = total_employee - (hadir + sakit + izin)

    return render_template(
        'hr/attendance_dashboard.html',
        today=today,
        total_employee=total_employee,
        hadir=hadir,
        sakit=sakit,
        izin=izin,
        alfa=alfa,
        employees=employees,
        attendance_today=attendance_today
    )


# ============================================================
# 🕓  HALAMAN ABSENSI PERSONAL
# ============================================================
@hr_bp.route('/attendance/<int:employee_id>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def employee_attendance_page(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    today = date.today() # <--- Variabel ini PENTING
    attendance = Attendance.query.filter_by(employee_id=employee_id, date=today).first()

    if request.method == 'POST':
        action = request.form.get('action')
        current_time = datetime.now().time()

        if not attendance:
            attendance = Attendance(employee_id=employee_id, date=today, status='hadir')
            db.session.add(attendance)

        if action == 'clock_in':
            if not attendance.check_in:
                attendance.check_in = current_time
                attendance.status = 'hadir'
                flash('✅ Absen masuk berhasil diinput!', 'success')
            else:
                flash('⚠️ Karyawan ini sudah absen masuk sebelumnya.', 'warning')
                
        elif action == 'clock_out':
            if not attendance.check_out:
                attendance.check_out = current_time
                flash('👋 Absen pulang berhasil diinput!', 'info')
            else:
                flash('⚠️ Karyawan ini sudah absen pulang sebelumnya.', 'warning')

        db.session.commit()
        return redirect(url_for('hr.employee_attendance_page', employee_id=employee_id))

    activity_logs = ActivityLog.query.filter_by(employee_id=employee_id).filter(
        db.func.date(ActivityLog.created_at) == today
    ).all()

    return render_template(
        'hr/employee_attendance_page.html',
        employee=employee,
        attendance=attendance,
        activity_logs=activity_logs,
        today=today # <--- INI YANG MENYELESAIKAN ERROR JINJA2
    )

# ============================================================
# 🚚  DASHBOARD OPERASIONAL
# ============================================================
@hr_bp.route('/operation')
@login_required
@role_required('admin', 'hr')
def operation_dashboard():
    today = date.today()

    active_employees = Employee.query.filter(Employee.status == 'aktif').all()
    attendance_today = {
        a.employee_id: a for a in Attendance.query.filter_by(date=today).all()
    }
    activities_today = ActivityLog.query.filter(
        db.func.date(ActivityLog.created_at) == today
    ).order_by(ActivityLog.employee_id).all()

    logs_grouped = {}
    for act in activities_today:
        logs_grouped.setdefault(act.employee_id, []).append(act)

    return render_template(
        'hr/operation_dashboard.html',
        employees=active_employees,
        attendance_today=attendance_today,
        logs_grouped=logs_grouped,
        today=today
    )


# ============================================================
# 📥  EXPORT LAPORAN BULANAN (EXCEL/CSV)
# ============================================================
@hr_bp.route('/export/monthly_report')
@login_required
@role_required('admin', 'hr')
def export_monthly_report():
    now = datetime.now()
    current_month = now.month
    current_year = now.year

    attendances = Attendance.query.filter(
        extract('month', Attendance.date) == current_month,
        extract('year', Attendance.date) == current_year
    ).order_by(Attendance.date.desc()).all()

    si = io.StringIO()
    cw = csv.writer(si)
    
    cw.writerow(['Tanggal', 'Nama Karyawan', 'Posisi', 'Client', 'Jam Masuk', 'Jam Pulang', 'Status'])

    for att in attendances:
        emp_name = att.employee.name if att.employee else "Deleted User"
        emp_pos = att.employee.position if att.employee else "-"
        client = att.employee.client.name if (att.employee and att.employee.client) else "-"
        cin = att.check_in.strftime('%H:%M') if att.check_in else "-"
        cout = att.check_out.strftime('%H:%M') if att.check_out else "-"
        
        cw.writerow([
            att.date.strftime('%d-%m-%Y'),
            emp_name,
            emp_pos,
            client,
            cin,
            cout,
            att.status.upper()
        ])

    output = make_response(si.getvalue())
    filename = f"Laporan_Absensi_{now.strftime('%B_%Y')}.csv"
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output


# ============================================================
# 🗑️  HAPUS DATA KARYAWAN
# ============================================================
@hr_bp.route('/employees/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def delete_employee(id):
    emp = Employee.query.get_or_404(id)
    name = emp.name
    
    try:
        if emp.user:
            db.session.delete(emp.user) 

        db.session.delete(emp)
        
        db.session.commit()
        flash(f"🗑️ Data personil {name} beserta seluruh riwayatnya berhasil dihapus permanen.", "info")
    except Exception as e:
        db.session.rollback()
        flash(f"❌ Gagal menghapus data: {str(e)}", "danger")
        
    return redirect(url_for('hr.manage_employees'))


# ============================================================
# 👤 DETAIL OPERASIONAL
# ============================================================
@hr_bp.route('/operation/<int:employee_id>', methods=['GET'])
@login_required
@role_required('admin', 'hr')
def operation_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        if start_date:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Format tanggal tidak valid.", "warning")
        return redirect(url_for('hr.operation_dashboard'))

    query = Attendance.query.filter_by(employee_id=employee_id).order_by(Attendance.date.desc())
    if start_date and end_date:
        query = query.filter(Attendance.date.between(start_date, end_date))
    elif start_date:
        query = query.filter(Attendance.date >= start_date)
    elif end_date:
        query = query.filter(Attendance.date <= end_date)
    attendance_history = query.all()

    logs_query = ActivityLog.query.filter_by(employee_id=employee_id)
    if start_date and end_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at).between(start_date, end_date))
    elif start_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at) >= start_date)
    elif end_date:
        logs_query = logs_query.filter(db.func.date(ActivityLog.created_at) <= end_date)
    work_logs = logs_query.order_by(ActivityLog.created_at.desc()).all()

    return render_template(
        'hr/operation_detail.html',
        employee=employee,
        attendance_history=attendance_history,
        work_logs=work_logs,
        start_date=start_date,
        end_date=end_date,
        today=date.today() 
    )


# ============================================================
# 🧾  KELOLA CLIENT
# ============================================================
@hr_bp.route('/clients', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'hr')
def manage_clients():
    if request.method == 'POST':
        name = request.form.get('name')
        address = request.form.get('address')
        contact_person = request.form.get('contact_person')
        phone = request.form.get('phone')

        username = name.lower().replace(" ", "_")
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("⚠️ Username client sudah ada. Ganti nama perusahaan.", "warning")
            return redirect(url_for('hr.manage_clients'))

        user = User(username=username, role='client', active=True)
        user.set_password('client123')
        db.session.add(user)
        db.session.flush()

        new_client = Client(
            name=name,
            address=address,
            contact_person=contact_person,
            phone=phone,
            user_id=user.id
        )
        db.session.add(new_client)
        db.session.commit()
        flash(f"✅ Client '{name}' berhasil ditambahkan! Akun login: {username}", "success")
        return redirect(url_for('hr.manage_clients'))

    clients = Client.query.order_by(Client.name.asc()).all()
    return render_template('hr/manage_clients.html', clients=clients)


# ============================================================
# 🗑️  HAPUS CLIENT
# ============================================================
@hr_bp.route('/clients/delete/<int:id>', methods=['POST'])
@login_required
@role_required('admin', 'hr')
def delete_client(id):
    client = Client.query.get_or_404(id)
    if client.user_id:
        user = User.query.get(client.user_id)
        if user: db.session.delete(user)

    db.session.delete(client)
    db.session.commit()
    flash(f"🗑️ Mitra {client.name} berhasil dihapus.", "info")
    return redirect(url_for('hr.manage_clients'))

# ============================================================
# 🔗 API: GET KARYAWAN BY JOB TYPE (Untuk Chart Click)
# ============================================================
@hr_bp.route('/api/employees/by_job/<path:job_type>')
@login_required
def get_employees_by_job(job_type):
    """Mengembalikan JSON data karyawan berdasarkan job_type untuk Modal Dashboard"""
    
    employees = Employee.query.filter(
        func.lower(Employee.job_type) == job_type.lower(),
        Employee.status == 'aktif'
    ).all()
    
    data = []
    for emp in employees:
        data.append({
            'name': emp.name,
            'position': emp.position,
            'client': emp.client.name if emp.client else '-',
            'join_date': emp.join_date.strftime('%d-%m-%Y') if emp.join_date else '-',
            'photo': url_for('static', filename='uploads/' + emp.photo) if emp.photo else url_for('static', filename='uploads/default_user.png')
        })
        
    return jsonify(data)

# ============================================================
# 📊  DASHBOARD HR UTAMA
# ============================================================
@hr_bp.route('/dashboard')
@login_required
@role_required('admin', 'hr')
def hr_dashboard():
    today = date.today()

    total_employees = Employee.query.count()
    active_employees = Employee.query.filter_by(status='aktif').count()
    total_clients = Client.query.count()
    total_assignments = Assignment.query.filter_by(status='aktif').count()
    
    hadir_hari_ini = Attendance.query.filter_by(date=today, status='hadir').count()

    job_labels = []
    job_counts = []
    job_data = (
        db.session.query(Employee.job_type, db.func.count(Employee.id))
        .group_by(Employee.job_type)
        .all()
    )
    for label, count in job_data:
        job_labels.append((label or "Lainnya").capitalize())
        job_counts.append(count)

    client_labels = []
    client_counts = []
    client_stats = (
        db.session.query(Client.name, db.func.count(Assignment.id))
        .join(Assignment, Assignment.client_id == Client.id)
        .filter(Assignment.status == 'aktif')
        .group_by(Client.name)
        .all()
    )
    for cname, ccount in client_stats:
        client_labels.append(cname)
        client_counts.append(ccount)

    return render_template(
        'hr/dashboard_hr.html',
        total_employees=total_employees,
        active_employees=active_employees,
        total_clients=total_clients,
        total_assignments=total_assignments,
        hadir_hari_ini=hadir_hari_ini, 
        job_labels=job_labels,
        job_counts=job_counts,
        client_labels=client_labels,
        client_counts=client_counts,
        today=today
    )