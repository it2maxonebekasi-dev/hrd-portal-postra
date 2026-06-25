from flask import Blueprint, render_template
from flask_login import login_required

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin')
@login_required
def dashboard_admin():
    return render_template('admin/dashboard_admin.html')