from functools import wraps
from flask import redirect, url_for, flash
from flask_login import current_user


def role_required(*roles):
    """
    Batasi akses berdasarkan role.
    Gunakan misalnya:
        @role_required('admin')
        @role_required('employee', 'hr')
    Admin dan HR punya akses penuh ke semua halaman.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # 🔹 Belum login
            if not current_user.is_authenticated:
                flash("Silakan login terlebih dahulu.", "warning")
                return redirect(url_for("auth.login"))

            # 🔹 Admin & HR punya izin global akses semua fitur
            if current_user.role in ("admin", "hr"):
                return f(*args, **kwargs)

            # 🔹 Jika role user tidak termasuk dalam roles yang diizinkan
            if current_user.role not in roles:
                flash("🚫 Anda tidak memiliki izin untuk mengakses halaman ini.", "danger")

                # Arahkan ke dashboard sesuai role
                if current_user.role == "employee":
                    return redirect(url_for("employee.dashboard_employee"))
                elif current_user.role == "client":
                    return redirect(url_for("client.dashboard_client"))
                elif current_user.role == "admin":
                    return redirect(url_for("admin.dashboard_admin"))
                elif current_user.role == "hr":
                    return redirect(url_for("hr.dashboard_hr"))
                else:
                    return redirect(url_for("auth.login"))

            # 🔹 Jika role diizinkan, lanjut ke fungsi aslinya
            return f(*args, **kwargs)
        return wrapper
    return decorator