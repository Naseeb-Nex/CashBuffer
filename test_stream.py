import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import io

app = FastAPI()

@app.get("/")
def test():
    data = "hello world\nline 2"
    return StreamingResponse(io.StringIO(data), media_type="text/csv")
