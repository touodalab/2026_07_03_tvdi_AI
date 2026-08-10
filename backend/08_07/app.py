import os
import sys
from contextlib import asynccontextmanager
from train_save import train_and_save_model
from pydantic import BaseModel,Field
from pprint import pprint
import joblib
from fastapi import FastAPI,HTTPException
import uvicorn


current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

model_path = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE = {}


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

class SalaryInput(BaseModel):
    YearsExperience: float = Field(..., description="工作年資 (年)", ge=0.0, le=60.0)
    EducationLevel: str = Field(..., description="學歷 (高中以下, 大學, 碩士以上)")
    City: str = Field(..., description="城市 (城市A, 城市B, 城市C)")

class SalaryOutput(BaseModel):
    predicted_salary: float = Field(..., description="預測年薪 (萬元)")
    feature_names: list[str] = Field(..., description="特徵欄位")
    feature_contribution: dict[str, float] = Field(..., description="各特徵對預測薪資之貢獻")
    model_type: str = Field(..., description="目前模型演算法")
    r2: float = Field(..., description="目前模型 R²")

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
            "alpha": model_data.get("alpha"),
            "coef": model_data.get("coef", []),
            "intercept": model_data.get("intercept"),
            "train_time": model_data.get("train_time"),
            "test_size": model_data.get("test_size"),
            "random_state": model_data.get("random_state")
        }
    )

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期：uvicorn 綁定埠口後才載入模型，
    避免 Render 因啟動太慢而判定『Port scan timeout』。
    """
    try:
        load_model_state()
    except Exception as e:
        print(f"[警告] 模型載入失敗，預測/訓練端點將回傳錯誤: {e}")
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    """根路徑：供 Render 健康檢查使用。"""
    return {"status": "ok", "service": "salary-predict-api", "docs": "/docs"}
@app.post("/train", response_model=TrainResult)
def train_endpoint(config:TrainConfig):
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

@app.post("/predict", response_model=SalaryOutput)
def predict_endpoint(payload: SalaryInput):
    """
    預測端點：接收工作年資、學歷與城市，回傳模型預測的年薪與各特徵貢獻。
    """
    try:
        oe = MODEL_STATE["oe"]
        ohe = MODEL_STATE["ohe"]
        scaler = MODEL_STATE["scaler"]
        model = MODEL_STATE["model"]
        feature_names = MODEL_STATE["feature_names"]

        # 1. 轉換學歷 (OrdinalEncoder: 高中以下=0, 大學=1, 碩士以上=2)
        education_val = float(oe.transform([[payload.EducationLevel]])[0][0])
        # 2. 轉換城市 (OneHotEncoder: 城市A, 城市B, 城市C)
        city_encoded = ohe.transform([[payload.City]])[0].tolist()
        # 3. 組合成完整特徵向量並標準化
        features = [[payload.YearsExperience, education_val, *city_encoded]]
        features_scaled = scaler.transform(features)
        # 4. 進行預測
        pred = float(model.predict(features_scaled)[0])

        contribution = {
            name: float(coef * val)
            for name, coef, val in zip(feature_names, model.coef_, features_scaled[0])
        }
        return SalaryOutput(
            predicted_salary=round(pred, 2),
            feature_names=feature_names,
            feature_contribution=contribution,
            model_type=MODEL_STATE["model_type"],
            r2=MODEL_STATE["r2"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"預測失敗: {str(e)}")

@app.get("/model-info")
def model_info_endpoint():
    """
    模型資訊端點：回傳目前服務所使用的模型狀態與評估指標，供前端初始化畫面使用。
    """
    return {
        "model_type": MODEL_STATE.get("model_type"),
        "r2": MODEL_STATE.get("r2"),
        "alpha": MODEL_STATE.get("alpha"),
        "intercept": MODEL_STATE.get("intercept"),
        "train_time": MODEL_STATE.get("train_time"),
        "test_size": MODEL_STATE.get("test_size"),
        "random_state": MODEL_STATE.get("random_state"),
        "feature_names": MODEL_STATE.get("feature_names", []),
        "feature_coefs": MODEL_STATE.get("feature_coefs", {}),
    }

if __name__ == "__main__":
    uvicorn.run("app:app", reload=True)