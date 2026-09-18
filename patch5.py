with open("tests/test_export.py", "r") as f:
    text = f.read()

text = text.replace("response = client.get(", "response = await client.get(")

text = text.replace('user_id="alice_user_id"', "user_id=unique_user_alice")

with open("tests/test_export.py", "w") as f:
    f.write(text)
