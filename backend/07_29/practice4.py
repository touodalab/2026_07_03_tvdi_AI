#在一個 Blocks 應用中，您可以配置多個事件按鈕與多個獨立的資料傳遞管道。
import gradio as gr

with gr.Blocks() as demo:
    a = gr.Number(label="數值A")
    b = gr.Number(label="數值B")

    atob = gr.Button("將 A 的值加 1 後填入 B")
    btoa = gr.Button("將 B 的值加 1 後填入 A")

    @atob.click(inputs = a, outputs= b)
    @btoa.click(inputs = b, outputs= a)
    def increase(num):
        return num + 1

demo.launch()