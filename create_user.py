from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    # Cek user admin sudah ada atau belum
    admin = User.query.filter_by(username="admin").first()
    
    if admin:
        # Update password yang sudah ada
        admin.set_password("112233")
        db.session.commit()
        print("✅ Password admin berhasil diupdate: username=admin, password=112233")
    else:
        # Buat user baru jika belum ada
        admin = User(username="admin", role="admin", active=True)
        admin.set_password("112233")
        db.session.add(admin)
        db.session.commit()
        print("✅ User admin berhasil dibuat: username=admin, password=112233")
    
    # Tampilkan semua user yang ada
    all_users = User.query.all()
    print("\n📋 Daftar user yang ada:")
    for user in all_users:
        print(f"  - {user.username} (role: {user.role})")
