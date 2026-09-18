with open("tests/test_export.py", "r") as f:
    text = f.read()

# Replace test_user with unique_user_alice
text = text.replace("test_user", "unique_user_alice")
text = text.replace('user_id="unique_user_alice"', 'user_id="alice_user_id"')

with open("tests/test_export.py", "w") as f:
    f.write(text)
