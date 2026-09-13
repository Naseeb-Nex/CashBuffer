import re
from datetime import datetime
from typing import Optional, Dict, Any

class AxisBankParser:
    """
    Standard text parser for Axis Bank transaction alerts.
    Expected format patterns for debits:
    'INR 500.00 has been debited from your A/c ... on 12-08-26 ... Info: UPI/SWIGGY/...'
    """
    
    DEBIT_REGEX = re.compile(
        r"(?:INR|Rs\.?)\s*(?P<amount>\d+(?:\.\d+)?)\s*has been debited.*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}).*?Info:\s*(?P<vendor>[^\n]+)",
        re.IGNORECASE | re.DOTALL
    )
    
    CREDIT_REGEX = re.compile(
        r"(?:INR|Rs\.?)\s*(?P<amount>\d+(?:\.\d+)?)\s*has been credited.*?on\s*(?P<date>\d{2}-\d{2}-\d{2,4}).*?Info:\s*(?P<vendor>[^\n]+)",
        re.IGNORECASE | re.DOTALL
    )

    @classmethod
    def parse(cls, body: str) -> Optional[Dict[str, Any]]:
        body = body.strip()
        
        # Check debit first
        debit_match = cls.DEBIT_REGEX.search(body)
        if debit_match:
            return cls._build_payload(debit_match, is_inflow=False)
            
        # Check credit
        credit_match = cls.CREDIT_REGEX.search(body)
        if credit_match:
            return cls._build_payload(credit_match, is_inflow=True)
            
        return None

    @staticmethod
    def _build_payload(match: re.Match, is_inflow: bool) -> Dict[str, Any]:
        amount_str = match.group('amount')
        date_str = match.group('date')
        vendor_raw = match.group('vendor').strip()
        
        # Handle 2-digit vs 4-digit years safely
        if len(date_str.split('-')[-1]) == 2:
            dt = datetime.strptime(date_str, "%d-%m-%y").date()
        else:
            dt = datetime.strptime(date_str, "%d-%m-%Y").date()
            
        return {
            "amount": float(amount_str),
            "currency": "INR",
            "is_inflow": is_inflow,
            "record_date": dt,
            "vendor_raw": vendor_raw
        }
