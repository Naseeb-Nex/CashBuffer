with open("tests/test_export.py", "r") as f:
    text = f.read()

text = text.replace(
    '"total_income,total_expense,net_balance,currency"',
    '"total_inflow,total_outflow,net_buffer,transaction_count,uncategorized_count"',
)

text = text.replace('"category,amount,budget,utilization"', '"category,amount"')

text = text.replace('assert "total_income" in data', 'assert "total_inflow" in data')
text = text.replace('assert "total_expense" in data', 'assert "total_outflow" in data')
text = text.replace('assert "breakdown" in data', 'assert "category_breakdown" in data')

with open("tests/test_export.py", "w") as f:
    f.write(text)
