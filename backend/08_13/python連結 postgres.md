# Python 連結 Render PostgreSQL 完整教學

> 這份教學專為程式初學者（學生）撰寫。只要一步一步跟著做，你就能讓 Python 程式成功連上雲端的 PostgreSQL 資料庫，並學會使用 `.env` 檔案妥善保護你的密碼。

---

## 目錄（Table of Contents）

1. [開始之前：你需要的東西](#1-開始之前你需要的東西)
2. [第一步：在 Render 建立 PostgreSQL 資料庫](#2-第一步在-render-建立-postgresql-資料庫)
3. [第二步：看懂連線字串（Connection String）](#3-第二步看懂連線字串connection-string)
4. [第三步：建立你的專案資料夾](#4-第三步建立你的專案資料夾)
5. [第四步：安裝需要的 Python 套件](#5-第四步安裝需要的-python-套件)
6. [第五步：建立 .env 檔案保護密碼](#6-第五步建立-env-檔案保護密碼)
7. [第六步：建立 .gitignore 防止密碼上傳](#7-第六步建立-gitignore-防止密碼上傳)
8. [第七步：建立 .env.example 範本檔](#8-第七步建立-envexample-範本檔)
9. [第八步：撰寫 Python 程式連結資料庫](#9-第八步撰寫-python-程式連結資料庫)
10. [第九步：執行並驗證連線成功](#10-第九步執行並驗證連線成功)
11. [常見錯誤排解（Troubleshooting）](#11-常見錯誤排解troubleshooting)
12. [你的完整專案結構長這樣](#12-你的完整專案結構長這樣)
13. [下一步建議](#13-下一步建議)

---

## 1. 開始之前：你需要的東西

在開始之前，請確認你已經具備以下條件：

| 需要的東西 | 說明 | 哪裡可以取得 |
| --- | --- | --- |
| Python 3.8 以上 | 執行 Python 程式的環境 | https://www.python.org/downloads/ |
| pip | Python 的套件安裝工具（Python 安裝時通常會一起裝） | 安裝 Python 時會自動裝好 |
| 一個命令列視窗 | 在 Windows 叫做「命令提示字元（CMD）」或「PowerShell」；在 Mac 叫做「終端機（Terminal）」 | 內建就有 |
| Render 帳號 | 免費雲端平台，可以建立 PostgreSQL 資料庫 | https://render.com |
| 一個文字編輯器 | 用來寫 `.py`、`.env` 等檔案 | 推薦 VSCode（免費）：https://code.visualstudio.com |

> **小提醒**：不確定有沒有裝 Python？在命令列輸入 `python --version`，如果有顯示版本號碼（例如 `Python 3.12.0`）就代表有裝好。

---

## 2. 第一步：在 Render 建立 PostgreSQL 資料庫

### 2.1 註冊 / 登入 Render

1. 打開瀏覽器，前往 **https://render.com**
2. 點擊右上角的 **Sign Up**（註冊）或 **Sign In**（登入）。
3. 可以用 Google、GitHub 帳號快速註冊，或使用 Email 註冊。
4. 登入後會進入 Render 的儀表板（Dashboard）。

### 2.2 建立 PostgreSQL 服務

1. 在 Dashboard 畫面，點擊右上角的 **New**（藍色按鈕）。
2. 從下拉選單中選擇 **PostgreSQL**。
3. 系統會要求你替這個資料庫取名，請輸入一個好記的名字，例如：
   ```
   my-first-db
   ```
4. 選擇方案（Plan）：
   - **免費方案（Free）**：`$0`，適合練習。注意：免費方案在閒置一段時間後會「休眠」，下次連線會比較慢，需要等它啟動。
   - **付費方案（Hobby / Pro）**：有費用，適合正式專案。
   - 課程練習建議選 **Free**。
5. 點擊下方 **Create Database** 按鈕，等待部署完成（通常需要幾分鐘）。

### 2.3 取得連線字串（Connection String）

1. 資料庫建立完成後，畫面會顯示這台資料庫的詳細資訊頁面。
2. 在頁面上方找到 **Connections** 區塊，裡面有幾個欄位：
   - **Internal Connection String**：從 Render 內部連線時使用（例如同一個帳號下部署的 Web 服務）。
   - **External Connection String**：從你自己的電腦（本地端）連線時使用。**我們這份教學就是要用這個**。
3. 點擊 **External Connection String** 欄位右邊的「複製（Copy）」按鈕。
4. 把複製到的字串先貼到記事本暫存，下一步我們會用到它。

> **重要**：這串文字包含你的帳號密碼，就像你家鑰匙一樣。**不要**把它貼到公開的地方（例如 LINE 群組、GitHub、臉書）。接下來我們會教你把它放進 `.env` 保護起來。

---

## 3. 第二步：看懂連線字串（Connection String）

你複製下來的連線字串長得像這樣：

```
postgresql://myuser:mysupersecretpassword@dpg-abc123-xxxx.a.oregon-postgres.render.com:5432/my_first_db_xxxx
```

它其實就是「一個網址」，裡面包藏了連上資料庫所需的全部資訊。我們把它拆開來看：

```
postgresql://  myuser  :  mysupersecretpassword  @  dpg-abc123-xxxx.a.oregon-postgres.render.com  :  5432  /  my_first_db_xxxx
   通訊協定        使用者名稱         密碼                     主機位址（Host）                            連接埠   資料庫名稱
```

| 位置 | 欄位 | 說明 | 例子 |
| --- | --- | --- | --- |
| `postgresql://` | 通訊協定 | 告訴程式這是 PostgreSQL 資料庫 | `postgresql://` |
| `:` 前面的部分 | 使用者名稱（User） | 連線到資料庫用的帳號 | `myuser` |
| `:` 到 `@` 中間 | 密碼（Password） | 這個帳號的密碼 | `mysupersecretpassword` |
| `@` 到 `:` 中間 | 主機位址（Host） | 資料庫伺服器在哪裡 | `dpg-abc123-xxxx.a.oregon-postgres.render.com` |
| 最後的 `:` 後面 | 連接埠（Port） | 伺服器開放的連線埠口 | `5432` |
| `/` 後面 | 資料庫名稱（Database） | 資料庫的名字 | `my_first_db_xxxx` |

> **為什麼要了解這個？** 因為日後連線出問題時，你才知道該檢查哪一個欄位。例如「主機位址錯誤」與「密碼錯誤」的修正方式完全不同。

---

## 4. 第三步：建立你的專案資料夾

在開始寫程式前，先建立一個乾淨的專案資料夾。所有相關檔案都放在裡面，比較好管理。

在命令列（CMD / PowerShell / Terminal）執行：

```
mkdir my_project
cd my_project
```

Windows 的範例（PowerShell）：

```
New-Item -ItemType Directory -Path my_project
cd my_project
```

之後你的所有操作都在這個資料夾裡面進行。

---

## 5. 第四步：安裝需要的 Python 套件

### 5.1 需要的套件

| 套件 | 用途 | 為什麼需要 |
| --- | --- | --- |
| `psycopg2-binary` | 讓 Python 連上 PostgreSQL | 官方推薦的 PostgreSQL 連線套件；`-binary` 版本已包含編譯好的程式，初學者安裝最不容易出錯 |
| `python-dotenv` | 讀取 `.env` 檔案的環境變數 | 讓你的密碼不用寫死在程式碼裡，而是從 `.env` 檔讀進來 |

### 5.2 執行安裝指令

先進入你的專案資料夾（`my_project`），然後執行：

```
pip install psycopg2-binary python-dotenv
```

如果出現 `pip 不是內部或外部命令`（Windows）或 `command not found`（Mac），可以試試改成：

```
python -m pip install psycopg2-binary python-dotenv
```

### 5.3 確認安裝成功

```
pip list
```

畫面上應該會看到 `psycopg2-binary` 與 `python-dotenv` 兩個套件及其版本號碼。

---

## 6. 第五步：建立 .env 檔案保護密碼

### 6.1 為什麼要用 `.env`？

如果把密碼直接寫死在程式碼裡，會有兩個問題：

1. **不安全**：一旦把程式碼上傳到 GitHub 或分享給別人，密碼就會被看光光。
2. **不好維護**：換密碼就得改程式碼，不小心改錯一行，整個程式就無法執行了。

`.env`（讀作 dot env）是一個專門存放「機密設定值」的檔案。程式在執行時才讀取它，程式碼本身不會包含任何密碼。

### 6.2 建立 `.env` 檔案

1. 在專案資料夾（`my_project`）裡面，用文字編輯器（VSCode）建立一個新檔案。
2. 檔名要叫做 `.env`（前面有個點，沒有其他檔名）。
3. 檔案內容寫入你的連線字串，格式如下：

```
DATABASE_URL=postgresql://myuser:mysupersecretpassword@dpg-abc123-xxxx.a.oregon-postgres.render.com:5432/my_first_db_xxxx
```

將等號右邊的值換成你剛才在 Render 複製的 **External Connection String**。

### 6.3 撰寫 `.env` 的重要注意事項

- `=` **兩側不要加空格**。
  - 對的：`DATABASE_URL=postgresql://...`
  - 錯的：`DATABASE_URL = postgresql://...`
- 一行只寫一個設定值。
- 值如果包含特殊字元（例如 `#`、空格等），請用雙引號包起來：
  ```
  DATABASE_URL="postgresql://myuser:pa@ss@host:5432/dbname"
  ```
- 不要在 `.env` 中寫入中文字元，以免造成編碼問題。
- 密碼中如果含有 `@`、`:` 等網址特殊字元，Render 產生的連線字串通常已經處理過，直接整段複製即可。

### 6.4 補充：什麼是「環境變數」？

環境變數（Environment Variable）是作業系統提供的一塊「設定暫存區」，以「名稱＝值」的形式存放資料。`.env` 檔案就是我們自訂的一份環境變數清單，由 `python-dotenv` 在程式啟動時讀取並載入程式環境。這樣最大的好處是：**密碼與程式碼分開存放**。

---

## 7. 第六步：建立 .gitignore 防止密碼上傳

### 7.1 為什麼需要 `.gitignore`？

如果你使用 Git / GitHub 管理程式碼，`.env` 是「機密檔案」，**絕對不能上傳**。一旦上傳，你的資料庫密碼就等於公開了。

`.gitignore` 是一份告訴 Git「哪些檔案不要追蹤、不要上傳」的清單。

### 7.2 建立 `.gitignore` 檔案

在專案資料夾（`my_project`）中建立新檔案，檔名叫做 `.gitignore`，內容如下：

```
.env
```

### 7.3 說明這個檔案

- 第一行 `.env` 表示：Git 會忽略名稱為 `.env` 的檔案。
- 之後任何 `git add .` 或 `git commit` 都不會把 `.env` 納入其中。

> **強烈警告**：
> - 絕對不要把 `.env` 上傳到 GitHub。
> - 如果你發現已經把 `.env` commit 上去了，**請立即做兩件事**：
>   1. 到 Render 重新產生（Reset）資料庫密碼，讓舊密碼失效。
>   2. 在命令列執行 `git rm --cached .env`，讓 Git 停止追蹤它，再重新 commit 一次。

---

## 8. 第七步：建立 .env.example 範本檔

### 8.1 為什麼需要 `.env.example`？

`.env` 不能上傳，但你的隊友或老師仍需要知道「這個專案需要設定哪些變數」。因此我們準備一個**不含真實密碼的範本檔** `.env.example`，它可以安全地上傳到 GitHub。

### 8.2 建立 `.env.example` 檔案

在專案資料夾（`my_project`）中建立新檔案 `.env.example`，內容如下：

```
DATABASE_URL=postgresql://your_username:your_password@your_host:5432/your_database
```

這裡面的值都是「示意」，只是讓別人知道該填入什麼。

### 8.3 使用方式

別人拿到你的專案後，只要：

```
cp .env.example .env
```

（Windows 請用：`copy .env.example .env`）

再把 `.env` 改成自己的真實連線字串即可。

---

## 9. 第八步：撰寫 Python 程式連結資料庫

### 9.1 程式碼解說（一步一步）

在專案資料夾建立主程式 `db_connect.py`，內容如下：

```python
import os
from dotenv import load_dotenv
import psycopg2

# 1. 載入 .env 檔案（把裡面的設定讀進程式環境）
load_dotenv()

# 2. 從環境變數取得連線字串
database_url = os.getenv("DATABASE_URL")

# 3. 檢查有沒有讀到（避免學生忘記建立 .env）
if database_url is None:
    print("錯誤：找不到 DATABASE_URL，請確認你已經建立 .env 檔案。")
    exit(1)

try:
    # 4. 建立與資料庫的連線
    conn = psycopg2.connect(database_url)

    # 5. 建立 cursor（執行 SQL 的「指標」）
    cur = conn.cursor()

    # 6. 執行一條 SQL 查詢：取得 PostgreSQL 版本
    cur.execute("SELECT version();")

    # 7. 讀取查詢結果
    result = cur.fetchone()
    print("✅ 連線成功！PostgreSQL 版本是：", result[0])

    # 8. 關閉 cursor 與連線（用完一定要關，節省資源）
    cur.close()
    conn.close()
    print("連線已關閉。")

except psycopg2.OperationalError as e:
    print("連線失敗：", e)
```

### 9.2 每一段在做什麼

| 程式碼 | 作用 |
| --- | --- |
| `from dotenv import load_dotenv` | 匯入 `python-dotenv` 套件 |
| `load_dotenv()` | 讀取同資料夾的 `.env` 檔，放入環境變數 |
| `os.getenv("DATABASE_URL")` | 取出名為 `DATABASE_URL` 的環境變數值 |
| `psycopg2.connect(...)` | 用連線字串建立資料庫連線 |
| `conn.cursor()` | 建立 cursor，之後用 `cur.execute()` 執行 SQL |
| `cur.execute("SELECT version();")` | 執行 SQL 查詢，取得資料庫版本 |
| `cur.fetchone()` | 取回第一筆查詢結果 |
| `cur.close()` / `conn.close()` | 釋放資源，關閉連線 |

### 9.3 想測更多 SQL？試試這個版本

```python
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()

database_url = os.getenv("DATABASE_URL")
if database_url is None:
    print("錯誤：找不到 DATABASE_URL，請確認你已經建立 .env 檔案。")
    exit(1)

try:
    conn = psycopg2.connect(database_url)
    cur = conn.cursor()

    # 查詢現在時間
    cur.execute("SELECT NOW();")
    now = cur.fetchone()
    print("資料庫目前的時間是：", now[0])

    # 建立一張測試表格
    cur.execute("CREATE TABLE IF NOT EXISTS students (id SERIAL PRIMARY KEY, name TEXT NOT NULL);")

    # 插入一筆資料
    cur.execute("INSERT INTO students (name) VALUES (%s);", ("小明",))

    # 重要：INSERT 之後要 commit，資料才會真的寫入
    conn.commit()

    # 查詢全部學生
    cur.execute("SELECT * FROM students;")
    rows = cur.fetchall()
    print("students 表格內容：", rows)

    cur.close()
    conn.close()
    print("完成！")

except psycopg2.OperationalError as e:
    print("連線失敗：", e)
```

> **重點**：執行 `INSERT` / `UPDATE` / `DELETE` 之後，一定要呼叫 `conn.commit()`，資料才會真正寫進資料庫。用 `%s` 佔位符傳入資料，可以防止 SQL 注入攻擊。

---

## 10. 第九步：執行並驗證連線成功

### 10.1 執行你的程式

先確認你的 `my_project` 資料夾裡有這三個檔案：

- `.env`（你的真實連線字串）
- `.gitignore`
- `db_connect.py`

然後在命令列執行：

```
python db_connect.py
```

### 10.2 預期的輸出結果

如果一切順利，你應該會看到類似這樣：

```
✅ 連線成功！PostgreSQL 版本是： PostgreSQL 16.x on x86_64-pc-linux-gnu, ...
連線已關閉。
```

### 10.3 如果看到錯誤訊息

不要緊張，請對照下方的[常見錯誤排解表](#11-常見錯誤排解troubleshooting)，一步一步檢查。

---

## 11. 常見錯誤排解（Troubleshooting）

| 錯誤訊息 | 可能原因 | 解決方法 |
| --- | --- | --- |
| `connection refused` | 主機位址或連接埠錯誤；或資料庫未啟動 | 回到 Render 重新複製 **External Connection String**，確認完整貼入 `.env`；免費方案請確認資料庫已啟動 |
| `password authentication failed` | 帳號或密碼錯誤 | 檢查 `.env` 內容是否正確、`=` 兩側是否不小心多打了空格、值有沒有被截斷 |
| `database "xxx" does not exist` | 資料庫名稱錯誤 | 檢查連線字串中 `/` 後面的資料庫名稱是否與 Render 顯示的一致 |
| `ModuleNotFoundError: No module named 'psycopg2'` | 套件未安裝，或安裝到別的 Python 環境 | 執行 `pip install psycopg2-binary`；若用虛擬環境，請先啟用虛擬環境再安裝 |
| 連線逾時（timeout） | 防火牆阻擋，或 Render 免費方案休眠中 | Render 免費方案閒置一段時間會休眠，重新開啟頁面或稍等它啟動；確認你的網路環境可以連到外部伺服器 |
| 密碼被上傳到 GitHub | `.env` 未加入 `.gitignore` | 立即到 Render 重置密碼，執行 `git rm --cached .env` 停止追蹤，再把 `.env` 加入 `.gitignore` |
| `is not permitted to connect to this server` | Render 免費方案的 IP 限制（僅少數情況） | 確認使用的連線字串是否為 External（非 Internal） |

**除錯小技巧**：可以在程式中暫時印出（但不建議長期使用）：

```python
print(database_url)
```

確認讀進來的字串是否完整。**確認完記得把這行刪掉**，不要在公開環境顯示密碼。

---

## 12. 你的完整專案結構長這樣

做完以上所有步驟後，你的 `my_project` 資料夾應該長這樣：

```
my_project/
├── .env              # 存放機密連線字串（不要上傳 GitHub）
├── .env.example      # 範本，值都是假的（可以上傳）
├── .gitignore        # 忽略 .env，避免密碼上傳
└── db_connect.py     # 主程式
```

| 檔案 | 是否可以上傳 GitHub | 說明 |
| --- | --- | --- |
| `.env` | ❌ 不可以 | 含真實密碼 |
| `.env.example` | ✅ 可以 | 不含真實密碼 |
| `.gitignore` | ✅ 可以 | 保護機制 |
| `db_connect.py` | ✅ 可以 | 你的程式碼 |

---

## 13. 下一步建議

你已經成功讓 Python 連上 Render PostgreSQL 了，恭喜！接下來可以延伸學習：

1. **使用 SQLAlchemy（ORM）**：用 Python 物件來操作資料庫，不用手寫 SQL。
2. **結合 Web 框架（Flask / FastAPI）**：做一個有資料庫的網站或 API。
3. **認識虛擬環境（venv）**：替每個專案建立獨立的 Python 環境，避免套件互相干擾。
4. **學習資料庫設計**：正規化、索引（Index）、資料型態，讓資料庫更快更穩。
5. **部署你的 Python 程式到 Render**：讓你的程式也跟資料庫一樣在雲端跑，變成一個公開服務。

---

> 撰寫完畢。有任何連不上、看不懂的地方，先對照「常見錯誤排解」，再詢問老師或同學。**記住：密碼不離 `.env`，`.env` 不進 GitHub！**
