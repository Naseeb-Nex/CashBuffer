import enum


class TransactionStatus(enum.Enum):
    CATEGORIZED = "categorized"
    UNCATEGORIZED = "uncategorized"


print(hasattr(TransactionStatus.CATEGORIZED, "__dict__"))
print(TransactionStatus.CATEGORIZED.__dict__)
