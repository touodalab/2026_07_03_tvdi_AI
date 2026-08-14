
import os
import pandas as pd
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from sklearn.tree import DecisionTreeClassifier

# 保留的最終特徵欄位 (相對指標 + 衍生特徵)
FEATURES = [
    '20MA',
    'BIAS_20',       # 20日乖離率 (相對指標)
    'MA_diff',       # 均線差值 (衍生指標)
    'daily_return',  # 當日報酬率 (百分比)
    'amplitude',     # 振幅 (相對比例)
    'spread',        # 高低價差
    'week',          # 星期 (週期變數)
]


MODEL_PARAMS = {
    'criterion': 'gini',
    'max_depth': 3,
    'min_samples_split': 10,
    'min_samples_leaf': 5,
    'random_state': 42,
}

FILE_NAME = 'stocks_202101_202607.xlsx'
FOLDER = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="長榮海運明日漲跌預測 API", version="1.0.0")


class PredictionOut(BaseModel):
    date: str
    prediction: int
    signal: str
    prob_down: float
    prob_up: float
    accuracy: float


def load_data() -> pd.DataFrame:
    """載入原始交易資料，並刪除 MA5~MA20 與 Unnamed: 12 欄位。"""
    df = pd.read_excel(os.path.join(FOLDER, FILE_NAME))
    drop_cols = [f'MA{i}' for i in range(5, 21)] + ['Unnamed: 12']
    return df.drop(columns=drop_cols, errors='ignore')


def build_features(df: pd.DataFrame):
    """產生衍生特徵與目標變數，回傳 (X, y, df_clean)。"""
    df = df.drop_duplicates().copy()

    df['MA_5'] = df['close'].rolling(window=5).mean()
    df['BIAS_20'] = (df['close'] - df['20MA']) / df['20MA']
    df['MA_diff'] = df['MA_5'] - df['20MA']
    df['daily_return'] = df['close'].pct_change()
    df['amplitude'] = (df['max'] - df['min']) / df['open']
    df['target'] = (df['close'].shift(-1) > df['close']).astype(int)

    df_clean = df.dropna().copy()

    X = df_clean[FEATURES]
    y = df_clean['target']
    return X, y, df_clean


def train_model(X_train, y_train) -> DecisionTreeClassifier:
    """訓練決策樹模型並回傳。"""
    model = DecisionTreeClassifier(**MODEL_PARAMS)
    model.fit(X_train, y_train)
    return model

X, y, df_clean = build_features(load_data())
train_size = int(len(X) * 0.8)
X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

model = train_model(X_train, y_train)
TEST_ACCURACY = float(model.score(X_test, y_test))


@app.get("/", response_class=HTMLResponse)
def index():
    latest_feature = X.iloc[[-1]]
    pred = int(model.predict(latest_feature)[0])
    prob = model.predict_proba(latest_feature)[0]
    latest_date = str(df_clean['date'].iloc[-1])
    signal = "【買進 / 看漲】" if pred == 1 else "【觀望 / 看跌或平盤】"

    color = "#d32f2f" if pred == 1 else "#1976d2"
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>長榮海運 明日漲跌預測</title>
    <style>
        body {{
            font-family: "Microsoft JhengHei", "PingFang TC", sans-serif;
            background: #f4f6f8;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }}
        .card {{
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.1);
            padding: 40px 48px;
            text-align: center;
            max-width: 460px;
        }}
        h1 {{ font-size: 22px; margin: 0 0 8px; }}
        .date {{ color: #777; margin-bottom: 24px; }}
        .signal {{
            font-size: 30px;
            font-weight: bold;
            color: {color};
            margin: 16px 0 24px;
        }}
        .probs {{ display: flex; justify-content: space-around; gap: 16px; }}
        .prob {{ flex: 1; background: #f9fafb; border-radius: 10px; padding: 14px; }}
        .prob .label {{ font-size: 13px; color: #666; }}
        .prob .value {{ font-size: 22px; font-weight: bold; margin-top: 4px; }}
        .acc {{ margin-top: 24px; color: #999; font-size: 13px; }}
        a {{ color: #1976d2; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>長榮海運 (2603) 明日漲跌預測</h1>
        <div class="date">最新數據日期：{latest_date}</div>
        <div class="signal">{signal}</div>
        <div class="probs">
            <div class="prob">
                <div class="label">下跌 / 平盤機率</div>
                <div class="value" style="color:#1976d2">{prob[0] * 100:.2f}%</div>
            </div>
            <div class="prob">
                <div class="label">上漲機率</div>
                <div class="value" style="color:#d32f2f">{prob[1] * 100:.2f}%</div>
            </div>
        </div>
        <div class="acc">測試集準確率：{TEST_ACCURACY:.4f}</div>
        <div class="acc">API 文件：<a href="/docs">/docs</a></div>
    </div>
</body>
</html>"""
    return html


@app.get("/predict", response_model=PredictionOut)
def predict():
    """回傳明日漲跌預測結果 (JSON)。"""
    latest_feature = X.iloc[[-1]]
    pred = int(model.predict(latest_feature)[0])
    prob = model.predict_proba(latest_feature)[0]

    return PredictionOut(
        date=str(df_clean['date'].iloc[-1]),
        prediction=pred,
        signal="【買進 / 看漲】" if pred == 1 else "【觀望 / 看跌或平盤】",
        prob_down=round(prob[0], 4),
        prob_up=round(prob[1], 4),
        accuracy=round(TEST_ACCURACY, 4),
    )


@app.get("/health")
def health():
    return JSONResponse({"status": "ok", "rows": int(len(X))})


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
