#動態更新組件的屬性

import gradio as gr

with gr.Blocks() as demo:
    radio = gr.Radio(
        ["短文模式", "長文模式", "隱藏"],
        label = "請選擇寫作模式"
    )

    text = gr.Textbox(lines=2, interactive=True)

    @radio.change(inputs=radio, outputs=text)
    def change_textbox(choice):
        if choice == "短文模式":
            return gr.Textbox(lines=2, visible=True, label="短文寫作")
        elif choice == "長文模式":
            return gr.Textbox(lines=8, visible=True, label="長文寫作")
        else:
            return gr.Textbox(visible=False)

demo.launch()