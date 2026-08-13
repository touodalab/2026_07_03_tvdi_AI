# PRD：薪資模型資料來源由 CSV 遷移至 Render PostgreSQL

## 1. 文件目的

本文件是一份**產品需求文件（PRD）**，用於指示「其他 AI 模型」（以下稱「執行模型」）完成一項程式碼遷移任務：

- **舊專案**：`backend/08_11/`
- **核心變更**：模型重新訓練時，**不再讀取 `Salary_Data2.csv` 作為資料集**，改為讀取 **Render 雲端 PostgreSQL** 伺服器中的資料表。
- **執行者**：任一被指定的 AI 模型。
- **完成前提**：所有變更完成後，必須**驗證連線方式**並確認模型可以正常重新訓練。

執行模型必須**完全依照本 PRD 的所有要求**，內容愈詳細愈好，不可省略任何步驟與驗證。

---

## 2. 背景說明

### 2.1 現況（遷移前）

- `backend/08_11/train_save.py` 中，`train_and_save_model()` 函式目前透過下列程式碼讀取資料集：

  ```python
  csv_path = os.path.join(current_dir, "Salary_Data2.csv")
  data = pd.read_csv(csv_path)
  ```

- 資料集 `Salary_Data2.csv` 欄位為：`YearsExperience`、`EducationLevel`、`City`、`Salary`。
- 模型使用的工作流程：
  1. `train_save.py` → 訓練並儲存 `salary_model.joblib`
  2. `app.py` → FastAPI + Gradio 平台，提供 `/train`、`/predict`、`/model-info`、`/health`
  3. 使用 `OrdinalEncoder`（學歷）、`OneHotEncoder`（城市）、`StandardScaler`（標準化）、線性迴歸系（LinearRegression / Lasso / Ridge）

### 2.2 目標（遷移後）

- 模型重新訓練時，從 **Render PostgreSQL** 的 `salary_data2` 資料表讀取相同欄位的資料。
- 不修改特徵工程、模型演算法與儲存格式，只更換「資料來源」。
- 連線資訊透過 **`.env`** 保護，不可寫死在程式碼中。

---

## 3. 現況盤點（已由 MCP server「postgres」確認）

> 執行模型可以使用 MCP server `postgres`（對應 Render PostgreSQL `tvdi_db`）查詢資料庫。以下為已確認之資訊，可直接沿用。

### 3.1 Render PostgreSQL 連線資訊

- **連線字串（Connection String）**（此為 opencode.json 中 MCP 設定值）：

  ```
  postgresql://tvdi_db_user:Pf4Z9Kkm2o8C1XL4e0WArY4GbM2yIbSE@dpg-d9u2qsjm8hqs73ecntug-a.singapore-postgres.render.com/tvdi_db?sslmode=require
  ```

- **資料庫**：`tvdi_db`
- **MCP server 名稱**：`postgres`（opencode.json 內已設定，`--connection-string` 同上）

### 3.2 資料表架構（已查詢確認）

**資料表：`salary_data2`（72 筆資料）**

| 欄位 | 資料型態 | 說明 |
| --- | --- | --- |
| `YearsExperience` | real | 工作年資（年），模型特徵 |
| `EducationLevel` | character varying | 學歷（高中以下、大學、碩士以上），模型特徵 |
| `City` | character varying | 城市（城市A、城市B、城市C），模型特徵 |
| `Salary` | real | 年薪（萬元），目標變數 y |

資料範例（前 5 筆）：

| YearsExperience | EducationLevel | City | Salary |
| --- | --- | --- | --- |
| 3 | 大學 | 城市A | 45.9 |
| 7.8 | 碩士以上 | 城市C | 80.5 |
| 2.3 | 高中以下 | 城市A | 25.2 |
| 5.1 | 高中以下 | 城市A | 30.4 |
| 10 | 碩士以上 | 城市B | 65.7 |

**資料表：`houseprice`（500 筆資料）**（與本次任務無直接關係，僅供參考）

