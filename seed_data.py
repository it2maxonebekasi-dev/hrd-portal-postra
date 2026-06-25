from app import create_app, db
from app.models import Client, Employee, Assignment
from datetime import date

app = create_app()

with app.app_context():
    # Data contoh Client
    c = Client(
        name='PT Bintang Jaya',
        address='Jl. Merdeka No.10',
        contact_person='Budi',
        phone='0812345678'
    )
    db.session.add(c)
    db.session.commit()

    # Data contoh Employee
    e1 = Employee(name='Andi', position='Security', job_type='security', client=c)
    e2 = Employee(name='Rina', position='Cleaner', job_type='cleaning', client=c)
    db.session.add_all([e1, e2])
    db.session.commit()

    # Data contoh Assignment
    a1 = Assignment(employee=e1, client=c, location='Gedung A', shift='pagi', start_date=date.today())
    a2 = Assignment(employee=e2, client=c, location='Gedung B', shift='siang', start_date=date.today())
    db.session.add_all([a1, a2])
    db.session.commit()

    print("✅  Data contoh Employee, Client, dan Assignment berhasil disimpan.")