import enum
import json
from typing import Any


class TransactionStatus(str, enum.Enum):
    CATEGORIZED = "categorized"
    UNCATEGORIZED = "uncategorized"


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        # if isinstance(obj, date): ...
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return super().default(obj)


class Tx:
    def __init__(self):
        self.amount = 100
        self.status = TransactionStatus.CATEGORIZED


tx = Tx()
try:
    print(json.dumps([tx], cls=ExtendedEncoder))
except Exception as e:
    print(f"Error: {e}")