| 欄位 | 資料型態 |
| --- | --- |
| 犯罪率、豪宅比、公設比、NO濃度、房間數、屋齡、賣場距離、師生比、低收入比、房價 | real |
| 臨公園、捷運距離、繳稅率 | integer |

### 3.3 參考專案（backend/08_13）

- `backend/08_13/` 內有一個小專案，已示範「Python 連結 Render PostgreSQL」的正確做法：
  - `.env` 檔（內容只有一行：`POSTGRES_URL=postgresql://...?sslmode=require`）
  - `.gitignore`（內容：`.env`）
  - `python連結 postgres.md`（完整教學文件）
- 執行模型應**參考此專案的連線寫法**（`load_dotenv()` + `os.getenv("POSTGRES_URL")` + `psycopg2.connect()`）。

### 3.4 目前 backend/08_13/.env 內容（供複製參考）

```
POSTGRES_URL=postgresql://tvdi_db_user:Pf4Z9Kkm2o8C1XL4e0WArY4GbM2yIbSE@dpg-d9u2qsjm8hqs73ecntug-a.singapore-postgres.render.com/tvdi_db?sslmode=require
```

---

## 4. 目標對象

- 本 PRD 是寫給 **執行模型（AI）** 看的任務指示。
- 最終使用者為**學生**，因此所有程式碼必須可實際執行、易於理解。
- 任務產物落在兩個資料夾：`backend/08_11/`（主要修改 + 使用 .env）、`backend/08_13/`（參考，不修改）。

---

## 5. 功能需求（詳細步驟）

### 5.1 步驟一：建立 / 更新 `.env` 檔案（保護密碼）

1. 檢查 `backend/08_11/` 是否已有 `.env`：
   - 若無，建立一個新的 `.env` 檔案。
   - 若有，直接更新內容。
2. `.env` 內容（與 `backend/08_13/.env` 相同）：
   ```
   POSTGRES_URL=postgresql://tvdi_db_user:Pf4Z9Kkm2o8C1XL4e0WArY4GbM2yIbSE@dpg-d9u2qsjm8hqs73ecntug-a.singapore-postgres.render.com/tvdi_db?sslmode=require
   ```
3. **注意事項**：
   - `=` 兩側不要加空格。
   - 值含 `?sslmode=require`，不要漏掉後綴。
   - 不要把真實密碼寫進任何 `.py` 檔案。

### 5.2 步驟二：確認 / 更新 `.gitignore` 檔案

1. 檢查 `backend/08_11/.gitignore` 是否存在且內容包含 `.env`。
2. 若不存在或缺少，建立／更新為：
   ```
   .env
   ```
3. 目的：防止密碼被 commit 上傳到 GitHub。

### 5.3 步驟三：安裝所需 Python 套件

在 `backend/08_11/` 中確認已安裝以下套件（若 `requirements.txt` 有列出則不需重複安裝）：

```
pip install psycopg2-binary python-dotenv pandas scikit-learn joblib
```

- `psycopg2-binary`：Python 連 PostgreSQL 的驅動程式。
- `python-dotenv`：讀取 `.env` 檔。
- `pandas`、`scikit-learn`、`joblib`：原專案既有的資料處理與模型套件。

執行模型應一併更新 `backend/08_11/requirements.txt`，加入 `psycopg2-binary` 與 `python-dotenv`。

### 5.4 步驟四：修改 `backend/08_11/train_save.py`

在 `train_and_save_model()` 中，將「讀取 CSV」改為「讀取 PostgreSQL」：

1. 在檔案頂端加入 import：
   ```python
   import os
   from dotenv import load_dotenv
   import psycopg2
   ```
   （`os`、`pandas` 已存在，不需重複加入。）
2. 在讀取資料前呼叫：
   ```python
   load_dotenv()
   ```
3. 以 SQL 讀取資料取代 `pd.read_csv(csv_path)`：
   ```python
   connection_string = os.getenv("POSTGRES_URL")
   if connection_string is None:
       raise RuntimeError("找不到 POSTGRES_URL，請確認 .env 檔案是否存在且內容正確。")

   conn = psycopg2.connect(connection_string)
   data = pd.read_sql_query("SELECT YearsExperience, EducationLevel, City, Salary FROM salary_data2", conn)
   conn.close()
   ```
