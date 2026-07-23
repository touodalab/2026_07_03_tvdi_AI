from fastapi import FastAPI, HTTPException
from tools import root



app = FastAPI()
@app.get("/")
def read_root(aqi_min:int|None=None, aqi_max:int|None=None):
    results = root.sites
    if aqi_min is not None:
        results = [s for s in results if s.aqi >= aqi_min]
    if aqi_max is not None:
        results = [s for s in results if s.aqi <= aqi_max]
    return results

@app.get("/county/{county_name}")
def specific_county(county_name:str):
    results = [site for site in root.sites if county_name == site.county]
    if not results:
        raise HTTPException(status_code=404, detail=f"找不到縣市「{county_name}」的空氣品質資料")
    return results
    


# @app.get("/items/{item_id}")
# def read_item(item_id: int, q: str | None = None):
#     return {"item_id": item_id, "q": q}