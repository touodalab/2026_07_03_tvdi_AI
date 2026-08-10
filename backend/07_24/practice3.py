import gradio as gr

def store_message(message:str, history:list[str]):
    output = {
        "目前訊息": message,
        "歷史訊息(倒序展示)": history[::-1]
    }
    history.append(message)
    return output, history

demo = gr.Interface(
    inputs=[
        gr.Textbox(label="請輸入您的訊息", placeholder="在此輸入文字..."),
        gr.State(value=[])        
    ],
    outputs=[
        gr.JSON(label="訊息日誌"),
        gr.State()
    ],
    fn=store_message,
    title = "💬 個人歷史訊息記錄器",
    description="您在此分頁輸入的每一筆訊息都會被暫存在會話狀態中，其他連線的使用者不會看到您的資料。"
)

demo.launch()