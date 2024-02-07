import chainlit as cl
from chainlit.input_widget import Select, Switch
from agents.agents import start_chat

@cl.on_chat_start
async def on_chat_start():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"],
                initial_index=0,
            ),
            Switch(id="storage", label="Persist Results", initial=False),
        ]
    ).send()
    value = settings["Model"]

@cl.on_message
async def on_message(message):
    start_chat(message)
