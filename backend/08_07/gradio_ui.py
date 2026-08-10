# ============================================
# 薪資預測機器學習平台 - Gradio 前端 (RWD)
# UI 風格仿照 Iris 鳶尾花全生命週期平台：
# https://roberthsu2003-iris-predict-service.hf.space/
# 底層呼叫 FastAPI 後端 app.py (/predict, /train, /model-info)
# ============================================
import os
import requests
import gradio as gr

# ============================================
# 0. 後端 API 連線設定
# ============================================
import time
import threading

API_BASE = os.environ.get("SALARY_API_BASE", "http://127.0.0.1:8000")

# 喚醒後端的最長等待秒數 (Render 免費方案冷啟動可能需 1~2 分鐘)
BACKEND_WAKE_MAX = int(os.environ.get("BACKEND_WAKE_MAX", "120"))


def wake_up_backend(max_wait: int = BACKEND_WAKE_MAX, request_timeout: int = 5) -> bool:
    """啟動時喚醒 Render 後端並等待其就緒。

    Render 免費方案在閒置後會讓 Web Service 休眠，第一次連線會觸發冷啟動
    (約 30~120 秒)。此函式會持續呼叫後端健康檢查 (GET /)，直到後端回應成功。
    """
    if os.environ.get("SKIP_BACKEND_WAKE") == "1":
        return True
    url = f"{API_BASE}/"
    deadline = time.monotonic() + max_wait
    attempt = 0
    while time.monotonic() < deadline:
        attempt += 1
        try:
            resp = requests.get(url, timeout=request_timeout)
            if resp.ok:
                print(f"[WakeUp] ✅ 後端已就緒: {API_BASE} (第 {attempt} 次嘗試)")
                return True
        except requests.RequestException:
            pass
        wait = min(1.5 * attempt, 8)
        print(f"[WakeUp] ⏳ 等待後端啟動中 ({API_BASE})，第 {attempt} 次，{wait:.0f}s 後重試…")
        time.sleep(wait)
    print(f"[WakeUp] ❌ 等待逾時 ({max_wait}s)，後端仍無法連線: {API_BASE}")
    return False


def request_json(method: str, path: str, payload: dict | None = None, timeout: int = 30) -> dict:
    """呼叫後端 API；若第一次連線失敗(後端休眠)則喚醒後端並重試一次。"""
    def _do():
        if method.upper() == "GET":
            resp = requests.get(f"{API_BASE}{path}", timeout=timeout)
        else:
            resp = requests.post(f"{API_BASE}{path}", json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    try:
        return _do()
    except requests.RequestException as first_err:
        print(f"[WakeUp] 首次連線失敗 ({first_err})，嘗試喚醒後端後重試…")
        wake_up_backend()
        return _do()


# 後端保活間隔秒數：前端執行期間持續 ping 後端，避免 Render 後端再度休眠
BACKEND_KEEPALIVE_INTERVAL = int(os.environ.get("BACKEND_KEEPALIVE_INTERVAL", "30"))


def _keepalive_loop(interval: int = BACKEND_KEEPALIVE_INTERVAL):
    """背景執行緒：在前端程式存續期間，定期呼叫後端健康檢查保持其甦醒。"""
    while True:
        try:
            requests.get(f"{API_BASE}/", timeout=5)
        except requests.RequestException:
            pass
        time.sleep(interval)


def start_backend_keepalive(interval: int = BACKEND_KEEPALIVE_INTERVAL) -> None:
    """前端啟動時開啟『後端保活』背景執行緒 (daemon，程式結束即停止)。"""
    t = threading.Thread(target=_keepalive_loop, args=(interval,), daemon=True, name="backend-keepalive")
    t.start()
    print(f"[KeepAlive] 已啟動後端保活，每 {interval}s ping {API_BASE}/")


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

# ============================================
# 1. RWD (響應式網頁設計) 全域樣式
# 採用 CSS Grid + auto-fit + clamp() + media query 斷點
# ============================================
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
# 2. HTML 結果卡片生成函數 (仿 Iris 的 HTML 卡片)
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
            'width:100%;max-width:100%;box-sizing:border-box;">' + "".join(items) + "</div>")


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
            'width:100%;max-width:100%;box-sizing:border-box;">' + "".join(items) + "</div>")


def make_error_html(msg: str) -> str:
    return f"<div style='background:#fce8e6;color:#c5221f;padding:20px;border-radius:12px;border:1.5px solid rgba(197,34,31,.3);text-align:center;font-weight:600;'>⚠️ {msg}</div>"


