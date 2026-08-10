import gradio as gr

with gr.Blocks() as demo:
    name = gr.Textbox(label="您的姓名")
    output = gr.Textbox(label="輸出結果")
    greet_btn = gr.Button("送出問候")

    @greet_btn.click(inputs=name, outputs=output)
    def greet(name:str)->str:
        return "Hello " + name + "!"

demo.launch()