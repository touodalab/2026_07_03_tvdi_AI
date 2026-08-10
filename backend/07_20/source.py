from pydantic import BaseModel, TypeAdapter
import requests
from requests import Response,JSONDecodeError,HTTPError

URL = 'https://data.ntpc.gov.tw/api/datasets/1b72abe8-8862-4130-aeb8-178c1240e6c4/json?page=0&size=1000'

class CameraPosition(BaseModel):
    year:int
    bureau:str
    unit:str
    location:str

def get_camera_position() -> list[CameraPosition]:
    try:
        r:Response = requests.request(method='GET',url=URL)
        r.raise_for_status()
        data:list[dict] = r.json()
        adapter = TypeAdapter(list[CameraPosition])
        list_position:list[CameraPosition] = adapter.validate_python(data)
        return list_position
    
    except HTTPError as e:
        raise Exception(f"web api目前有問題:{e}")
    except JSONDecodeError as e:
        raise Exception(f"json格式有錯:{e}")
    except Exception as e:
        raise Exception(f"發生錯誤:{e}")