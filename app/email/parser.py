import re
from datetime import date, datetime
from typing import Any


class AxisBankParser:
    """Parser for Axis Bank transaction alerts."""

    DEBIT_REGEX = re.compile(
        r"(?:INR|Rs\.?)\s*(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)\s*has been debited.*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}).*?Info:\s*(?P<vendor>[^\n\r]+)",
        re.IGNORECASE | re.DOTALL,
    )
    CREDIT_REGEX = re.compile(
        r"(?:INR|Rs\.?)\s*(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)\s*has been credited.*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}).*?Info:\s*(?P<vendor>[^\n\r]+)",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def parse(cls, body: str) -> dict[str, Any] | None:
        body = body.strip()
        debit_match = cls.DEBIT_REGEX.search(body)
        if debit_match:
            return cls._build_payload(debit_match, is_inflow=False)

        credit_match = cls.CREDIT_REGEX.search(body)
        if credit_match:
            return cls._build_payload(credit_match, is_inflow=True)
        return None

    @staticmethod
    def _build_payload(match: re.Match, is_inflow: bool) -> dict[str, Any]:
        amount_str = match.group("amount").replace(",", "")
        date_str = match.group("date")
        vendor_raw = match.group("vendor").strip().rstrip(".")
        if len(date_str.split("-")[-1]) == 2:
            dt = datetime.strptime(date_str, "%d-%m-%y").date()
        else:
            dt = datetime.strptime(date_str, "%d-%m-%Y").date()
        return {
            "amount": float(amount_str),
            "currency": "INR",
            "is_inflow": is_inflow,
            "record_date": dt,
            "vendor_raw": vendor_raw,
        }


class HDFCBankParser:
    """Parser for HDFC Bank transaction alerts."""

    DEBIT_REGEX = re.compile(
        r"(?:Rs\.?|INR)\s*(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)\s*has been (?:debited from|spent on).*?(?:to|at|info:?)\s*(?P<vendor>[^\n\r.]+).*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}|\d{4}-\d{2}-\d{2})",
        re.IGNORECASE | re.DOTALL,
    )
    CREDIT_REGEX = re.compile(
        r"(?:Rs\.?|INR)\s*(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)\s*has been (?:credited to|deposited into).*?(?:by|from|info:?)\s*(?P<vendor>[^\n\r.]+).*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}|\d{4}-\d{2}-\d{2})",
        re.IGNORECASE | re.DOTALL,
    )

    @classmethod
    def parse(cls, body: str) -> dict[str, Any] | None:
        body = body.strip()
        debit_match = cls.DEBIT_REGEX.search(body)
        if debit_match:
            return cls._build_payload(debit_match, is_inflow=False)

        credit_match = cls.CREDIT_REGEX.search(body)
        if credit_match:
            return cls._build_payload(credit_match, is_inflow=True)
        return None

    @staticmethod
    def _build_payload(match: re.Match, is_inflow: bool) -> dict[str, Any]:
        amount_str = match.group("amount").replace(",", "")
        date_str = match.group("date")
        vendor_raw = match.group("vendor").strip().rstrip(".")
        if "-" in date_str:
            parts = date_str.split("-")
            if len(parts[0]) == 4:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            elif len(parts[-1]) == 2:
                dt = datetime.strptime(date_str, "%d-%m-%y").date()
            else:
                dt = datetime.strptime(date_str, "%d-%m-%Y").date()
        else:
            dt = date.today()
        return {
            "amount": float(amount_str),
            "currency": "INR",
            "is_inflow": is_inflow,
            "record_date": dt,
            "vendor_raw": vendor_raw,
        }


class GenericBankParser:
    """
    Fallback parser for generic banking transaction alerts (supports INR, USD, EUR, GBP).
    """

    GENERIC_PATTERN = re.compile(
        r"(?P<currency>INR|Rs\.?|USD|\$|EUR|€|GBP|£)\s*(?P<amount>\d+(?:,\d+)*(?:\.\d+)?)\s*(?:was|has been)?\s*(?P<type>debited|spent|paid|credited|deposited|received|transferred)\s*(?:to|at|for|from|by)?\s*(?P<vendor>[^\n\r.]+?)(?:\s+on\s+(?P<date>\d{2}[-/]\d{2}[-/]\d{2,4}|\d{4}[-/]\d{2}[-/]\d{2})|\.|\n|$)",
        re.IGNORECASE,
    )

    CURRENCY_MAP = {
        "INR": "INR",
        "RS": "INR",
        "RS.": "INR",
        "USD": "USD",
        "$": "USD",
        "EUR": "EUR",
        "€": "EUR",
        "GBP": "GBP",
        "£": "GBP",
    }

    @classmethod
    def parse(cls, body: str) -> dict[str, Any] | None:
        body = body.strip()
        match = cls.GENERIC_PATTERN.search(body)
        if not match:
            return None

        amount_str = match.group("amount").replace(",", "")
        raw_curr = match.group("currency").upper().strip()
        currency = cls.CURRENCY_MAP.get(raw_curr, "INR")
        action_type = match.group("type").lower()
        is_inflow = action_type in {"credited", "deposited", "received"}

        vendor_raw = match.group("vendor").strip().rstrip(".")
        if not vendor_raw or vendor_raw.lower() in {"your account", "a/c", "bank"}:
            vendor_raw = "Unknown Vendor"

        date_str = match.group("date")
        if date_str:
            date_str = date_str.replace("/", "-")
            parts = date_str.split("-")
            if len(parts[0]) == 4:
                dt = datetime.strptime(date_str, "%Y-%m-%d").date()
            elif len(parts[-1]) == 2:
                dt = datetime.strptime(date_str, "%d-%m-%y").date()
            else:
                dt = datetime.strptime(date_str, "%d-%m-%Y").date()
        else:
            dt = date.today()

        return {
            "amount": float(amount_str),
            "currency": currency,
            "is_inflow": is_inflow,
            "record_date": dt,
            "vendor_raw": vendor_raw,
        }


class UnifiedBankParser:
    """Unified entry point testing all parsers in order of specificity."""

    @classmethod
    def parse(cls, body: str) -> dict[str, Any] | None:
        if not body or not body.strip():
            return None

        # 1. Axis Bank
        axis_res = AxisBankParser.parse(body)
        if axis_res:
            return axis_res

        # 2. HDFC Bank
        hdfc_res = HDFCBankParser.parse(body)
        if hdfc_res:
            return hdfc_res

        # 3. Generic Alert
        return GenericBankParser.parse(body)