4. **保留以下不變**：
   - `OrdinalEncoder` / `OneHotEncoder` / `StandardScaler` 的設定與順序。
   - `feature_names`（`['YearsExperience', 'EducationLevel', 'City_城市A', 'City_城市B', 'City_城市C']`）。
   - `train_test_split`、模型選擇、`joblib.dump`、回傳字典結構。
5. **錯誤處理**：
   - 連線失敗時拋出清楚的異常訊息（例如連線字串錯誤、資料表不存在、資料庫休眠）。
   - 若 `SELECT` 回傳 0 筆資料，應拋出異常，避免訓練出空模型。

> 建議把「取得資料」抽成一個獨立函式（例如 `load_dataset_from_db()`），讓 `train_and_save_model()` 更清楚易讀。

### 5.5 步驟五：修改 `backend/08_11/app.py`（如需要）

- `app.py` 目前透過 `from train_save import train_and_save_model` 呼叫訓練邏輯，**不需要大幅修改**。
- 僅需確認：
  - `app.py` 同樣需要 `load_dotenv()` 才能讓內部呼叫的訓練函式讀到環境變數（若 `train_save.py` 內已有 `load_dotenv()` 則可省略）。
  - `app.py` 中參考 `Salary_Data2.csv` 的錯誤訊息文案（例如 `train_gradio_handler` 中的「請確認資料集 (Salary_Data2.csv) 與模型檔案正確」）應改為「請確認 PostgreSQL 連線與 salary_data2 資料表正確」。
- 若有其他檔案（`gradio_app.py`、`gradio_ui.py`、`test1.py`）讀取 CSV，執行模型應一併檢查並確認是否也需要修改（以 `grep` 搜尋 `Salary_Data2.csv` 與 `read_csv`）。

### 5.6 步驟六：複製 `.env` 至 `backend/08_11/`

- 依需求，**若任務中使用到 `.env`**（本任務確實會用到），必須把 `.env` 複製一份至 `backend/08_11/`（主要專案資料夾）：
  ```
  copy backend/08_13/.env backend/08_11/.env
  ```
- 並確認 `backend/08_11/.gitignore` 包含 `.env`（若無則建立）。
- 目的：`backend/08_11` 的 `train_save.py` 與 `app.py` 需要讀取 `.env` 中的 `POSTGRES_URL` 才能連上同一台 PostgreSQL。

### 5.7 步驟七：驗證連線方式（必做）

完成所有程式碼修改後，**必須**執行以下驗證：

1. **直接連線驗證**（參考 `backend/08_13/python連結 postgres.md` 的做法）：
   - 寫一個一次性驗證腳本（例如 `backend/08_11/verify_db.py`，或直接在 Python REPL 執行）：
     ```python
     from dotenv import load_dotenv
     import os, psycopg2

     load_dotenv()
     url = os.getenv("POSTGRES_URL")
     print("連線字串已讀取：", url[:40], "...")
     conn = psycopg2.connect(url)
     cur = conn.cursor()
     cur.execute("SELECT version();")
     print("✅ PostgreSQL 版本：", cur.fetchone()[0])
     cur.execute("SELECT count(*) FROM salary_data2;")
     print("✅ salary_data2 筆數：", cur.fetchone()[0])
     cur.close()
     conn.close()
     print("✅ 連線驗證通過")
     ```
   - 預期輸出：連線字串有讀到、PostgreSQL 版本印出、筆數為 72。
2. **訓練驗證**：
   - 執行 `python train_save.py`，確認：
     - 不會再報 `FileNotFoundError`（找不到 Salary_Data2.csv）。
     - 能成功讀取資料庫資料並完成訓練。
     - `salary_model.joblib` 成功產出／更新。
