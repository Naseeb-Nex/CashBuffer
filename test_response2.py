import io

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

app = FastAPI()


@app.get("/csv")
def get_csv():
    csv_data = "col1,col2\nval1,val2\n"
    return StreamingResponse(
        content=io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=budget.csv"},
    )


client = TestClient(app)
resp = client.get("/csv")
print(resp.headers)
print(resp.text)
