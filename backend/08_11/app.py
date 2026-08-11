# ============================================
# 薪資預測機器學習平台 - 單一整合服務 (FastAPI + Gradio)
#
# 整合來源：
#   * 後端 app.py        -> FastAPI RESTful API (/train, /predict, /model-info)
#   * gradio_ui.py       -> Gradio 前端 UI (RWD, 仿 Iris 風格)
#   * gradio_app.py      -> Gradio 前端 (先前版本)
#
# 整合重點：
#   1. 單一行程 / 單一 Server：使用 gr.mount_gradio_app() 將 Gradio UI
#      直接掛載到 FastAPI 實例上，共用同一個 Uvicorn 執行行程與同一個 Port。
#   2. 消除內部 HTTP 請求：前端不再透過 requests.post("http://127.0.0.1:8000/predict")
#      呼叫自身 API，而是直接在 Python 函式內呼叫對應的業務邏輯 (模型預測 / 模型訓練)，
#      提升執行效率並減少不必要的內部網路開銷。
#   3. 保留原有功能：FastAPI 的 /train、/predict、/model-info 端點仍然可用
#      (供外部程式或測試使用)；Gradio 原有介面元件、分頁、輸入輸出欄位與互動邏輯完整保留。
#
# 啟動方式 (擇一)：
#   python app.py
#   uvicorn app:app
# ============================================
import os
import sys
from contextlib import asynccontextmanager

import joblib
import gradio as gr
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from train_save import train_and_save_model

# ============================================
# 0. 路徑與全域模型狀態
# ============================================
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

model_path = os.path.join(current_dir, "salary_model.joblib")
MODEL_STATE = {}


# ============================================
# 1. Pydantic 資料模型 (API 請求解構)
# ============================================
class TrainConfig(BaseModel):
    test_size: float = Field(0.2, description="測試集分割比例", ge=0.1, le=0.5)
    random_state: int = Field(76, description="隨機種子", ge=0)
    model_type: str = Field("LinearRegression", description="模型演算法類型 (LinearRegression, Lasso, Ridge)")
    alpha: float = Field(1.0, description="正則化強度 alpha (適用於 Lasso 與 Ridge)", ge=0.001, le=100.0)


class TrainResult(BaseModel):
    status: str = Field(..., description="執行結果狀態")
    r2: float = Field(..., description="測試集 R-squared 決定係數")
    coef: list[float] = Field(..., description="特徵權重係數列表")
    intercept: float = Field(..., description="截距")
    feature_coefs: dict[str, float] = Field(..., description="特徵及其權重映射")
    model_type: str = Field(..., description="模型演算法類型")
    alpha: float = Field(..., description="正則化強度 alpha")
    train_time: float = Field(..., description="訓練耗時 (秒)")
    message: str = Field(..., description="提示訊息")


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


# ============================================
# 2. 模型載入 / 狀態管理
# ============================================
def load_model_state():
    """從 salary_model.joblib 載入最新模型與預處理器至全域 MODEL_STATE。"""
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
            "feature_coefs": model_data.get("feature_coefs", {}),
            "model_type": model_data.get("model_type"),
            "alpha": model_data.get("alpha"),
            "coef": model_data.get("coef", []),
            "intercept": model_data.get("intercept"),
            "train_time": model_data.get("train_time"),
            "test_size": model_data.get("test_size"),
            "random_state": model_data.get("random_state"),
        }
    )


