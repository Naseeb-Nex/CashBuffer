import csv
import json
from io import StringIO
from datetime import date
from typing import Any

class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, date):
            return obj.isoformat()
        if hasattr(obj, "__dict__"):
            # Exclude SQLAlchemy internal state
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return super().default(obj)

def format_transactions(transactions, format):
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "amount", "currency", "is_inflow", "record_date", "vendor_raw", "category_id", "status"])
        for tx in transactions:
            writer.writerow([
                tx.id,
                tx.amount,
                tx.currency,
                tx.is_inflow,
                tx.record_date.isoformat() if tx.record_date else "",
                tx.vendor_raw,
                tx.category_id,
                tx.status.value if hasattr(tx.status, 'value') else tx.status,
            ])
        return output.getvalue()
    elif format == "json":
        return json.dumps(transactions, cls=ExtendedEncoder, indent=2)

def format_budget(budget, format):
    if format == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["total_income", "total_expense", "net_balance", "currency"])
        writer.writerow([
            budget.get("total_income", 0),
            budget.get("total_expense", 0),
            budget.get("net_balance", 0),
            budget.get("currency", "INR")
        ])
        
        writer.writerow([])
        writer.writerow(["category", "amount", "budget", "utilization"])
        for cat in budget.get("breakdown", []):
            writer.writerow([
                cat["category_name"],
                cat["total_amount"],
                cat["budget_limit"] if cat["budget_limit"] else "",
                f"{cat['utilization_pct']}%" if "utilization_pct" in cat else ""
            ])
            
        return output.getvalue()
    elif format == "json":
        return json.dumps(budget, indent=2)