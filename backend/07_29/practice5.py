#輸出至多個組件 (Return List)

import gradio as gr

with gr.Blocks() as demo:
    food_box = gr.Number(value=5, label="剩餘食物數量")
    status_box = gr.Textbox(label="寵物狀態")

    @gr.Button("餵食").click(inputs=food_box, outputs=[food_box, status_box])
    def eat(food):
        if food > 0:
            return food-1, "飽足 😋"
        else:
            return 0, "飢餓 😢"

demo.launch()