# ============================================
# 3. 後端 API 呼叫函數
# ============================================

def _post_json(path: str, payload: dict, timeout: int = 120):
    """後端在 Render 休眠時會先喚醒並等待就緒，再重試一次。"""
    return request_json("POST", path, payload=payload, timeout=timeout)


def predict_gradio_handler(years_exp, edu, city):
    """即時預測：呼叫後端 /predict"""
    try:
        data = _post_json("/predict", {
            "YearsExperience": float(years_exp),
            "EducationLevel": edu,
            "City": city,
        }, timeout=30)
        card = make_prediction_card(
            data["predicted_salary"], data["model_type"], data["r2"]
        )
        bars = make_contribution_bars(data["feature_contribution"])
        return card, bars
    except Exception as e:
        err = f"無法連線後端 {API_BASE} 或預測失敗：{e}"
        return make_error_html(err), make_error_html("請確認後端 app.py 已啟動 (uvicorn app:app)")


def train_gradio_handler(model_type, alpha, test_size, random_state):
    """線上重新訓練：呼叫後端 /train"""
    try:
        data = _post_json("/train", {
            "test_size": float(test_size),
            "random_state": int(random_state),
            "model_type": model_type,
            "alpha": float(alpha),
        })
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
        err = f"無法連線後端 {API_BASE} 或訓練失敗：{e}"
        return (
            "### 📢 最新狀態: `❌ 線上訓練失敗`",
            make_error_html(err),
            make_error_html("請確認後端 app.py 已啟動 (uvicorn app:app)"),
        )


def fetch_model_info():
    """取得目前模型狀態 (供初始畫面使用)，後端休眠時會先喚醒。"""
    try:
        return request_json("GET", "/model-info", timeout=10)
    except requests.RequestException:
        return None


# ============================================
# 4. 初始畫面內容 (後端未啟動則顯示佔位內容)
# ============================================
# 啟動前端時先喚醒 Render 後端 (含冷啟動等待)，再載入初始資料；
# 並開啟保活執行緒，讓後端在服務期間保持甦醒
wake_up_backend()
start_backend_keepalive()
info = fetch_model_info()
if info:
    initial_metrics = make_metrics_card(info)
    initial_coefs = make_coef_chart(info.get("feature_coefs", {}))
    initial_status = f"### 📢 最新狀態: `✅ 已連線後端，目前模型為 {info.get('model_type')}`"
    default_model = info.get("model_type", "LinearRegression")
    default_alpha = info.get("alpha", 1.0)
    default_test_size = info.get("test_size", 0.2)
    default_seed = info.get("random_state", 76)
else:
    initial_metrics = make_error_html(f"無法連線後端 {API_BASE}")
    initial_coefs = make_error_html("無法載入特徵權重資料")
    initial_status = "### 📢 最新狀態: `⚠️ 尚未連線後端，請先啟動 app.py`"
    default_model, default_alpha, default_test_size, default_seed = "LinearRegression", 1.0, 0.2, 76

try:
    pred_resp = _post_json("/predict", {
        "YearsExperience": 5.0, "EducationLevel": "大學", "City": "城市A",
    }, timeout=30)
    pred_data = pred_resp
    initial_card = make_prediction_card(
        pred_data["predicted_salary"], pred_data["model_type"], pred_data["r2"]
    )
    initial_bars = make_contribution_bars(pred_data["feature_contribution"])
except requests.RequestException:
    initial_card = make_error_html(f"無法連線後端 {API_BASE}")
    initial_bars = make_error_html("無法載入特徵貢獻資料")


# ============================================
# 5. 建立 Gradio UI (RWD + 仿 Iris 風格)
# ============================================
with gr.Blocks(
    title="💰 Salary 薪資預測機器學習全生命週期平台",
    theme=gr.themes.Soft(primary_hue="teal", secondary_hue="indigo"),
) as demo:

    gr.HTML(RWD_CSS)

    gr.Markdown(
        """
        # 💰 Salary 薪資預測機器學習全生命週期平台
        本系統展示機器學習模型部署的**完整生命週期**。此服務底層使用 **FastAPI** 驅動的 RESTful API，並結合 **Gradio** 開發了互動式 Web 介面。
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 啟動 Gradio 前端，後端 API: {API_BASE}")
    demo.queue().launch(server_name="0.0.0.0", server_port=port)
