import enum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.db.database import Base


class TransactionStatus(str, enum.Enum):
    PARSED = "parsed"  # Raw from email, needs categorization attempt
    NEEDS_REVIEW = "needs_review"  # Agent couldn't auto-resolve, waiting for user
    CATEGORIZED = "categorized"  # Successfully tagged


class User(Base):
    """
    Multi-tenant boundary table.
    The `id` here MUST strictly map to the Kinde JWT `sub` (Subject).
    """

    __tablename__ = "users"
    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    telegram_chat_id = Column(String, unique=True, index=True, nullable=True)  # Linked via bot /start trick
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class LLMConfig(Base):
    """BYO-LLM feature configuration per user."""

    __tablename__ = "llm_configs"
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    provider = Column(String, nullable=False)  # e.g., 'openai', 'anthropic', 'ollama'
    model_name = Column(String, nullable=False)
    encrypted_key = Column(String, nullable=False)  # Decrypted memory-only using app/core/config.py ENCRYPTION_KEY


class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)


class VendorRule(Base):
    """Agent's long-term memory for auto-categorization."""

    __tablename__ = "vendor_rules"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    vendor_regex = Column(String, nullable=False)
    default_category_id = Column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)


class Transaction(Base):
    """Core financial ledger."""

    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)

    amount = Column(Float, nullable=False)
    currency = Column(String, default="USD")
    is_inflow = Column(Boolean, default=False)  # False = Expense, True = Income
    record_date = Column(Date, nullable=False)
    vendor_raw = Column(String, nullable=False)

    category_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PARSED)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
