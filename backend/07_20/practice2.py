# 匯入 FastAPI 框架
from fastapi import FastAPI
# 匯入 uvicorn 伺服器，用於執行 FastAPI 應用程式
import uvicorn
# 從 source 模組匯入取得攝影機位置的函式與資料模型
from source import get_camera_position, CameraPosition

# 建立 FastAPI 應用程式實例
app = FastAPI()


# 定義首頁路由 (GET /)，可接受查詢參數 bureau (選擇性)
@app.get("/")
def read_root(bureau:str | None = None):
    # 取得所有攝影機位置資料
    data:list[CameraPosition] = get_camera_position()
    # 若未提供 bureau 參數，則回傳全部資料
    if not bureau :        
        return data
    
    # 若有提供 bureau，篩選出符合該局屬單位的攝影機資料
    bureau_datas:list[CameraPosition] = []
    for camera in data:        
        if camera.bureau == bureau:
            bureau_datas.append(camera)
        
    return bureau_datas



# 註解掉的範例路由：依 item_id 取得單一項目資料
#@app.get("/items/{item_id}")
#def read_item(item_id: int, q: str | None = None):
#    return {"item_id": item_id, "q": q}

# 主程式入口：啟動 uvicorn 伺服器，支援熱重載 (reload=True)
if __name__ == "__main__":
    uvicorn.run("practice2:app",reload=True)