3. **API 驗證**：
   - 執行 `python app.py`，確認服務正常啟動。
   - 呼叫 `/health`、`/model-info`、`/train`、`/predict` 確認功能正常。
   - 特別確認 `/train` 重新訓練後，`/model-info` 的 R² 數值有更新。

### 5.8 步驟八：清理

- 確認 `Salary_Data2.csv` 是否仍被任何程式碼引用。
- 若不再需要，可保留檔案（不刪除，避免影響他人），但程式碼不得再依賴它。

### 5.9 步驟九：程式碼審查（Code Review）（必做）

完成步驟一至八後，執行模型**必須**以「審查者」角度重新檢視所有變更，找出問題並修正。審查需涵蓋以下項目：

1. **審查範圍**：
   - 本次修改的核心檔案：`backend/08_11/train_save.py`、`backend/08_11/app.py`。
   - 新增／更新的設定檔：`backend/08_11/.env`、`backend/08_11/.gitignore`、`backend/08_11/requirements.txt`。
   - 其他可能引用 CSV 的檔案（`gradio_app.py`、`gradio_ui.py`、`test1.py`、`run.py`）。

2. **審查項目（Checklist）**：

   **A. 密碼安全**
   - [ ] 所有 `.py` 檔案中不得出現連線字串、帳號或密碼明文。
   - [ ] 連線字串一律透過 `load_dotenv()` + `os.getenv("POSTGRES_URL")` 讀取。
   - [ ] `.gitignore` 確實包含 `.env`。
   - [ ] `.env` 與 `.env.example` 區分正確（若 `.env.example` 存在，其值必須是假的）。

   **B. 資料庫連線正確性**
   - [ ] 使用 `psycopg2.connect()` 建立連線。
   - [ ] 連線失敗時拋出清楚、可判讀的錯誤訊息（含原因）。
   - [ ] `cursor` 與 `connection` 在所有路徑下都會被正確關閉（建議使用 `try/finally` 或 `with` 區塊，避免例外發生時資源未釋放）。
   - [ ] 缺少 `POSTGRES_URL` 時有明確的例外提示。

   **C. SQL 安全性**
   - [ ] 本任務 SQL 為固定字串（`SELECT "YearsExperience", "EducationLevel", "City", "Salary" FROM salary_data2`），若未來加入動態條件，必須使用參數化查詢（`%s` 佔位符），禁止直接拼接使用者輸入。

   **D. 資料正確性**
   - [ ] 查詢欄位名稱與 `salary_data2` 表 schema 一致（大小寫注意：`YearsExperience`、`EducationLevel`、`City`、`Salary`）。
   - [ ] 查詢結果為 0 筆時會拋出例外，避免訓練出空模型。

   **E. 向後相容**
   - [ ] `train_and_save_model()` 的函式簽名與回傳字典格式完全未變。
   - [ ] `feature_names`、`OrdinalEncoder`／`OneHotEncoder`／`StandardScaler` 的設定與順序未變。
   - [ ] `app.py` 的 `/train`、`/predict`、`/model-info`、`/health` 端點行為不變。

   **F. 程式碼品質**
   - [ ] 註解與錯誤訊息使用繁體中文。
   - [ ] 無殘留讀取 `Salary_Data2.csv` 的程式碼或誤導性錯誤訊息。
   - [ ] 程式碼風格與原專案一致（縮排、命名、import 順序）。

3. **審查產出**：
   - 執行模型必須產出一份「**程式碼審查報告**」，記錄每項檢查的結果（通過／不通過），並說明不通過項目的修正方式。
   - 所有不通過項目必須在交付前修正完成並複驗。

---

## 6. 非功能需求

1. **密碼安全**：連線字串一律從 `.env` 讀取，禁止寫死在 `.py` 檔中。
2. **向後相容**：不改變 `train_and_save_model()` 的回傳格式，`app.py`、`gradio` 相關介面不得受影響。
3. **可執行性**：所有提供之程式碼必須真實可用，執行模型應實際執行驗證。
4. **清楚易懂**：程式碼要保留註解（中文），說明每個步驟在做什麼。
5. **語言**：程式碼註解與錯誤訊息使用繁體中文。
6. **完整性**：任務完成後，`backend/08_11/` 的 `.env` 與 `.gitignore` 都必須存在且正確。

