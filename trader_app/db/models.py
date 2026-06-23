import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.orm import foreign

from .database import Base


def uuid_text():
    return str(uuid.uuid4())


class TimestampMixin:
    uuid = Column(String(36), unique=True, nullable=False, default=uuid_text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("plan IN ('trial', 'basic', 'pro', 'vip')", name="ck_users_plan"),
        CheckConstraint("trade_type IN ('spot', 'futures')", name="ck_users_trade_type"),
        CheckConstraint("spot_enabled IN (0, 1) AND futures_enabled IN (0, 1)", name="ck_users_type_flags"),
        Index("ix_users_email", "email"),
        Index("ix_users_plan_paid", "plan", "is_paid"),
        Index("ix_users_referral_code", "referral_code"),
        Index("ix_users_chat_id", "chat_id"),
    )

    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True, nullable=False)
    password = Column(Text, nullable=False)
    chat_id = Column(Text, unique=False, nullable=True)
    is_paid = Column(Integer, nullable=False, default=0)
    plan = Column(Text, nullable=False, default="trial")
    trial_start = Column(Text)
    trades = Column(Integer, nullable=False, default=0)
    expiry = Column(Text)
    api_key = Column(Text)
    api_secret = Column(Text)
    profit = Column(Float, nullable=False, default=0)
    trade_amount = Column(Float, nullable=False, default=10)
    trade_type = Column(Text, nullable=False, default="futures")
    spot_enabled = Column(Integer, nullable=False, default=1)
    futures_enabled = Column(Integer, nullable=False, default=1)
    bot_active = Column(Integer, nullable=False, default=0)
    referral_code = Column(Text)
    referred_by = Column(Text)
    affiliate_balance = Column(Float, nullable=False, default=0)
    total_referrals = Column(Integer, nullable=False, default=0)
    free_basic_unlocked = Column(Integer, nullable=False, default=0)
    free_pro_unlocked = Column(Integer, nullable=False, default=0)
    free_vip_unlocked = Column(Integer, nullable=False, default=0)
    is_admin = Column(Integer, nullable=False, default=0)
    lifetime_owner = Column(Integer, nullable=False, default=0)
    email_verified = Column(Integer, nullable=False, default=0)
    email_verification_token = Column(Text)
    email_verification_sent_at = Column(Text)
    password_reset_token = Column(Text)
    password_reset_expires_at = Column(Text)

    referrals = relationship("AffiliateReferral", primaryjoin=lambda: User.chat_id == foreign(AffiliateReferral.referrer_chat_id), viewonly=True)
    commissions = relationship("AffiliateCommission", primaryjoin=lambda: User.chat_id == foreign(AffiliateCommission.referrer_chat_id), viewonly=True)
    withdrawals = relationship("AffiliateWithdrawal", primaryjoin=lambda: User.chat_id == foreign(AffiliateWithdrawal.chat_id), viewonly=True)


class AffiliateReferral(Base, TimestampMixin):
    __tablename__ = "affiliate_referrals"
    __table_args__ = (
        Index("ix_affiliate_referrals_referrer", "referrer_chat_id"),
        Index("ix_affiliate_referrals_referred", "referred_chat_id"),
    )

    id = Column(Integer, primary_key=True)
    referrer_chat_id = Column(Text)
    referred_chat_id = Column(Text)
    referred_email = Column(Text)


class AffiliateCommission(Base, TimestampMixin):
    __tablename__ = "affiliate_commissions"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_affiliate_commissions_amount_nonnegative"),
        Index("ix_affiliate_commissions_referrer", "referrer_chat_id"),
        Index("ix_affiliate_commissions_status", "status"),
    )

    id = Column(Integer, primary_key=True)
    referrer_chat_id = Column(Text)
    referred_chat_id = Column(Text)
    plan = Column(Text)
    payment_id = Column(Text, index=True)
    amount = Column(Float, nullable=False, default=0)
    status = Column(Text, nullable=False, default="approved")



