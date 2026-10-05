from typing import Optional
from sqlalchemy.orm import Session

from tracker.models.ai_insight import AIInsight, InsightScope, InsightPeriod


class AIInsightRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, insight: AIInsight) -> AIInsight:
        self.db.add(insight)
        self.db.commit()
        self.db.refresh(insight)
        return insight

    def get_latest_for_user(self, user_id: int, period: InsightPeriod = InsightPeriod.weekly) -> Optional[AIInsight]:
        return (
            self.db.query(AIInsight)
            .filter(
                AIInsight.scope == InsightScope.individual,
                AIInsight.user_id == user_id,
                AIInsight.period == period,
            )
            .order_by(AIInsight.generated_at.desc())
            .first()
        )

    def get_latest_for_group(self, group_id: int, period: InsightPeriod = InsightPeriod.weekly) -> Optional[AIInsight]:
        return (
            self.db.query(AIInsight)
            .filter(
                AIInsight.scope == InsightScope.group,
                AIInsight.group_id == group_id,
                AIInsight.period == period,
            )
            .order_by(AIInsight.generated_at.desc())
            .first()
        )
