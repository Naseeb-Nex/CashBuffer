"""Axis Bank email alert parser."""

from __future__ import annotations

import re
from datetime import date, datetime

from apps.ingress.src.domain.interfaces import AlertParser
from apps.ingress.src.domain.models import ParsedAlert

class AxisBankParser(AlertParser):
    """Parses Axis bank alert emails."""

    # Matches debit: INR 450.00 has been debited ... on 15-09-2026 ... Info: UPI/SWIGGY/...
    DEBIT_PATTERN = re.compile(
        r"(?:INR|Rs\.?)\s*([\d,]+\.?\d*)\s+has\s+been\s+debited.*?(?:on\s+(\d{1,2}-\d{1,2}-\d{2,4})).*?Info:\s*([^\.\n]+)",
        re.IGNORECASE | re.DOTALL,
    )

    # Matches credit: INR 50,000.00 has been credited ... on 01-09-26 ... Info: SALARY...
    CREDIT_PATTERN = re.compile(
        r"(?:INR|Rs\.?)\s*([\d,]+\.?\d*)\s+has\s+been\s+credited.*?(?:on\s+(\d{1,2}-\d{1,2}-\d{2,4})).*?Info:\s*([^\.\n]+)",
        re.IGNORECASE | re.DOTALL,
    )

    def _parse_date(self, date_str: str) -> date:
        date_str = date_str.strip()
        for fmt in ("%d-%m-%Y", "%d-%m-%y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        return date.today()

    def parse(self, text: str, raw_email_id: str | None = None) -> ParsedAlert | None:
        if not text:
            return None

        email_url = f"https://mail.google.com/mail/u/0/#all/{raw_email_id}" if raw_email_id else None

        # Check debit first
        m_debit = self.DEBIT_PATTERN.search(text)
        if m_debit:
            amt_str, date_str, vendor_raw = m_debit.groups()
            amount = float(amt_str.replace(",", ""))
            return ParsedAlert(
                amount=-abs(amount),  # negative = expense
                currency="INR",
                is_inflow=False,
                record_date=self._parse_date(date_str),
                vendor_raw=vendor_raw.strip(),
                raw_email_id=raw_email_id,
                email_url=email_url,
                raw_source="gmail_axis",
                notes=f"Axis debit alert: {vendor_raw.strip()}",
            )

        # Check credit
        m_credit = self.CREDIT_PATTERN.search(text)
        if m_credit:
            amt_str, date_str, vendor_raw = m_credit.groups()
            amount = float(amt_str.replace(",", ""))
            return ParsedAlert(
                amount=abs(amount),  # positive = income
                currency="INR",
                is_inflow=True,
                record_date=self._parse_date(date_str),
                vendor_raw=vendor_raw.strip(),
                raw_email_id=raw_email_id,
                email_url=email_url,
                raw_source="gmail_axis",
                notes=f"Axis credit alert: {vendor_raw.strip()}",
            )

        return None
