import gradio as gr
import random
import time

def user_action(user_message, history):
    history = history or []
    history.append({"role": "user", "content": user_message})
    return "", history, history

def bot_action(history):
    history = history or []
    bot_message = random.choice([
        "你好！有什麼我可以幫忙的？",
        "這是一個 Blocks 範例。",
        "很高興為您服務。"
    ])
    time.sleep(1.5)

    history.append({"role": "assistant", "content": bot_message})
    return history, history

with gr.Blocks() as demo:
    chatbox = gr.Chatbot(label="對話視窗")
    msg = gr.Textbox(label="請輸入您的訊息（按 Enter 發送）")
    clear = gr.Button("🧹 清空對話記錄")
    state = gr.State([])

    msg.submit(
        fn=user_action,
        inputs=[msg, state],
        outputs=[msg, chatbox, state],
        queue=False,
    ).then(
        fn=bot_action,
        inputs=state,
        outputs=[chatbox, state],
        queue=False,
    )

    clear.click(
        fn=lambda: ([], []),
        inputs=None,
        outputs=[chatbox, state],
        queue=False,
    )

demo.launch()