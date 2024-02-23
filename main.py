# This is where the chainlit main page will be implemented.
import chainlit as cl
from chainlit.input_widget import Select, Switch
from agents.agents import start_chat


@cl.on_settings_update
async def on_settings_update(settings):
    global transcript_id
    transcript_id = settings["Transcripts"][-1]
    _message = f"for transcript id {transcript_id}, please extract all the entities"
    msg = cl.Message(content=_message)
    await on_message(msg)


@cl.on_chat_start
async def on_chat_start():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Transcripts",
                label="Call Transcripts",
                values=["call-transcript-1", "call-transcript-2", "call-transcript-3", "call-transcript-4"],
                initial_index=0,
            ),
        ]
    ).send()


@cl.on_message
async def on_message(message):
    start_chat(message)