---

## 7. 驗收標準（Acceptance Criteria）

以下條件**全部**符合才算完成：

1. `backend/08_11/train_save.py` 不再使用 `pd.read_csv` 讀取 `Salary_Data2.csv`，改為從 PostgreSQL `salary_data2` 讀取。
2. `backend/08_11/.env` 存在，內容為正確的 `POSTGRES_URL`（與 `backend/08_13/.env` 一致）。
3. `backend/08_11/.gitignore` 存在且包含 `.env`。
4. `backend/08_11/.env` 存在且內容正確（與 `backend/08_13/.env` 一致）。
5. `backend/08_11/requirements.txt` 已加入 `psycopg2-binary`、`python-dotenv`。
6. 執行 `python train_save.py` 成功，`salary_model.joblib` 更新成功，且無 `FileNotFoundError`。
7. 執行 `python app.py` 成功，`/train` 與 `/predict` 功能正常。
8. `app.py`（及任何其他 .py）中已無「`Salary_Data2.csv` 讀取」的程式碼與誤導性錯誤訊息。
9. 連線驗證腳本執行通過（PostgreSQL 版本 + `salary_data2` 筆數 72）。
10. **程式碼審查完成**：依 §5.9 之 Checklist 逐項審查，所有項目通過，或已完成修正並複驗；且產出「程式碼審查報告」。

---

## 8. Render 部署（Deployment）

> 本章節指示執行模型（或使用者）將 `backend/08_11` 部署到 Render 雲端平台。部署**必須**使用完整且正確的 `requirements.txt`，並透過 Render 環境變數注入 `POSTGRES_URL`，不得將密碼寫入程式碼或上傳 GitHub。

### 8.1 部署前準備

1. **確認 `requirements.txt` 完整**：必須包含專案實際使用之所有第三方套件。已比對確認內容如下（請以此為準，若有新增套件須同步更新）：
   ```
   fastapi>=0.139.0
   uvicorn>=0.51.0
   pydantic>=2.13.4
   scikit-learn>=1.9.0
   pandas>=2.0.0
   numpy>=1.24.0
   joblib>=1.5.3
   gradio>=6.20.0
   requests>=2.34.2
   psycopg2-binary>=2.9.10
   python-dotenv>=1.0.1
   ```
2. **確認 `.gitignore`**：必須包含 `.env`，確保密碼不會上傳 GitHub。
3. **將專案推上 GitHub**：確認 `backend/08_11/` 已 commit 並 push 至遠端 repo（`.env` 不得在 push 內容中）。
4. **確認部署入口**：Render 的 Start Command 使用 `python app.py`；`app.py` 已讀取 `PORT` 環境變數（`os.environ.get("PORT", 8000)`）並監聽 `0.0.0.0`。

### 8.2 建立 Render Web Service

1. 登入 https://render.com → 儀表板 → 點擊 **New** → **Web Service**。
2. 選擇要部署的 GitHub repository（本專案 `backend/08_11`）。
3. 填寫基本設定：
   | 欄位 | 建議值 | 說明 |
   | --- | --- | --- |
   | Name | `salary-predict-service` | 服務名稱（自訂） |
   | Runtime | `Python 3` | 由 Render 自動偵測 |
   | Region | 與資料庫 `tvdi_db` 相同（新加坡 Singapore） | 降低延遲 |
   | Branch | `main` | 部署分支 |
   | Build Command | `pip install -r requirements.txt` | 安裝依賴 |
   | Start Command | `python app.py` | 啟動整合服務 (FastAPI + Gradio) |
   | Instance Type | `Free` | 練習用免費方案（閒置會休眠） |
4. 展開 **Advanced** → 確認無需額外設定（Dockerfile 非必要）。
5. 點擊 **Create Web Service**，等待首次部署（約數分鐘）。

### 8.3 設定環境變數（重要）

部署完成後（或建立時），在服務的 **Environment** 分頁加入：

