import io

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.get("/")
def test():
    data = "hello world\nline 2"
    return StreamingResponse(io.StringIO(data), media_type="text/csv")
