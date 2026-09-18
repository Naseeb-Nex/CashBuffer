with open("tests/test_export.py", "r") as f:
    text = f.read()

text = text.replace(
    """@pytest.fixture
def mock_export_auth():
    app.dependency_overrides[get_current_user] = lambda: "test_user"
    yield
    app.dependency_overrides.clear()""",
    """@pytest.fixture
def mock_export_auth(unique_user_alice):
    app.dependency_overrides[get_current_user] = lambda: unique_user_alice
    yield
    app.dependency_overrides.clear()""",
)

text = text.replace("regex=", "pattern=")

with open("tests/test_export.py", "w") as f:
    f.write(text)
