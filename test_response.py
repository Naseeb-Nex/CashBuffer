from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

app = FastAPI()


@app.get("/csv")
def get_csv():
    csv_data = "col1,col2\nval1,val2\n"
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=budget.csv"},
    )


client = TestClient(app)
resp = client.get("/csv")
print(resp.headers)
print(resp.text)
