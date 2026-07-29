import gradio as gr

with gr.Blocks() as demo:
    gr.Markdown("# 👋 歡迎頁面\n請在下方輸入您的姓名，輸出將即時更新：")
    inp = gr.Textbox(placeholder="您叫什麼名字？",label="文字輸入")
    out = gr.Textbox(label="即時歡迎詞")

    @inp.change(inputs=inp, outputs=out)
    def welcome(name):
        return f"歡迎來到 Gradio, {name}！"

demo.launch()
