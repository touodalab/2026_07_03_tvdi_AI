# ============================================
# 0. 載入套件與環境設定
# ============================================

import os
import sys

current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from train_save import train_and_save_model

print("環境準備完畢，已成功載入 train_and_save_model 模組。")

# ============================================
# 定義 Pydantic 訓練相關模型（與 app.py 相同）
# ============================================

from pydantic import BaseModel,Field
from pprint import pprint

class TrainConfig(BaseModel):
    test_size: float = Field(0.2, description="測試集分割比例", ge=0.1 , le=0.5)
    random_state: int = Field(76, description="隨機種子", ge=0)
    model_type: str = Field("LinearRegression", description="模型演算法類型 (LinearRegression, Lasso, Ridge)")
    alpha: float = Field(1.0, description="正則化強度 alpha (適用於 Lasso 與 Ridge)", ge= 0.001, le=100.0)

class TrainResult(BaseModel):
    status: str = Field(..., description="執行結果狀態")
    r2: float = Field(..., description="測試集 R-squared 決定係數")
    coef: list[float] = Field(..., description="特徵權重係數列表")
    intercept: float = Field(..., description="截距")
    feature_coefs: dict[str, float] = Field(..., description="特徵及其權重映射")
    model_type: str = Field(..., description="模型演算法類型")
    alpha: float = Field(..., description="正則化強度 alpha")
    train_time: float = Field(..., description="訓練耗時 (秒)")
    message:str = Field(..., description="提示訊息")

print("TranConfig(BaseModel)")
pprint(TrainConfig.model_json_schema())
print("==============================")
print("TrainResult(BaseModel)")
pprint(TrainResult.model_json_schema())

from train_save import train_and_save_model
res_ridge:dict = train_and_save_model(
    test_size=0.2,
    random_state=76,
    model_type="Ridge",
    alpha=10.0
)
pprint(res_ridge)

import joblib

current_dir = os.getcwd()
model_path = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE = {}

def load_model_state():
    global MODEL_STATE
    if not os.path.exists(model_path):
        train_and_save_model()

    model_data = joblib.load(model_path)
    MODEL_STATE.clear()
    MODEL_STATE.update(
        {
            "model": model_data["model"],
            "oe": model_data["oe"],
            "ohe": model_data["ohe"],
            "scaler": model_data["scaler"],
            "r2": model_data.get("r2"),
            "feature_names": model_data["feature_names"],
            "feature_coefs": model_data.get("feature_coefs",{}),
            "model_type": model_data.get("model_type"),
            "alpha": model_data.get("alpha")
        }
    )
    print(f"✅ MODEL_STATE 已成功更新！當前模型：{MODEL_STATE['model_type']}，R² Score：{MODEL_STATE['r2']:.4f}")

load_model_state()

from fastapi import HTTPException

def train_api(config:TrainConfig) -> dict:
    """
    訓練端點：傳入測試集比例、隨機種子、模型類型與 alpha，線上重新訓練模型，並即時更新服務所使用的模型。
    """
    try:
        # 1. 執行重新訓練並儲存模型
        res = train_and_save_model(
            test_size=config.test_size,
            random_state= config.random_state,
            model_type= config.model_type,
            alpha=config.alpha
        )
         # 2. 線上重新載入最新模型狀態至全域變數
        load_model_state()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"線上訓練失敗: {str(e)}")

    return res

from fastapi import FastAPI
from fastapi.testclient import TestClient

mini_api = FastAPI()
@mini_api.post("/train", response_model=TrainResult)
def train_endpoint(config:TrainConfig):
    res = train_api(config=config)
    return res

client = TestClient(mini_api)
response = client.post("/train", json={
    "test_size": 0.2,
    "random_state": 76,
    "model_type": "Lasso",
    "alpha": 5.0
})
print("【重訓 Lasso 結果】")
print("HTTP 狀態碼:", response.status_code)
pprint(response.json())
   