# ============================================
# 3. 核心業務邏輯 (Gradio 與 FastAPI 共用，直接在行程內呼叫)
# ============================================
def _predict_salary(years_experience: float, education_level: str, city: str) -> dict:
    """執行薪資預測，回傳與原 /predict 端點相同的結果字典。"""
    if not MODEL_STATE:
        load_model_state()
    oe = MODEL_STATE["oe"]
    ohe = MODEL_STATE["ohe"]
    scaler = MODEL_STATE["scaler"]
    model = MODEL_STATE["model"]
    feature_names = MODEL_STATE["feature_names"]

    # 1. 轉換學歷 (OrdinalEncoder: 高中以下=0, 大學=1, 碩士以上=2)
    education_val = float(oe.transform([[education_level]])[0][0])
    # 2. 轉換城市 (OneHotEncoder: 城市A, 城市B, 城市C)
    city_encoded = ohe.transform([[city]])[0].tolist()
    # 3. 組合成完整特徵向量並標準化
    features = [[years_experience, education_val, *city_encoded]]
    features_scaled = scaler.transform(features)
    # 4. 進行預測
    pred = float(model.predict(features_scaled)[0])

    contribution = {
        name: float(coef * val)
        for name, coef, val in zip(feature_names, model.coef_, features_scaled[0])
    }
    return {
        "predicted_salary": round(pred, 2),
        "feature_names": feature_names,
        "feature_contribution": contribution,
        "model_type": MODEL_STATE["model_type"],
        "r2": MODEL_STATE["r2"],
    }


def _train_model(test_size: float, random_state: int, model_type: str, alpha: float) -> dict:
    """執行線上重新訓練並即時更新 MODEL_STATE，回傳與原 /train 端點相同的結果字典。"""
    res = train_and_save_model(
        test_size=test_size,
        random_state=random_state,
        model_type=model_type,
        alpha=alpha,
    )
    load_model_state()
    return res


def _get_model_info() -> dict:
    """取得目前服務所使用的模型狀態與評估指標。"""
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


# ============================================
# 4. FastAPI 應用程式與 RESTful API 端點
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期：啟動時若尚未載入模型則載入。
    模型若已在模組載入階段 (Gradio 初始畫面) 載入，則不需重複載入。
    """
    if not MODEL_STATE:
        try:
            load_model_state()
        except Exception as e:
            print(f"[警告] 模型載入失敗，預測/訓練端點將回傳錯誤: {e}")
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """健康檢查端點：供 Render 等平台設定 GET /health 作為健康檢查 (Gradio UI 掛載於 /)。"""
    return {"status": "ok", "service": "salary-predict-api", "docs": "/docs"}


@app.post("/train", response_model=TrainResult)
def train_endpoint(config: TrainConfig):
    """
    訓練端點：傳入測試集比例、隨機種子、模型類型與 alpha，線上重新訓練模型，並即時更新服務所使用的模型。
    """
    try:
        res = _train_model(
            test_size=config.test_size,
            random_state=config.random_state,
            model_type=config.model_type,
            alpha=config.alpha,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"線上訓練失敗: {str(e)}")

    return res


@app.post("/predict", response_model=SalaryOutput)
def predict_endpoint(payload: SalaryInput):
    """
    預測端點：接收工作年資、學歷與城市，回傳模型預測的年薪與各特徵貢獻。
    """
    try:
        return SalaryOutput(
            **_predict_salary(
                payload.YearsExperience,
                payload.EducationLevel,
                payload.City,
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"預測失敗: {str(e)}")


@app.get("/model-info")
def model_info_endpoint():
    """
    模型資訊端點：回傳目前服務所使用的模型狀態與評估指標，供前端初始化畫面使用。
    """
    return _get_model_info()


# ============================================
# 5. Gradio 前端 (RWD，仿 Iris 風格)
# ============================================
EDU_CHOICES = ["高中以下", "大學", "碩士以上"]
CITY_CHOICES = ["城市A", "城市B", "城市C"]
MODEL_CHOICES = ["LinearRegression", "Lasso", "Ridge"]

# 特徵欄位 -> 中文顯示名稱
FEATURE_LABELS = {
    "YearsExperience": "工作年資",
    "EducationLevel": "學歷等級",
    "City_城市A": "城市A",
    "City_城市B": "城市B",
    "City_城市C": "城市C",
}

# 採用 CSS Grid + auto-fit + clamp() + media query 斷點
RWD_CSS = """
<style>
/* ---------- 通用預測卡片 (仿 Iris 風格) ---------- */
.rwd-card, .rwd-bars, .rwd-info-strip, .rwd-metrics {
    max-width: 100%;
    box-sizing: border-box;
    overflow-wrap: break-word;
}
/* 強制所有自訂卡片文字為深色，避免 Gradio 主題(尤其手機深色模式)把文字蓋成白色 */
.rwd-card,
.rwd-card h2,
.rwd-card span,
.rwd-card strong,
.rwd-card .rwd-tag,
.rwd-card .rwd-sub,
.rwd-bars .rwd-bar-info span,
.rwd-info-strip,
.rwd-info-strip strong,
.rwd-metric .rwd-label,
.rwd-chart-title {
    color: #111111 !important;
}
.rwd-card {
    background-color: #ffffff;
    padding: 22px;
    border-radius: 12px;
    text-align: center;
    border: 1.5px solid rgba(19, 115, 51, 0.25);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
    margin-bottom: 20px;
    transition: all 0.3s ease;
}
.rwd-card .rwd-tag {
    font-size: clamp(0.8rem, 2.5vw, 0.95rem);
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    opacity: 0.85;
}
.rwd-card h2 {
    font-size: clamp(1.6rem, 6vw, 2.4rem);
    margin: 8px 0;
    font-weight: 800;
    letter-spacing: 0.5px;
}
.rwd-card .rwd-sub {
    font-size: clamp(0.85rem, 2.5vw, 1.1rem);
    font-weight: 500;
    opacity: 0.92;
}
.rwd-card .rwd-sub strong {
    font-size: clamp(1rem, 3.5vw, 1.5rem);
}

