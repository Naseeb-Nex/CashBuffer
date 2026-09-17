from datetime import date

from app.email.parser import (
    AxisBankParser,
    GenericBankParser,
    HDFCBankParser,
    UnifiedBankParser,
)


def test_axis_bank_debit_parser():
    email_body = (
        "INR 450.00 has been debited from your A/c no. XX1234 on 15-09-2026 at 14:20:10. Info: UPI/SWIGGY/ORDER_9876."
    )
    result = AxisBankParser.parse(email_body)
    assert result is not None
    assert result["amount"] == 450.00
    assert result["currency"] == "INR"
    assert result["is_inflow"] is False
    assert result["record_date"] == date(2026, 9, 15)
    assert "SWIGGY" in result["vendor_raw"]


def test_axis_bank_credit_parser():
    email_body = (
        "INR 50,000.00 has been credited to your A/c no. XX1234 on 01-09-26 at 09:00:00. "
        "Info: SALARY_TRANSFER_ACME_CORP."
    )
    result = AxisBankParser.parse(email_body)
    assert result is not None
    assert result["amount"] == 50000.00
    assert result["is_inflow"] is True
    assert result["record_date"] == date(2026, 9, 1)
    assert "SALARY" in result["vendor_raw"]


def test_hdfc_bank_debit_parser():
    email_body = "Rs. 1,299.50 has been spent on your HDFC Bank Card ending 5678 at AMAZON INDIA on 2026-09-14."
    result = HDFCBankParser.parse(email_body)
    assert result is not None
    assert result["amount"] == 1299.50
    assert result["is_inflow"] is False
    assert result["record_date"] == date(2026, 9, 14)
    assert "AMAZON" in result["vendor_raw"]


def test_generic_bank_parser_usd():
    email_body = "$79.99 was paid to Uber Technologies on 2026-09-12."
    result = GenericBankParser.parse(email_body)
    assert result is not None
    assert result["amount"] == 79.99
    assert result["currency"] == "USD"
    assert result["is_inflow"] is False
    assert "Uber" in result["vendor_raw"]


def test_unified_parser_dispatch():
    axis_text = "INR 350.00 has been debited on 10-09-2026 Info: ZOMATO"
    res = UnifiedBankParser.parse(axis_text)
    assert res is not None
    assert res["amount"] == 350.00
    assert "ZOMATO" in res["vendor_raw"]

    invalid_text = "Hello, this is a random newsletter with no transaction."
    assert UnifiedBankParser.parse(invalid_text) is None