| Key | Value | 說明 |
| --- | --- | --- |
| `POSTGRES_URL` | `postgresql://tvdi_db_user:...@dpg-d9u2qsjm8hqs73ecntug-a.singapore-postgres.render.com/tvdi_db?sslmode=require` | Render PostgreSQL 連線字串（與 `.env` 相同） |

- Render 會自動注入 `PORT` 環境變數，無需手動設定。
- 儲存後 Render 會重新部署（Deploy）一次，請等待部署成功。

### 8.4 驗證部署結果

部署成功後，於瀏覽器開啟 Render 提供的網址（例如 `https://salary-predict-service.onrender.com`），驗證以下項目：

| 驗證項目 | 網址 / 方式 | 預期結果 |
| --- | --- | --- |
| 健康檢查 | `GET /health` | 回傳 `{"status":"ok","service":"salary-predict-api","docs":"/docs"}` |
| API 文件 | `GET /docs` | 顯示 Swagger 文件 |
| 模型資訊 | `GET /model-info` | 回傳模型類型、R²、特徵等 |
| 預測 | `POST /predict` | 輸入 `YearsExperience`、`EducationLevel`、`City`，回傳預測年薪 |
| 線上訓練 | `POST /train` | 重新訓練成功並回傳 R² |
| Gradio UI | 根路徑 `/` | 顯示薪資預測平台介面 |

### 8.5 部署注意事項

1. **免費方案休眠**：Render Free 方案在閒置一段時間後會休眠，下次請求會先喚醒（需等待 30~60 秒），此屬正常現象。
2. **資料庫連線**：訓練端 `/train` 會連線到 `tvdi_db`，若資料庫休眠需等待喚醒；連線字串務必含 `?sslmode=require`。
3. **環境變數來源**：Render 上的 `POSTGRES_URL` 是唯一的連線來源；本機 `.env` 僅供本地開發，兩者值必須一致。
4. **`salary_model.joblib`**：模型檔可隨 repo 上傳（不含機密），首次啟動若存在則直接載入，不需重新訓練。

### 8.6 使用 `render.yaml`（Blueprint）部署 — Step by Step

> 此法會讓 Render 讀取 repo 內 `backend/08_11/render.yaml` 自動建立服務，重複部署時設定保持一致。以下為完整操作步驟。

**步驟 0：確認檔案齊全（部署前檢查）**

在推上 GitHub 之前，先確認 `backend/08_11/` 內有以下檔案：
- [ ] `render.yaml`（Blueprint 設定檔，已提供）
- [ ] `requirements.txt`（完整套件清單，已提供）
- [ ] `app.py`（入口程式，Start Command 會執行它）
- [ ] `.gitignore`（內含 `.env`）
- [ ] `salary_model.joblib`（可選，模型檔）

**步驟 1：把 repo 推到 GitHub**

1. 在終端機切換到專案根目錄（`2026_07_03_tvdi_AI/`）。
2. 確認 Git 狀態與本次要提交的變更：
   ```
   git status
   ```
3. 確認 `.env` **沒有**被列在要提交的清單中（若有，代表 `.gitignore` 未生效，先修正再繼續）。
4. 加入與提交 `backend/08_11` 的變更：
   ```
   git add backend/08_11
   git commit -m "加入 render.yaml 與部署設定"
   ```
5. 推送到 GitHub：
   ```
   git push
   ```
6. 到 GitHub 網頁確認 `backend/08_11/render.yaml` 已經出現。

**步驟 2：進入 Render Blueprint 頁面**

1. 瀏覽器開啟 **https://render.com**。
2. 登入帳號（與建立 PostgreSQL 的帳號相同）。
3. 進入 **Dashboard**。
4. 點擊右上角的 **New** 按鈕。
5. 在下拉選單中選擇 **Blueprint**（另一個選項是 Web Service，兩者不同）。

**步驟 3：連接 GitHub repository**

