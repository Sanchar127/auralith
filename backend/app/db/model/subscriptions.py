from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubscriptionDuration(Base):
    __tablename__ = "subscription_durations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    name: Mapped[str] = mapped_column(String(50), unique=True)  # "Monthly", "Quarterly", etc.
    duration_months: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), 
        default=Decimal('0.00')
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Relationship
    plans = relationship("SubscriptionPlan", back_populates="duration")


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    monthly_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    context_window: Mapped[int] = mapped_column(
        Integer,
        default=128000,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    
    # Foreign key to duration
    duration_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("subscription_durations.id"),
        nullable=False,
    )
    
    # Relationships
    duration = relationship("SubscriptionDuration", back_populates="plans")
    subscriptions = relationship(
        "UserSubscription",
        back_populates="plan",
    )
    
    # Optional: Add unique constraint to prevent duplicate plans
    __table_args__ = (
        UniqueConstraint('name', 'duration_id', name='uq_plan_name_duration'),
    )
    
    @property
    def duration_months(self) -> int:
        """Get duration in months from the related duration object"""
        return self.duration.duration_months if self.duration else 0
    
    @property
    def monthly_effective_price(self) -> Decimal:
        """Calculate effective monthly price"""
        if self.duration_months > 0:
            return self.price / self.duration_months
        return self.price
    
    @property
    def savings_percentage(self) -> Decimal:
        """Calculate savings compared to monthly plan"""
        if self.duration_months > 1:
            # Assuming monthly plan price is base price / duration_months
            monthly_total = self.price / self.duration_months * self.duration_months
            if monthly_total > 0:
                savings = ((monthly_total - self.price) / monthly_total) * 100
                return Decimal(str(round(savings, 2)))
        return Decimal('0.00')
    
    @property
    def duration_label(self) -> str:
        """Get human-readable duration label"""
        return self.duration.name if self.duration else "Unknown"
    
    def __repr__(self) -> str:
        return f"<SubscriptionPlan {self.name} ({self.duration_label})>"