/* ---------- 指標卡片網格 (auto-fit 自動換行) ---------- */
.rwd-metrics {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}
.rwd-metric {
    background-color: #f8f9fa;
    padding: 18px 10px;
    border-radius: 10px;
    text-align: center;
    border: 1px solid #e0e0e0;
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
}
.rwd-metric .rwd-label {
    font-size: 0.72rem;
    color: #5f6368;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.rwd-metric .rwd-value {
    font-size: clamp(1.15rem, 4vw, 2rem);
    font-weight: 800;
    margin-top: 5px;
    line-height: 1.2;
    word-break: break-word;
}

/* ---------- 橫條圖 (貢獻度 / 特徵權重) ---------- */
.rwd-bars {
    background-color: #ffffff;
    padding: 14px;
    border-radius: 10px;
    border: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: 12px;
}
.rwd-bar-row { width: 100%; }
.rwd-bar-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: 5px;
    font-weight: 600;
    font-size: clamp(0.8rem, 2.5vw, 0.95rem);
    gap: 8px;
}
.rwd-bar-track {
    background-color: #f1f3f4;
    border-radius: 8px;
    height: 12px;
    overflow: hidden;
    width: 100%;
}
.rwd-bar-fill {
    height: 100%;
    border-radius: 8px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ---------- 資訊條 ---------- */
.rwd-info-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 22px;
    font-size: clamp(0.82rem, 2.5vw, 0.95rem);
    color: #3c4043;
    background: #f1f3f4;
    padding: 12px 18px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    font-weight: 500;
    margin-top: 14px;
}

/* ---------- 圖表標題 ---------- */
.rwd-chart-title {
    margin: 0 0 8px 0;
    font-size: 1.1rem;
    font-weight: 700;
    color: #202124;
    letter-spacing: 0.3px;
}

/* ---------- 錯誤提示 ---------- */
.rwd-error {
    background: #fce8e6;
    color: #c5221f;
    padding: 20px;
    border-radius: 12px;
    border: 1.5px solid rgba(197, 34, 31, 0.3);
    text-align: center;
    font-weight: 600;
}

