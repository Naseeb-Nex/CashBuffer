import enum
import json
from typing import Any


class TransactionStatus(str, enum.Enum):
    CATEGORIZED = "categorized"
    UNCATEGORIZED = "uncategorized"


print(hasattr(TransactionStatus.CATEGORIZED, "__dict__"))
print(TransactionStatus.CATEGORIZED.__dict__)


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return super().default(obj)


print(json.dumps([TransactionStatus.CATEGORIZED], cls=ExtendedEncoder))
