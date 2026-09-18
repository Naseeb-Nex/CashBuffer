with open("tests/test_export.py", "r") as f:
    text = f.read()

text = text.replace(
    "from app.api.auth import get_current_user", "from app.api.auth import get_current_user\nfrom main import app"
)

text = text.replace("def mock_export_auth(app):", "def mock_export_auth():")

text = text.replace("app.dependency_overrides.pop(get_current_user, None)", "app.dependency_overrides.clear()")

with open("tests/test_export.py", "w") as f:
    f.write(text)
