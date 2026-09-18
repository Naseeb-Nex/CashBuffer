import json
from datetime import date, datetime
from typing import Any


class ExtendedEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)


print(json.dumps([datetime.now(), date.today()], cls=ExtendedEncoder))
