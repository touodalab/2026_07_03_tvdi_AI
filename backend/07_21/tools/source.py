from pydantic import BaseModel,Field,field_validator
from datetime import datetime
# 定義 AirSite 模型，對應單一測站的空氣品質資料
class AirSite(BaseModel):
    aqi:int                                    # 空氣品質指標
    county:str                                 # 縣市名稱
    date:datetime = Field(alias="datacreationdate")  # 資料建立時間，使用 alias 對應 JSON 欄位名
    lat:float = Field(alias = "latitude")      # 緯度
    lon:float = Field(alias="longitude")       # 經度
    pm25:float = Field(alias="pm2.5")          # PM2.5 濃度
    pollutant:str                              # 主要污染物名稱
    site_name:str = Field(alias="sitename")    # 測站名稱
    status:str                                 # 空品等級狀態

    #自定義驗證器：將空字串轉換為 0，避免型別轉換錯誤
    @field_validator('aqi','lat','lon','pm25', mode='before')
    @classmethod
    def empty_to_zero(cls, v):
        return 0 if v == '' else v

class Root(BaseModel):
    status:bool = True          # 回應狀態，預設為 True
    sites:list[AirSite] 