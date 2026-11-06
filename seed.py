from database import SessionLocal, engine, Base
from tracker.models import *
from tracker.services.security import hash_password
from tracker.models.notification import Notification
from tracker.models.checkin import Checkin, PeriodType
from tracker.models.task import Task, TaskStatus
from datetime import date

Base.metadata.create_all(bind=engine)
db = SessionLocal()

try:
    existing = db.query(User).filter(User.email == "admin@trackly.com").first()
    if existing:
        db.delete(existing)
        db.commit()
        print("Removed admin")

    demo = db.query(User).filter(User.email == "demo@trackly.com").first()
    if demo:
        db.delete(demo)
        db.commit()
        print("Removed demo")

    for name, email in [("Samrawit Tiyisak", "samrawittyisakk@gmail.com"), ("Eyerusalem Gebremedhin", "eyerusalemgebremedhin21@gmail.com"), ("Eyerusalem V", "eyerusalemv@gmail.com")]:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(name=name, email=email, hashed_password=hash_password("AhwatPass123!"), skills="", is_verified=True, is_active=True)
            db.add(u); db.commit(); db.refresh(u)
            print(f"Created: {u.email}")
        else:
            print(f"Exists: {u.email}")

    for u in db.query(User).all():
        if not db.query(Notification).filter(Notification.user_id == u.id).first():
            db.add(Notification(user_id=u.id, title="Welcome to Trackly", message="Your account is ready.", type="info"))
    db.commit()

    # Create sample groups
    from tracker.models.group import Group
    from tracker.models.membership import Membership
    lead_user = db.query(User).filter(User.email == "eyerusalemv@gmail.com").first()
    g1 = db.query(Group).filter(Group.name == "Nexa").first()
    if not g1:
        g1 = Group(name="Nexa", description="Demo group", created_by=lead_user.id)
        db.add(g1); db.commit(); db.refresh(g1)
    for u in db.query(User).all():
        if not db.query(Membership).filter(Membership.group_id == g1.id, Membership.user_id == u.id).first():
            role = "lead" if u.email == "eyerusalemv@gmail.com" else "member"
            db.add(Membership(group_id=g1.id, user_id=u.id, role=role))
    db.commit()
    print("Seeded group Nexa")

    lead_user = db.query(User).filter(User.email == "eyerusalemv@gmail.com").first()
    members = db.query(User).all()
    for i, u in enumerate(members[:3]):
        t = Task(title=f"Task {i+1}", description="Demo task", assignee_id=u.id, assigned_by_id=lead_user.id, group_id=g1.id, status=TaskStatus.todo)
        db.add(t)
    db.commit()
    print("Seeded tasks")

    for u in db.query(User).limit(3).all():
        c = Checkin(user_id=u.id, group_id=g1.id, achieved="Demo checkin", period_type=PeriodType.daily, period_date=date.today())
        db.add(c)
    db.commit()
    print("Seeded checkins")
    for name, email in [("Mahlet Hiluf", "mahlethbelete@gmail.com"), ("Eyerusalem Gebremedhin", "eyerusalemv@gmail.com"), ("Eyoba Mulubrhan", "eyobamulubrhan@gmail.com"), ("Helen Mezgebe", "helenmezgebet@gmail.com"), ("Samrawit Yisak", "samrawittyisakk@gmail.com"), ("Ariam Kidanemariam", "ariamkidaneg@gmail.com")]:
        u = db.query(User).filter(User.email == email).first()
        if not u:
            u = User(name=name, email=email, hashed_password=hash_password("AhwatPass123!"), skills="", job_title="Software Engineer", is_verified=True, is_active=True)
            db.add(u); db.commit(); db.refresh(u)
            print(f"Created: {u.email}")
        else:
            u.name = name
            u.job_title = "Software Engineer"
            db.commit()
            print(f"Exists: {u.email}")

    lead_user = db.query(User).filter(User.email == "eyerusalemv@gmail.com").first()
    g2 = db.query(Group).filter(Group.name == "Ahwat").first()
    if not g2:
        g2 = Group(name="Ahwat", description="Demo group", created_by=lead_user.id)
        db.add(g2); db.commit(); db.refresh(g2)
    for u in db.query(User).filter(User.email.in_(["mahlethbelete@gmail.com","eyerusalemv@gmail.com","eyobamulubrhan@gmail.com","helenmezgebet@gmail.com","samrawittyisakk@gmail.com","ariamkidaneg@gmail.com"])).all():
        if not db.query(Membership).filter(Membership.group_id == g2.id, Membership.user_id == u.id).first():
            role = "lead" if u.email == "eyerusalemv@gmail.com" else "member"
            db.add(Membership(group_id=g2.id, user_id=u.id, role=role))
    db.commit()
    checkin_data = {
        "mahlethbelete@gmail.com": ("Build API", "Completed API endpoints", "Fast progress", "Minor bugs", "Refactor", "None"),
        "eyobamulubrhan@gmail.com": ("UI work", "Finished dashboard", "Clean design", "Slow load", "Optimize", "None"),
        "helenmezgebet@gmail.com": ("Testing", "Wrote tests", "Coverage up", "Flaky tests", "Fix tests", "None"),
        "ariamkidaneg@gmail.com": ("Docs", "Updated docs", "Clear docs", "Time", "Add more", "None"),
    }
    for email, (goal, achieved, well, didnt, improve, blocker) in checkin_data.items():
        u = db.query(User).filter(User.email == email).first()
        if u:
            c = Checkin(user_id=u.id, group_id=g2.id, goal=goal, achieved=achieved, went_well=well, didnt_go_well=didnt, improve=improve, blocker=blocker, period_type=PeriodType.daily, period_date=date.today())
            db.add(c)
    db.commit()
    print("Seeded checkins for Ahwat")

    lead_user = db.query(User).filter(User.email == "eyerusalemv@gmail.com").first()
    task_data = {
        "mahlethbelete@gmail.com": "Build API",
        "eyobamulubrhan@gmail.com": "UI work",
        "helenmezgebet@gmail.com": "Testing",
        "ariamkidaneg@gmail.com": "Docs",
    }
    for email, title in task_data.items():
        u = db.query(User).filter(User.email == email).first()
        if u:
            t = Task(title=title, description="Demo task", assignee_id=u.id, assigned_by_id=lead_user.id, group_id=g2.id, status=TaskStatus.todo)
            db.add(t)
    db.commit()
    print("Seeded Ahwat tasks")

finally:
    db.close()
