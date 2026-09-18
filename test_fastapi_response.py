from fastapi import Response

r = Response(content="test")
print(r.body)
