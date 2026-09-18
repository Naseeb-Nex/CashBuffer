with open("tests/test_export.py", "r") as f:
    text = f.read()

text = text.replace(
    'response = await client.get("/api/v1/export/transactions?format=csv")',
    'response = await client.get("/api/v1/export/transactions?format=csv")\n    print("Response status:", response.status_code)\n    print("Response text:", response.text)',
)

with open("tests/test_export.py", "w") as f:
    f.write(text)
