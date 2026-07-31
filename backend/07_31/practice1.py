import gradio as gr
from fastapi import FastAPI
import uvicorn

#1. 初始化FastAPI應用程式

app = FastAPI(
    title="FastAPI + Gradio 整合範例",
    description="利用 FastAPI 作為後端 API，並掛載 Gradio UI",
    version="1.0"
)

# --------------------------------------------------
# FastAPI 原生路由 (API 端點)
# --------------------------------------------------

@app.get("/root")
def read_root():
    return {"message": "歡迎來到 FastAPI 主頁！請存取 /ui 使用 Gradio 介面。"}

@app.get("/api/greet")
def api_greet(name:str="World"):
    """一個簡單的原生 FastAPI 端點"""
    return {
        "status":"success",
        "result":f"Hello, {name} from FastAPI"
        }

# ---------------------------------------------------
# Gradio 介面定義
# ---------------------------------------------------

def predict(name:str, intensity:int):
    """Gradio 使用的處理函式"""
    greeting = f"Hello {name}" * intensity
    return greeting

demo = gr.Interface(
    fn=predict,
    inputs=[
        gr.Textbox(lines=2, placeholder="請輸入姓名...", label="姓名"),
        gr.Slider(1, 10, value=3, step=1, label="重複次數")
    ],
    outputs=gr.Textbox(label="輸出結果"),
    title="Gradio 互動介面",
    description="這是嵌入在 FastAPI 裡面的 Gradio UI"
)

# --------------------------------------------------
# 將 Gradio 掛載至 FastAPI
# --------------------------------------------------
# 將 Gradio app 掛載在 `/ui` 路徑下

app = gr.mount_gradio_app(app, demo, path="/")





if __name__ == "__main__":
    # 執行伺服器：http://0.0.0.0:8000
    uvicorn.run(app, host="0.0.0.0", port=8000)