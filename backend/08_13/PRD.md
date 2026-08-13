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

---

## 8. 附錄：重要路徑與參考資訊

| 項目 | 路徑 / 內容 |
| --- | --- |
| 舊專案（主要修改處） | `backend/08_11/` |
| 複製 .env 目標 | `backend/08_11/`（由 `backend/08_13/.env` 複製） |
| 參考小專案 | `backend/08_13/`（`.env`、`.gitignore`、`python連結 postgres.md`） |
| MCP server 名稱 | `postgres`（設定檔：專案根目錄 `opencode.json`） |
| 資料庫名稱 | `tvdi_db` |
| 資料表 | `salary_data2`（72 筆）、`houseprice`（500 筆） |
| 關鍵 SQL | `SELECT YearsExperience, EducationLevel, City, Salary FROM salary_data2` |