class AffiliateWithdrawal(Base, TimestampMixin):
    __tablename__ = "affiliate_withdrawals"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_affiliate_withdrawals_amount_positive"),
        CheckConstraint("status IN ('pending', 'paid', 'rejected')", name="ck_affiliate_withdrawals_status"),
        Index("ix_affiliate_withdrawals_chat_status", "chat_id", "status"),
    )

    id = Column(Integer, primary_key=True)
    chat_id = Column(Text)
    wallet_address = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(Text, nullable=False, default="pending")



class TelegramReferral(Base, TimestampMixin):
    __tablename__ = "telegram_referrals"

    telegram_id = Column(Text, primary_key=True)
    referral_code = Column(Text, index=True)


class ProcessedPayment(Base, TimestampMixin):
    __tablename__ = "processed_payments"
    __table_args__ = (
        Index("ix_processed_payments_order_id", "order_id"),
        Index("ix_processed_payments_invoice_id", "invoice_id"),
    )

    payment_id = Column(Text, primary_key=True)
    order_id = Column(Text, index=True)
    payment_status = Column(Text)
    plan = Column(Text)
    amount = Column(Float, nullable=False, default=0)
    currency = Column(Text, nullable=False, default="usd")
    invoice_id = Column(Text)
    invoice_url = Column(Text)
    raw_payload = Column(Text)


class PaymentInvoice(Base, TimestampMixin):
    __tablename__ = "payment_invoices"
    __table_args__ = (
        CheckConstraint("amount >= 0 AND original_amount >= 0 AND discount_amount >= 0", name="ck_payment_invoices_amount_nonnegative"),
        Index("ix_payment_invoices_chat_created", "chat_id", "created_at"),
        Index("ix_payment_invoices_status", "status"),
        Index("ix_payment_invoices_invoice_id", "invoice_id"),
    )

    id = Column(Integer, primary_key=True)
    invoice_id = Column(Text)
    payment_id = Column(Text)
    chat_id = Column(Text)
    email = Column(Text)
    plan = Column(Text)
    status = Column(Text, nullable=False, default="created")
    amount = Column(Float, nullable=False, default=0)
    original_amount = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)
    currency = Column(Text, nullable=False, default="usd")
    coupon_code = Column(Text)
    invoice_url = Column(Text)
    raw_response = Column(Text)
    paid_at = Column(DateTime(timezone=True), nullable=True)


class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 95", name="ck_coupons_discount_range"),
        CheckConstraint("active IN (0, 1)", name="ck_coupons_active_flag"),
        Index("ix_coupons_code", "code"),
    )

    id = Column(Integer, primary_key=True)
    code = Column(Text, unique=True, nullable=False)
    discount_percent = Column(Float, nullable=False, default=0)
    active = Column(Integer, nullable=False, default=1)
    expires_at = Column(Text)
    max_redemptions = Column(Integer)
    redemption_count = Column(Integer, nullable=False, default=0)


class FailedPayment(Base, TimestampMixin):
    __tablename__ = "failed_payments"
    __table_args__ = (Index("ix_failed_payments_created", "created_at"),)

    id = Column(Integer, primary_key=True)
    payment_id = Column(Text)
    invoice_id = Column(Text)
    order_id = Column(Text)
    plan = Column(Text)
    payment_status = Column(Text)
    reason = Column(Text)
    raw_payload = Column(Text)


class SubscriptionRenewal(Base, TimestampMixin):
    __tablename__ = "subscription_renewals"
    __table_args__ = (Index("ix_subscription_renewals_chat_created", "chat_id", "created_at"),)

    id = Column(Integer, primary_key=True)
    chat_id = Column(Text)
    email = Column(Text)
    plan = Column(Text)
    payment_id = Column(Text)
    previous_expiry = Column(Text)
    new_expiry = Column(Text)
    amount = Column(Float, nullable=False, default=0)
    renewal_type = Column(Text, nullable=False, default="new")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_email_created", "email", "created_at"),
        Index("ix_audit_logs_action_created", "action", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(String(36), unique=True, nullable=False, default=uuid_text)
    action = Column(Text, index=True)
    email = Column(Text, index=True)
    ip_address = Column(Text)
    details = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
