from datetime import datetime
from sqlalchemy.orm import Session
from tracker.models.notification import Notification


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def notify(self, user_id: int, title: str, message: str, type: str = "info", group_id: int = None, link: str = None):
        n = Notification(user_id=user_id, group_id=group_id, type=type, title=title, message=message, link=link)
        self.db.add(n)
        self.db.commit()
        self.db.refresh(n)
        return n

    def notify_group(self, group_id: int, user_ids: list, title: str, message: str, type: str = "info", link: str = None):
        for uid in set(user_ids):
            try:
                self.db.add(Notification(user_id=uid, group_id=group_id, type=type, title=title, message=message, link=link))
            except Exception:
                pass
        self.db.commit()
