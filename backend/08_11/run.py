import uvicorn
import threading
import time
import sys
from app import app

def run_fastapi():
    """在獨立執行緒中啟動 FastAPI"""
    uvicorn.run(app, host="127.0.0.1", port=8000)

def run_gradio():
    """啟動 Gradio 介面"""
    # Import inside function to avoid issues with execution order if necessary
    from gradio_interface import demo
    print("🚀 Gradio 介面正在啟動於 http://127.0.0.1:7860")
    demo.launch(server_name="127.0.0.1", server_port=7860)

if __name__ == "__main__":
    # 1. 先啟動 FastAPI 端點伺服器 (放到執行緒裡，以免阻塞主程式)
    api_thread = threading.Thread(target=run_fastapi, daemon=True)
    api_thread.start()

    # 给 API 一點點啟動時間
    time.sleep(2)

    # 2. 同時啟動 Gradio (這會阻塞主執行緒，讓程式持續運行)
    print("🚀 FastAPI 已就緒，正在開啟 Gradio UI...")
    run_gradio()
