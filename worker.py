#!/usr/bin/env python3
import time
from datetime import datetime, date, timedelta
try:
    import pytz
except Exception:
    from datetime import timezone as _timezone
    class pytz:
        class timezone:
            def __init__(self, *a, **k): pass
            def localize(self, dt):
                return dt.replace(tzinfo=__import__('datetime').timezone.utc)
            def __call__(self):
                return __import__('datetime').timezone.utc


from database import SessionLocal
from tracker.models.group import Group
from tracker.models.group_checkin_settings import GroupCheckinSettings
from tracker.models.membership import Membership
from tracker.models.checkin import Checkin
from tracker.models.sent_reminder import SentReminder
from tracker.models.notification import Notification
from tracker.services.notification_service import NotificationService


DAYS = ['mon','tue','wed','thu','fri','sat','sun']


def run_once():
    db = SessionLocal()
    try:
        groups = db.query(Group).filter(Group.is_archived == False).all()
        for g in groups:
            s = db.query(GroupCheckinSettings).filter(GroupCheckinSettings.group_id == g.id).first()
            if not s or not s.enabled or not s.deadline_at:
                continue
            tz = pytz.timezone(s.timezone or 'Africa/Nairobi')
            now = datetime.now(tz)
            today = now.date()
            wd = DAYS[now.weekday()]
            days = (s.days_of_week or 'mon,tue,wed,thu,fri').split(',')
            if wd not in [d.strip() for d in days]:
                continue
            if db.query(SentReminder).filter_by(group_id=g.id, reminder_date=today, reminder_type='SUMMARY').first():
                continue
            deadline_dt = tz.localize(datetime.combine(today, s.deadline_at))
            if now >= deadline_dt + timedelta(minutes=2):
                members = db.query(Membership).filter(Membership.group_id == g.id).all()
                submitted = set()
                for c in db.query(Checkin).filter(Checkin.group_id == g.id, Checkin.period_date == today).all():
                    submitted.add(c.user_id)
                not_submitted = []
                for m in members:
                    if m.user_id not in submitted:
                        not_submitted.append(m.user_id)
                lines = []
                lines.append(f"CHECK-IN SUMMARY — {today.strftime('%A, %d %B %Y')}")
                lines.append(f"Submitted: {len(submitted)}   |   Not submitted: {len(not_submitted)}")
                if not_submitted and s.list_missed_publicly:
                    lines.append("\nDid not check in")
                    for i, uid in enumerate(not_submitted, 1):
                        from tracker.models.user import User
                        u = db.query(User).get(uid)
                        lines.append(f"{i}. {u.name if u else uid}")
                msg = "\n".join(lines)
                ns = NotificationService(db)
                for m in members:
                    ns.notify(m.user_id, "Check-in summary", msg, type="checkin", group_id=g.id)
                db.add(SentReminder(group_id=g.id, reminder_date=today, reminder_type='SUMMARY'))
                db.commit()
    finally:
        db.close()


if __name__ == '__main__':
    while True:
        try:
            run_once()
        except Exception as e:
            print(e)
        time.sleep(300)
