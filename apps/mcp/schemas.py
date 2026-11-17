from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MonthlySummaryParams(BaseModel):
    """Parameters for calculating read-only tenant monthly financial summary."""

    model_config = ConfigDict(extra="forbid")

    year: int = Field(..., ge=1970, le=2100, description="Calendar year (e.g. 2026)")
    month: int = Field(..., ge=1, le=12, description="Calendar month (1-12)")


class CategoryBreakdownItem(BaseModel):
    category_id: int | None = None
    category_name: str
    total_amount: float
    transaction_count: int


class MonthlySummaryResponse(BaseModel):
    year: int
    month: int
    total_inflow: float
    total_outflow: float
    net_buffer: float
    transaction_count: int
    uncategorized_count: int
    category_breakdown: list[CategoryBreakdownItem]


class TransactionQueryParams(BaseModel):
    """Parameters for querying tenant ledger transactions."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(50, ge=1, le=100, description="Max transactions to return (1-100)")
    offset: int = Field(0, ge=0, description="Offset for pagination (>=0)")
    start_date: date | None = Field(None, description="Filter transactions on or after this date (YYYY-MM-DD)")
    end_date: date | None = Field(None, description="Filter transactions on or before this date (YYYY-MM-DD)")
    status: Literal["parsed", "needs_review", "categorized"] | None = Field(
        None, description="Filter by categorization status"
    )
    category_id: int | None = Field(None, ge=1, description="Filter by category ID")
    search: str | None = Field(None, max_length=100, description="Case-insensitive vendor search substring")
    min_amount: float | None = Field(None, ge=0.0, description="Minimum transaction amount")
    max_amount: float | None = Field(None, ge=0.0, description="Maximum transaction amount")
    is_inflow: bool | None = Field(None, description="True for income, False for expenses")

    @model_validator(mode="after")
    def validate_ranges(self) -> TransactionQueryParams:
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError(
                f"start_date ({self.start_date}) cannot be after end_date ({self.end_date})"
            )
        if self.min_amount is not None and self.max_amount is not None and self.min_amount > self.max_amount:
            raise ValueError(
                f"min_amount ({self.min_amount}) cannot be greater than max_amount ({self.max_amount})"
            )
        return self


class TransactionItem(BaseModel):
    id: int
    user_id: str
    amount: float
    currency: str
    is_inflow: bool
    record_date: date
    vendor_raw: str
    category_id: int | None = None
    category_name: str | None = None
    status: str
    created_at: datetime | None = None


class TransactionQueryResponse(BaseModel):
    items: list[TransactionItem]
    total_count: int
    limit: int
    offset: int
    has_more: bool


class RecurringBillsParams(BaseModel):
    """Parameters for detecting and listing recurring bills / subscriptions."""

    model_config = ConfigDict(extra="forbid")

    min_occurrences: int = Field(
        2, ge=2, le=50, description="Minimum frequency threshold to qualify as a recurring bill"
    )
    lookback_months: int = Field(
        12, ge=1, le=60, description="Number of past months to inspect for recurring patterns"
    )


class RecurringBillItem(BaseModel):
    vendor: str
    currency: str
    average_amount: float
    min_amount: float
    max_amount: float
    occurrence_count: int
    first_payment_date: date
    last_payment_date: date
    category_name: str
    estimated_frequency: str
    estimated_monthly_amount: float


class RecurringBillsResponse(BaseModel):
    bills: list[RecurringBillItem]
    total_monthly_commitment: float
    bill_count: int
