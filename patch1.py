with open("app/services/export.py", "r") as f:
    text = f.read()

text = text.replace(
    'writer.writerow(["total_income", "total_expense", "net_balance", "currency"])',
    'writer.writerow(["total_inflow", "total_outflow", "net_buffer", "transaction_count", "uncategorized_count"])',
)

text = text.replace(
    """        writer.writerow([
            budget.get("total_income", 0),
            budget.get("total_expense", 0),
            budget.get("net_balance", 0),
            budget.get("currency", "INR")
        ])""",
    """        writer.writerow([
            budget.get("total_inflow", 0),
            budget.get("total_outflow", 0),
            budget.get("net_buffer", 0),
            budget.get("transaction_count", 0),
            budget.get("uncategorized_count", 0)
        ])""",
)

# the breakdown has no budget_limit/utilization_pct either
text = text.replace(
    """        writer.writerow(["category", "amount", "budget", "utilization"])
        for cat in budget.get("breakdown", []):
            writer.writerow([
                cat["category_name"],
                cat["total_amount"],
                cat["budget_limit"] if cat["budget_limit"] else "",
                f"{cat['utilization_pct']}%" if "utilization_pct" in cat else ""
            ])""",
    """        writer.writerow(["category", "amount"])
        for cat in budget.get("category_breakdown", []):
            writer.writerow([
                cat["category_name"],
                cat["total_amount"]
            ])""",
)

with open("app/services/export.py", "w") as f:
    f.write(text)
