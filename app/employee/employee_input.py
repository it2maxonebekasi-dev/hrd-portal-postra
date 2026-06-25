    import os, uuid, traceback
    from datetime import datetime
    from flask import Blueprint, render_template, request, redirect, url_for, flash
    from flask_login import login_required, current_user
    from werkzeug.utils import secure_filename
    from app.models import db, Employee, EmployeeDocument, EmployeePersonalDetail
    from app.role_check import role_required   # ✅ untuk batasi akses HR/Admin

    employee_input_bp = Blueprint('employee_input_bp', __name__)

    UPLOAD_FOLDER = 'app/static/uploads'
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def to_int(value):
        try:
            return int(value) if value else None
        except (ValueError, TypeError):
            return None


    # ===============================================================
    # 🔹 TAMBAH DATA KARYAWAN BARU (HR/Admin)
    # ===============================================================
    @employee_input_bp.route('/add', methods=['GET', 'POST'])
    @login_required
    @role_required('admin', 'hr')
    def add_employee():
        try:
            if request.method == 'POST':
                nama = request.form.get('nama_lengkap') or "Tanpa Nama"

                posisi = 'Baru'
                jenis_pekerjaan = 'Belum Ditentukan'

                new_employee = Employee(
                    name=nama,
                    position=posisi,
                    job_type=jenis_pekerjaan
                )
                db.session.add(new_employee)
                db.session.flush()

                tanggal_str = request.form.get('tanggal_lahir')
                tgl_lahir = None
                if tanggal_str:
                    try:
                        tgl_lahir = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
                    except ValueError:
                        flash("⚠️ Format tanggal salah, diabaikan.", "warning")

                detail = EmployeePersonalDetail(
                    employee_id=new_employee.id,
                    nik=request.form.get('nik'),
                    full_name=nama,
                    gender=request.form.get('jenis_kelamin'),
                    birth_place=request.form.get('tempat_lahir'),
                    birth_date=tgl_lahir,
                    address_ktp=request.form.get('alamat_ktp'),
                    address_current=request.form.get('alamat_sekarang'),
                    education=request.form.get('pendidikan'),
                    last_job=request.form.get('pekerjaan_terakhir'),
                )
                db.session.add(detail)

                os.makedirs(UPLOAD_FOLDER, exist_ok=True)
                for key in ('ijazah', 'ktp', 'foto'):
                    file = request.files.get(key)
                    if file and allowed_file(file.filename):
                        filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
                        file.save(os.path.join(UPLOAD_FOLDER, filename))
                        doc = EmployeeDocument(
                            employee_id=new_employee.id,
                            document_type=key.upper(),
                            file_path=f"static/uploads/{filename}"
                        )
                        db.session.add(doc)

                db.session.commit()
                flash("✅ Data karyawan berhasil disimpan!", "success")
                return redirect(url_for('employee_input_bp.view_employee', emp_id=new_employee.id))

        except Exception as e:
            db.session.rollback()
            traceback.print_exc()
            flash(f"Terjadi kesalahan saat simpan: {e}", "danger")

        return render_template('employee/form_input.html')


    # ===============================================================
    # 👁️ LIHAT DATA KARYAWAN
    # ===============================================================
    @employee_input_bp.route('/view/<int:emp_id>')
    @login_required
    @role_required('admin', 'hr')
    def view_employee(emp_id):
        emp = Employee.query.get_or_404(emp_id)
        detail = emp.personal_detail
        docs = emp.documents
        return render_template('employee/view_employee.html',
                            employee=emp, detail=detail, docs=docs)


    # ===============================================================
    # 📋 DAFTAR SELURUH KARYAWAN
    # ===============================================================
    @employee_input_bp.route('/list')
    @login_required
    @role_required('admin', 'hr')
    def list_employees():
        employees = Employee.query.join(EmployeePersonalDetail).all()
        return render_template('employee/list_employees.html', employees=employees)