1. 若 Render 尚未連接 GitHub，會被導向 GitHub 授權畫面，點擊 **Authorize** / **Install** 授權 Render 存取 repo（選「Only select repositories」並勾選本專案 repo 較安全）。
2. 授權後，畫面上會列出可用的 repository。
3. 點擊本專案的 repo（`2026_07_03_tvdi_AI`）。
4. Render 會自動掃描 repo，找到 `backend/08_11/render.yaml`，並在畫面上列出將要建立的資源。

**步驟 4：確認資源與設定**

Render 會依 `render.yaml` 顯示一筆 Web Service：
- **Name**：`salary-predict-service`
- **Runtime**：`Python`
- **Region**：`Singapore (Southeast Asia)`
- **Plan**：`Free`

確認後，點擊 **Apply**（或 **Create Resources** / **Create**）按鈕。

**步驟 5：等待首次部署**

1. 點擊建立後，Render 會開始執行 Build：
   - 依序執行 `pip install -r requirements.txt` 安裝所有套件。
2. 在 Dashboard 點進 `salary-predict-service`，可在 **Events / Deploys** 分頁看到部署進度。
3. 等待狀態變成 **Live**（首次部署通常需要數分鐘）。
4. 若部署失敗，點進失敗的 Deploy 查看 **Logs**，常見原因：
   - `pip install` 找不到套件 → 檢查 `requirements.txt` 版本是否有效。
   - 啟動逾時 → 檢查 `app.py` 是否在 `PORT` 指定的 port 監聽 `0.0.0.0`。

**步驟 6：填入 `POSTGRES_URL` 環境變數（必做）**

`render.yaml` 中的 `POSTGRES_URL` 是 `sync: false`，Render **不會**替你填入值，必須手動設定：

1. 進入服務 `salary-predict-service` 的 **Environment** 分頁。
2. 找到 `POSTGRES_URL` 這一列（Render 已為你建立該變數名稱）。
3. 在 **Value** 欄位填入完整連線字串（與 `backend/08_11/.env` 相同）：
   ```
   postgresql://tvdi_db_user:Pf4Z9Kkm2o8C1XL4e0WArY4GbM2yIbSE@dpg-d9u2qsjm8hqs73ecntug-a.singapore-postgres.render.com/tvdi_db?sslmode=require
   ```
4. 點擊 **Save Changes**（若沒有 Value 欄位，可點 **Add Environment Variable** 自行新增，Key 為 `POSTGRES_URL`）。
5. Render 會自動觸發一次重新部署，等待部署完成至 **Live**。

**步驟 7：驗證部署結果**

1. 在服務 **Overview** 分頁找到網址（格式為 `https://salary-predict-service.onrender.com`）。
2. 用瀏覽器或 Postman 依序驗證：
   - `GET /health` → `{"status":"ok",...}`
   - `GET /docs` → Swagger 文件
   - `GET /model-info` → 模型資訊
   - `POST /predict` → 輸入特徵回傳預測年薪
   - `POST /train` → 重新訓練成功
   - 根路徑 `/` → Gradio UI
3. 全部正常即部署完成。

**步驟 8：後續更新（重新部署）**

每次要更新程式，只需：
1. 修改程式碼後 commit 並 push 到 GitHub。
2. 到 Render 服務頁面點擊 **Manual Deploy** → **Deploy latest commit**。
3. 等待部署至 **Live** 即可。

---

## 9. 附錄：重要路徑與參考資訊

| 項目 | 路徑 / 內容 |
| --- | --- |
| 舊專案（主要修改處） | `backend/08_11/` |
| 複製 .env 目標 | `backend/08_11/`（由 `backend/08_13/.env` 複製） |
| 參考小專案 | `backend/08_13/`（`.env`、`.gitignore`、`python連結 postgres.md`） |
| MCP server 名稱 | `postgres`（設定檔：專案根目錄 `opencode.json`） |
| 資料庫名稱 | `tvdi_db` |
| 資料表 | `salary_data2`（72 筆）、`houseprice`（500 筆） |
| 關鍵 SQL | `SELECT YearsExperience, EducationLevel, City, Salary FROM salary_data2` |
