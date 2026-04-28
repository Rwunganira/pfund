from app import app
with app.app_context():
    from models import User
    users = User.query.all()
    if not users:
        print("NO USERS FOUND")
    for u in users:
        print(f"id={u.id} username={u.username} email={u.email} confirmed={u.confirmed} role={u.role}")
