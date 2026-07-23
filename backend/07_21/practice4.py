# =============================================================================
# 台灣股票資料 API（FastAPI + yfinance）
# =============================================================================
# 本檔案建立一個 FastAPI 應用程式，提供以下功能：
#   1. 首頁（/）— 以 HTML 表單讓使用者輸入股票代碼與查詢期間
#   2. 查詢 API（/stock）— 回傳指定股票在指定期間內的歷史股價 JSON 資料
#   3. Swagger 文件（/docs）— FastAPI 自動產生的 API 互動式文件
#
# 使用方式：
#   python practice4.py
#   或 uvicorn practice4:app --reload
#   開啟瀏覽器至 http://127.0.0.1:8000 即可看到查詢頁面
# =============================================================================

# --- 標準函式庫 ---
from enum import Enum  # 用於建立固定的列舉型別，限制可選的查詢期間

# --- 第三方套件 ---
import yfinance as yf  # Yahoo Finance 股票資料來源
from fastapi import FastAPI, HTTPException, Query  # FastAPI 核心元件
from fastapi.responses import HTMLResponse  # 用於回傳 HTML 頁面


# ---------------------------------------------------------------------------
# 建立 FastAPI 應用程式實例
# ---------------------------------------------------------------------------
# title / description / version 會顯示在 Swagger UI（/docs）頁面上
app = FastAPI(
    title="台灣股票資料 API",
    description="依股票代碼查詢最近 1 天、1 星期、1 個月或 1 年的股價。",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# 查詢期間列舉（StockPeriod）
# ---------------------------------------------------------------------------
# 繼承 str 與 Enum，使其同時具備字串比較能力與列舉的型別安全。
# yfinance 的 history() 方法接受 "1d"、"5d"、"1mo"、"1y" 等期間代碼。
class StockPeriod(str, Enum):
    """yfinance 支援的查詢期間。"""

    one_day = "1d"      # 最近 1 個交易日
    one_week = "5d"     # 最近 5 個交易日（約 1 星期）
    one_month = "1mo"   # 最近 1 個月
    one_year = "1y"     # 最近 1 年


# ---------------------------------------------------------------------------
# 期間代碼 → 中文標籤對照表
# ---------------------------------------------------------------------------
# 用於在 API 回傳結果中提供人類可讀的中文期間說明
PERIOD_LABELS = {
    StockPeriod.one_day: "1 天",
    StockPeriod.one_week: "1 星期",
    StockPeriod.one_month: "1 個月",
    StockPeriod.one_year: "1 年",
}


# ---------------------------------------------------------------------------
# 核心函式：取得股票歷史資料
# ---------------------------------------------------------------------------
def get_stock_history(
    stock_code: str, period: StockPeriod
) -> list[dict[str, object]]:
    """
    使用 yfinance 取得台灣股票的歷史股價。

    參數：
        stock_code (str): 股票代碼，如 "2330"（台積電）、"2317"（鴻海）
        period (StockPeriod): 查詢期間列舉值

    回傳：
        list[dict]: 每筆交易日的開盤價、最高價、最低價、收盤價與成交量
    """
    # 台灣上市股票在 Yahoo Finance 的代碼格式為「代碼.TW」
    symbol = f"{stock_code}.TW"

    # 透過 yfinance Ticker 物件取得歷史資料（回傳 pandas DataFrame）
    history = yf.Ticker(symbol).history(period=period.value)

    # 將 DataFrame 的每一列轉換為 dict，方便 FastAPI 序列化為 JSON
    records: list[dict[str, object]] = []
    for date, row in history.iterrows():
        records.append(
            {
                "date": date.isoformat(),       # 日期轉為 ISO 8601 字串
                "open": float(row["Open"]),      # 開盤價
                "high": float(row["High"]),      # 最高價
                "low": float(row["Low"]),        # 最低價
                "close": float(row["Close"]),    # 收盤價
                "volume": int(row["Volume"]),    # 成交量（股）
            }
        )
    return records


# ---------------------------------------------------------------------------
# 路由 1：首頁（/）— 提供 HTML 表單查詢介面
# ---------------------------------------------------------------------------
# response_class=HTMLResponse：告訴 FastAPI 回傳原始 HTML 而非 JSON
# include_in_schema=False：不在 Swagger 文件中顯示此路由
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    """顯示簡單的股票期間查詢頁面。"""
    return """
    <!doctype html>
    <html lang="zh-Hant">
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>台灣股票資料</title>
      </head>
      <body>
        <h1>台灣股票資料</h1>
        <!-- 表單以 GET 方式提交至 /stock 端點 -->
        <form action="/stock" method="get">
          <!-- 股票代碼輸入欄：4~6 碼數字，如 2330、0050 -->
          <label for="stock_code">股票代碼：</label>
          <input id="stock_code" name="stock_code" value="2330"
                 pattern="[0-9]{4,6}" maxlength="6" required>
          <br><br>
          <!-- 查詢期間下拉選單 -->
          <label for="period">查詢期間：</label>
          <select id="period" name="period">
            <option value="1d">1 天</option>
            <option value="5d">1 星期</option>
            <option value="1mo">1 個月</option>
            <option value="1y">1 年</option>
          </select>
          <button type="submit">查詢</button>
        </form>
        <!-- 連結至 FastAPI 自動產生的 Swagger API 文件 -->
        <p>API 文件：<a href="/docs">/docs</a></p>
      </body>
    </html>
    """


# ---------------------------------------------------------------------------
# 路由 2：股票查詢 API（/stock）— 回傳 JSON 格式的歷史股價
# ---------------------------------------------------------------------------
# Query() 用於定義查詢參數的預設值、驗證規則與說明文字，
# 這些資訊會自動出現在 Swagger UI 中，方便前端或其他開發者了解用法。
@app.get("/stock", summary="查詢台灣股票歷史股價")
def read_stock(
    stock_code: str = Query(
        default="2330",                              # 預設查詢台積電
        pattern=r"^[0-9]{4,6}$",                     # 正規表達式驗證：4~6 位數字
        description="台灣股票代碼，例如：2330、2317、0050",
    ),
    period: StockPeriod = Query(
        default=StockPeriod.one_month,               # 預設查詢 1 個月
        description="查詢期間：1d、5d、1mo 或 1y",
    ),
) -> dict[str, object]:
    """依股票代碼及指定期間回傳開、高、低、收與成交量。"""
    symbol = f"{stock_code}.TW"

    # 嘗試取得股票資料；若 yfinance 發生錯誤（如網路中斷），回傳 502
    try:
        data = get_stock_history(stock_code, period)
    except Exception as exc:
        raise HTTPException(status_code=502, detail="目前無法取得股票資料") from exc

    # 若查詢結果為空（如代碼不存在或該期間無交易資料），回傳 404
    if not data:
        raise HTTPException(status_code=404, detail="查無股票資料")

    # 回傳完整的查詢結果 JSON
    return {
        "stock_code": stock_code,         # 使用者輸入的股票代碼
        "symbol": symbol,                 # Yahoo Finance 格式的代碼（如 2330.TW）
        "period": period.value,           # 期間代碼（1d、5d 等）
        "period_label": PERIOD_LABELS[period],  # 期間中文標籤
        "count": len(data),               # 查詢到的交易日筆數
        "data": data,                     # 歷史股價陣列
    }


# ---------------------------------------------------------------------------
# 直接執行本檔案時，啟動 uvicorn 開發伺服器
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn  # ASGI 伺服器，用於執行 FastAPI 應用

    uvicorn.run(app, host="127.0.0.1", port=8000)