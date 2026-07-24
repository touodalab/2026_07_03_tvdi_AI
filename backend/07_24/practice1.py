import gradio as gr

def greet(name, intensity):
    return "Hello," + name + "!" * int(intensity)

#建立Interface實體
demo = gr.Interface(
    fn=greet,
    inputs=["text","slider"],
    outputs = ["text"],
    examples=[["徐國堂",2], ["徐xx",1]]
)

demo.launch()
