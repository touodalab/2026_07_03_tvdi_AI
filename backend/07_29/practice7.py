# 保持組件原值不變 (gr.skip())

import random
import gradio as gr

with gr.Blocks() as demo:
    with gr.Row():
        clear_button = gr.Button("清除")
        skip_button = gr.Button("跳過 A (保持原狀)")
        random_button = gr.Button("隨機產生")
    numbers = [gr.Number(label="數值 A"), gr.Number(label="數值 B")]

    #全部清空為None
    clear_button.click(lambda:(None, None), outputs=numbers)

    #B 填入 "已跳過"，但 A 保持原本的數值
    skip_button.click(lambda:[gr.skip(), 10], outputs=numbers)

    # 3. 隨機產生兩個新數值
    random_button.click(lambda:(random.randint(0,100), random.randint(0, 100)),outputs=numbers )

demo.launch()