/* ---------- 響應式斷點：手機/平板 強制單欄 ---------- */
/* 注意：Gradio 6 的 Row 使用 .row (flexbox) 類別，非舊版的 .gradio-row (grid) */
@media (max-width: 900px) {
    .gradio-container .row {
        flex-direction: column;
    }
    .gradio-container .row > * {
        min-width: 100% !important;
    }
}
@media (max-width: 640px) {
    .rwd-card { padding: 16px; }
    .rwd-info-strip { flex-direction: column; gap: 6px; }
    .rwd-metrics { grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }
    .rwd-bars { gap: 10px; }
    .rwd-bar-info { flex-wrap: wrap; }
}
</style>
"""


# ============================================
# 6. HTML 結果卡片生成函數 (仿 Iris 的 HTML 卡片)
# ============================================
def make_prediction_card(pred: float, model_type: str, r2: float) -> str:
    """薪資預測結果卡片 (綠底卡片，風格與 Iris 的『品種預測卡片』一致)。
    全部使用 inline style，確保手機/深色模式下文字仍為黑色且不會被 Gradio 主題蓋掉。"""
    monthly = pred * 10000 / 12
    return f"""
    <div style="background-color:#e6f4ea;color:#111111;padding:20px;border-radius:12px;border:1.5px solid rgba(19,115,51,.25);text-align:center;margin-bottom:14px;box-shadow:0 4px 12px rgba(0,0,0,.06);max-width:100%;box-sizing:border-box;">
        <div style="font-size:14px;font-weight:bold;letter-spacing:1.5px;color:#111111;text-transform:uppercase;">📊 預測年薪</div>
        <div style="font-size:clamp(24px,8vw,36px);font-weight:800;margin:8px 0;color:#111111;line-height:1.2;word-break:break-word;">NT$ {pred:,.2f} 萬</div>
        <div style="font-size:16px;font-weight:500;color:#111111;">折合月薪約 <strong style="font-size:20px;color:#111111;">NT$ {monthly:,.0f}</strong> 元 / 月</div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px 22px;font-size:14px;color:#111111;background:#f1f3f4;padding:12px 18px;border-radius:8px;border:1px solid #e0e0e0;font-weight:500;margin-bottom:16px;max-width:100%;box-sizing:border-box;">
        <span style="color:#111111;">🤖 模型演算法: <strong style="color:#111111;">{model_type}</strong></span>
        <span style="color:#111111;">📈 模型 R² Score: <strong style="color:#111111;">{r2:.4f}</strong></span>
    </div>
    """


def make_contribution_bars(contrib: dict[str, float]) -> str:
    """各特徵對預測薪資的貢獻度橫條圖 (正貢獻綠色、負貢獻紅色)。全部 inline style。"""
    if not contrib:
        return "<div style='background:#fce8e6;color:#c5221f;padding:20px;border-radius:12px;text-align:center;font-weight:600;'>⚠️ 目前尚無特徵貢獻資料</div>"
    max_abs = max(abs(v) for v in contrib.values()) or 1.0
    items = []
    for feat, val in contrib.items():
        pct = abs(val) / max_abs * 100
        color = "#137333" if val >= 0 else "#c5221f"
        sign = "+" if val >= 0 else "-"
        label = FEATURE_LABELS.get(feat, feat)
        items.append(f"""
        <div style="width:100%;">
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 8px;margin-bottom:5px;font-weight:600;font-size:14px;color:#111111;">
                <span style="color:#111111;">{label}</span>
                <span style="color:#111111;white-space:nowrap;">{sign}NT$ {abs(val):,.2f} 萬</span>
            </div>
            <div style="background-color:#f1f3f4;border-radius:8px;height:12px;overflow:hidden;width:100%;">
                <div style="background-color:{color};width:{pct:.1f}%;height:100%;border-radius:8px;"></div>
            </div>
        </div>""")
    return ('<div style="display:flex;flex-direction:column;gap:14px;margin-top:4px;'
            'width:100%;max-width:100%;box-sizing:border-box;'
            'background-color:#ffffff;padding:14px;border-radius:10px;border:1px solid #e0e0e0;">'
            + "".join(items) + "</div>")


def make_metrics_card(info: dict) -> str:
    """訓練評估指標卡片網格 (R² / 訓練耗時 / 正則化強度)。全部 inline style。"""
    r2 = info.get("r2")
    train_time = info.get("train_time")
    alpha = info.get("alpha")
    r2_str = f"{r2 * 100:.2f}%" if r2 is not None else "—"
    time_str = f"{train_time:.4f}s" if train_time is not None else "—"
    alpha_str = f"α={alpha}" if alpha is not None else "—"
    model_type = info.get("model_type", "—")
    intercept = info.get("intercept")
    test_size = info.get("test_size")
    seed = info.get("random_state")
    return f"""
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:14px;margin-bottom:16px;max-width:100%;box-sizing:border-box;">
        <div style="background-color:#f8f9fa;padding:16px 10px;border-radius:10px;text-align:center;border:1px solid #e0e0e0;box-shadow:0 2px 6px rgba(0,0,0,.02);">
            <div style="font-size:12px;color:#111111;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">測試集 R²</div>
            <div style="font-size:26px;font-weight:800;color:#1a73e8;margin-top:5px;line-height:1.2;">{r2_str}</div>
        </div>
        <div style="background-color:#f8f9fa;padding:16px 10px;border-radius:10px;text-align:center;border:1px solid #e0e0e0;box-shadow:0 2px 6px rgba(0,0,0,.02);">
            <div style="font-size:12px;color:#111111;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">模型訓練耗時</div>
            <div style="font-size:26px;font-weight:800;color:#137333;margin-top:5px;line-height:1.2;">{time_str}</div>
        </div>
        <div style="background-color:#f8f9fa;padding:16px 10px;border-radius:10px;text-align:center;border:1px solid #e0e0e0;box-shadow:0 2px 6px rgba(0,0,0,.02);">
            <div style="font-size:12px;color:#111111;font-weight:bold;letter-spacing:.5px;text-transform:uppercase;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">正則化強度</div>
            <div style="font-size:26px;font-weight:800;color:#ab47bc;margin-top:5px;line-height:1.2;">{alpha_str}</div>
        </div>
    </div>
    <div style="display:flex;flex-wrap:wrap;gap:8px 22px;font-size:14px;color:#111111;background:#f1f3f4;padding:12px 18px;border-radius:8px;border:1px solid #e0e0e0;font-weight:500;max-width:100%;box-sizing:border-box;">
        <span style="color:#111111;">🤖 模型演算法: <strong style="color:#111111;">{model_type}</strong></span>
        <span style="color:#111111;">📐 截距 (intercept): <strong style="color:#111111;">{intercept:.4f}</strong></span>
        <span style="color:#111111;">🗂️ 測試集比例: <strong style="color:#111111;">{test_size}</strong></span>
        <span style="color:#111111;">🎲 隨機種子: <strong style="color:#111111;">{seed}</strong></span>
    </div>
    """


def make_coef_chart(feature_coefs: dict[str, float]) -> str:
    """特徵權重係數橫條圖 (Feature Coefficients)。全部 inline style。"""
    if not feature_coefs:
        return "<p style='color:#111111;text-align:center;padding:20px;'>目前無特徵權重資料</p>"
    max_abs = max(abs(v) for v in feature_coefs.values()) or 1.0
    items = ['<div style="font-size:16px;font-weight:700;color:#111111;margin-bottom:10px;">⚖️ 特徵權重係數 (Feature Coefficients)</div>']
    for feat, val in feature_coefs.items():
        pct = abs(val) / max_abs * 100
        color = "#1a73e8" if val >= 0 else "#e37400"
        sign = "+" if val >= 0 else "-"
        label = FEATURE_LABELS.get(feat, feat)
        items.append(f"""
        <div style="width:100%;">
            <div style="display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px 8px;margin-bottom:5px;font-weight:600;font-size:14px;color:#111111;">
                <span style="color:#111111;">{label}</span>
                <span style="color:#111111;white-space:nowrap;">{sign}{abs(val):,.4f}</span>
            </div>
            <div style="background-color:#f1f3f4;border-radius:8px;height:12px;overflow:hidden;width:100%;">
                <div style="background-color:{color};width:{pct:.1f}%;height:100%;border-radius:8px;"></div>
            </div>
        </div>""")
    return ('<div style="display:flex;flex-direction:column;gap:12px;margin-top:4px;'
            'width:100%;max-width:100%;box-sizing:border-box;'
            'background-color:#ffffff;padding:14px;border-radius:10px;border:1px solid #e0e0e0;">'
            + "".join(items) + "</div>")


def make_error_html(msg: str) -> str:
    return f"<div style='background:#fce8e6;color:#c5221f;padding:20px;border-radius:12px;border:1.5px solid rgba(197,34,31,.3);text-align:center;font-weight:600;'>⚠️ {msg}</div>"


# ============================================
# 7. Gradio 互動函數 (直接在行程內呼叫業務邏輯，不再透過 HTTP)
# ============================================
def predict_gradio_handler(years_exp, edu, city):
    """即時預測：直接呼叫模型預測邏輯 (_predict_salary)。"""
    try:
        data = _predict_salary(float(years_exp), edu, city)
        card = make_prediction_card(
            data["predicted_salary"], data["model_type"], data["r2"]
        )
        bars = make_contribution_bars(data["feature_contribution"])
        return card, bars
    except Exception as e:
        err = f"預測失敗：{e}"
        return make_error_html(err), make_error_html("請確認模型已正確載入 (salary_model.joblib)")


def train_gradio_handler(model_type, alpha, test_size, random_state):
    """線上重新訓練：直接呼叫訓練邏輯 (_train_model)。"""
    try:
        data = _train_model(
            test_size=float(test_size),
            random_state=int(random_state),
            model_type=model_type,
            alpha=float(alpha),
        )
        status = (
            "### 📢 最新狀態: `✅ 線上重新訓練並載入成功！`\n"
            f"> {data.get('message', '')}"
        )
        metrics = make_metrics_card({
            "r2": data.get("r2"),
            "train_time": data.get("train_time"),
            "alpha": data.get("alpha"),
            "model_type": data.get("model_type"),
            "intercept": data.get("intercept"),
            "test_size": test_size,
            "random_state": random_state,
        })
        coef = make_coef_chart(data.get("feature_coefs", {}))
        return status, metrics, coef
    except Exception as e:
        err = f"訓練失敗：{e}"
        return (
            "### 📢 最新狀態: `❌ 線上訓練失敗`",
            make_error_html(err),
            make_error_html("請確認資料集 (Salary_Data2.csv) 與模型檔案正確"),
        )


def fetch_model_info():
    """取得目前模型狀態 (供初始畫面使用)，直接讀取記憶體中的 MODEL_STATE。"""
    try:
        return _get_model_info()
    except Exception:
        return None


# ============================================
# 8. 初始畫面內容 (直接讀取模型狀態，不需透過 HTTP 喚醒後端)
# ============================================
try:
    load_model_state()
except Exception as e:
    print(f"[警告] 模型載入失敗: {e}")

info = fetch_model_info()
if info:
    initial_metrics = make_metrics_card(info)
    initial_coefs = make_coef_chart(info.get("feature_coefs", {}))
    initial_status = f"### 📢 最新狀態: `✅ 模型已載入，目前模型為 {info.get('model_type')}`"
    default_model = info.get("model_type", "LinearRegression")
    default_alpha = info.get("alpha", 1.0)
    default_test_size = info.get("test_size", 0.2)
    default_seed = info.get("random_state", 76)
else:
    initial_metrics = make_error_html("無法載入模型狀態")
    initial_coefs = make_error_html("無法載入特徵權重資料")
    initial_status = "### 📢 最新狀態: `⚠️ 模型尚未載入`"
    default_model, default_alpha, default_test_size, default_seed = "LinearRegression", 1.0, 0.2, 76

try:
    pred_data = _predict_salary(5.0, "大學", "城市A")
    initial_card = make_prediction_card(
        pred_data["predicted_salary"], pred_data["model_type"], pred_data["r2"]
    )
    initial_bars = make_contribution_bars(pred_data["feature_contribution"])
except Exception:
    initial_card = make_error_html("無法載入預測卡片")
    initial_bars = make_error_html("無法載入特徵貢獻資料")


# ============================================
# 9. 建立 Gradio UI (RWD + 仿 Iris 風格)
# ============================================
with gr.Blocks(
    title="💰 Salary 薪資預測機器學習全生命週期平台",
) as demo:

    gr.HTML(RWD_CSS)

    gr.Markdown(
        """
        # 💰 Salary 薪資預測機器學習全生命週期平台
        本系統展示機器學習模型部署的**完整生命週期**。此服務將 **FastAPI** 與 **Gradio** 整合於單一執行行程：
        Gradio UI 直接掛載於 FastAPI 實例上，前端呼叫即為行程內的直接函式呼叫，無需額外的內部 HTTP 請求。
        * 🔮 **即時預測分頁**：輸入人員特徵 (工作年資、學歷、城市)，即時取得薪資預測與各特徵貢獻分析。
        * ⚙️ **線上訓練分頁**：可線上調整模型演算法與超參數，即時呼叫後端重新訓練並查看評估指標與特徵權重。
        """
    )

    with gr.Tabs():

        # ---------- 分頁一：即時預測 ----------
        with gr.Tab("🔮 即時薪資預測"):
            with gr.Row():
                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 1. 輸入人員特徵 (Features)")
                    years_exp = gr.Slider(minimum=0.0, maximum=40.0, value=5.0, step=0.5,
                                          label="工作年資 Years Experience (年)")
                    edu = gr.Dropdown(choices=EDU_CHOICES, value="大學",
                                      label="學歷 Education Level")
                    city = gr.Dropdown(choices=CITY_CHOICES, value="城市A",
                                       label="城市 City")
                    predict_btn = gr.Button("🔮 開始預測", variant="primary", size="lg")

                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 2. 預測結果與特徵貢獻分析")
                    output_card = gr.HTML(value=initial_card, label="薪資預測卡片")
                    output_bars = gr.HTML(value=initial_bars, label="特徵貢獻分析")

            inputs = [years_exp, edu, city]
            outputs = [output_card, output_bars]
            for widget in [years_exp, edu, city]:
                widget.change(fn=predict_gradio_handler, inputs=inputs, outputs=outputs)
            predict_btn.click(fn=predict_gradio_handler, inputs=inputs, outputs=outputs)

        # ---------- 分頁二：線上訓練 ----------
        with gr.Tab("⚙️ 線上模型訓練與評估"):
            with gr.Row():
                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 1. 調整模型與超參數")
                    model_type = gr.Dropdown(choices=MODEL_CHOICES, value=default_model,
                                             label="模型演算法 Model Type")
                    alpha = gr.Slider(minimum=0.01, maximum=100.0, value=default_alpha, step=0.01,
                                      label="正則化強度 alpha (適用於 Lasso 與 Ridge)")
                    test_size = gr.Slider(minimum=0.1, maximum=0.5, value=default_test_size, step=0.05,
                                          label="測試集分割比例 test_size")
                    seed = gr.Number(value=default_seed, label="隨機種子 random_state", precision=0)

                    train_btn = gr.Button("🚀 開始訓練模型", variant="primary", size="lg")

                with gr.Column(scale=1, min_width=320):
                    gr.Markdown("### 2. 訓練結果與特徵權重")
                    train_status = gr.Markdown(initial_status)
                    metrics_card = gr.HTML(value=initial_metrics, label="評估指標卡片")
                    coef_chart = gr.HTML(value=initial_coefs, label="特徵權重圖表")

            train_btn.click(
                fn=train_gradio_handler,
                inputs=[model_type, alpha, test_size, seed],
                outputs=[train_status, metrics_card, coef_chart],
            )


# ============================================
# 10. 掛載 Gradio UI 至 FastAPI 實例 (單一行程 / 單一 Port)
# ============================================
demo.queue()
app = gr.mount_gradio_app(
    app,
    demo,
    path="/",
    theme=gr.themes.Soft(primary_hue="teal", secondary_hue="indigo"),
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("🚀 啟動整合服務 (FastAPI + Gradio)，共用單一 Uvicorn 行程與單一 Port ...")
    print(f"   - Gradio UI:      http://127.0.0.1:{port}/")
    print(f"   - API 文件:       http://127.0.0.1:{port}/docs")
    print(f"   - 健康檢查:       GET /health")
    print(f"   - 訓練端點:       POST /train")
    print(f"   - 預測端點:       POST /predict")
    print(f"   - 模型資訊:       GET /model-info")
    uvicorn.run(app, host="0.0.0.0", port=port)
