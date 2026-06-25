from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User
# ✅ Import Form
from app.auth.forms import LoginForm 

# ======================================================
# 🔐 Blueprint AUTH – Login & Logout
# ======================================================
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ------------------------------------------------------
# 🔑 LOGIN PAGE
# ------------------------------------------------------
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, langsung arahkan sesuai role
    if current_user.is_authenticated:
        return redirect_user_by_role(current_user)

    form = LoginForm()

    # --- [DEBUG LOG] ---
    # Akan muncul di Log Render jika tombol login ditekan
    if request.method == 'POST':
        print(f"🔍 [DEBUG] Percobaan Login dari IP: {request.remote_addr}")

    # ✅ Validasi Form (Cek CSRF & Kelengkapan Data)
    if form.validate_on_submit():
        
        username = form.username.data.strip()
        password = form.password.data.strip()

        print(f"🔍 [DEBUG] Mencari user: '{username}' di database...")

        user = User.query.filter_by(username=username).first()

        # --- LOGIKA PENGECEKAN ---
        if not user:
            print(f"❌ [DEBUG] User '{username}' TIDAK DITEMUKAN.")
            flash('❌ Username tidak ditemukan.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.check_password(password):
            print(f"❌ [DEBUG] Password SALAH untuk user '{username}'.")
            flash('❌ Password salah.', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.active:
            print(f"⚠️ [DEBUG] Akun '{username}' tidak aktif.")
            flash('⚠️ Akun ini tidak aktif.', 'warning')
            return render_template('auth/login.html', form=form)

        # --- JIKA SUKSES ---
        print(f"✅ [DEBUG] Login SUKSES untuk: {username}")
        login_user(user) 
        flash(f'✅ Selamat datang, {user.username}!', 'success')
        
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        
        return redirect_user_by_role(user)

    # --- [DEBUG KHUSUS] JIKA VALIDASI GAGAL ---
    # Ini bagian paling penting untuk melihat kenapa login mental
    if form.errors:
        print(f"⚠️ [DEBUG] FORM ERROR: {form.errors}")
        # Biasanya errornya: {'csrf_token': ['The CSRF token is missing.']}
        
        for err in form.errors.values():
            flash(f'⚠️ {err[0]}', 'danger')

    return render_template('auth/login.html', form=form)


# ------------------------------------------------------
# 🚪 LOGOUT
# ------------------------------------------------------
@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('👋 Anda telah logout.', 'info')
    return redirect(url_for('auth.login'))


# ------------------------------------------------------
# 🔄 Fungsi bantu untuk redirect berdasar ROLE
# ------------------------------------------------------
def redirect_user_by_role(user):
    """Arahkan user ke dashboard sesuai role-nya."""
    if user.role == 'admin':
        return redirect(url_for('admin.dashboard_admin'))
    elif user.role == 'hr':
        return redirect(url_for('hr.dashboard_hr'))
    elif user.role == 'client':
        return redirect(url_for('client.dashboard_client'))
    elif user.role == 'employee':
        return redirect(url_for('employee.dashboard_employee'))
    else:
        flash('⚠️ Role pengguna tidak dikenali.', 'warning')
        return redirect(url_for('auth.login'))