from __future__ import annotations

from typing import List

import os
import json
import logging
import sys

from dataclasses import dataclass

import chainlit as cl

from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser, JsonKeyOutputFunctionsParser
from langchain_openai import ChatOpenAI
from langchain.prompts.chat import ChatPromptTemplate
from langchain.utils.openai_functions import convert_pydantic_to_openai_function

from typing_extensions import Annotated

import autogen
from autogen.agentchat.assistant_agent import AssistantAgent  # noqa E402
from autogen.agentchat.groupchat import GroupChat, Agent  # noqa E402

# from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, ConversableAgent
# from autogen.agentchat.groupchat import GroupChat
from .chainlit_agents import ChainlitAssistantAgent, ChainlitUserProxyAgent
from model.models import CaseSchema

from dotenv import load_dotenv, find_dotenv

from transcripts import transcripts

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logging.getLogger().addHandler(logging.StreamHandler(stream=sys.stdout))

_ = load_dotenv(find_dotenv())  # read local .env file

config_list = [
    {
        'model': 'gpt-4-1106-preview',
        'api_key': os.getenv("OPENAI_API_KEY"),
    },
]

print(config_list)


def chat_new_message(self, message, sender):
    cl.run_sync(
        cl.Message(
            content="",
            author=sender.name,
        ).send()
    )
    content = message
    cl.run_sync(
        cl.Message(
            content=content,
            author=sender.name,
        ).send()
    )





missing_value_dict = {}
missing_value_dict['orderNumber'] = "Please provide the customer's order number"
missing_value_dict['productSKU'] = "Please provide the SKU for the customer's product"


# @dataclass
# class ExecutorGroupchat(GroupChat):
#     dedicated_executor: autogen.UserProxyAgent = None
#
#     def select_speaker(
#             self, last_speaker: autogen.ConversableAgent, selector: autogen.ConversableAgent
#     ):
#         """Select the next speaker."""
#
#         try:
#             message = self.messages[-1]
#             if "function_call" in message:
#                 return self.dedicated_executor
#         except Exception as e:
#             print(e)
#             pass
#
#         selector.update_system_message(self.select_speaker_msg())
#         final, name = selector.generate_oai_reply(
#             self.messages
#             + [
#                 {
#                     "role": "system",
#                     "content": f"Read the above conversation. Then select the next role from {self.agent_names} to play. Only return the role.",
#                 }
#             ]
#         )
#         if not final:
#             # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
#             return self.next_agent(last_speaker)
#         try:
#             return self.agent_by_name(name)
#         except ValueError:
#             return self.next_agent(last_speaker)


# @user_proxy.register_for_execution()
# @chatbot.register_for_llm(description="Call transcript entity extractor.")
def extract_entities(call_transcript_id: Annotated[str, "The id of the call transcript to be processed"], ) -> str:
    try:
        print(f"Transcript ID: {call_transcript_id}")
        # model = ChatOpenAI(temperature=0, model="gpt-3.5-turbo-1106")
        model = ChatOpenAI(temperature=0, model="gpt-4-1106-preview")

        prompt = ChatPromptTemplate.from_messages([
            ("system",
             """
             Extract the relevant information, if not explicitly provided do not guess. Extract partial info.
             There is one entity (requiredElements) that you need to pay special attention to.
            Do not make up what you think is required nor use the data model provided to you to determine
            what is required. Only use the agent's responses in the call transcript to determine what is required.
            For example, you might find a response from the agent such as "productSKU is required", if you find
            phrases like that, then only those elements should be considered required
             """),
            ("human", "{input}")
        ])

        case_extraction_functions = [convert_pydantic_to_openai_function(CaseSchema)]
        extraction_model = model.bind(
            functions=case_extraction_functions,
            function_call={"name": "CaseSchema"}
        )
        extraction_chain = prompt | extraction_model | JsonOutputFunctionsParser()
        # Run
        json_output = extraction_chain.invoke({"input": transcripts.call_transcript_dict[call_transcript_id]})
        # return json_output
        return json.dumps(json_output)

    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


# @user_proxy.register_for_execution()
# @chatbot.register_for_llm(description="Format json to look pretty")
def style_output(input_json: Annotated[str, "The JSON string to be formatted"], ) -> str:
    try:
        print(f"input_json: {input_json}")
        # Print output
        # json_dict = json.loads(input_json)
        # json_pretty = json.dumps(json_dict, indent=4)
        json_pretty = json.dumps(input_json, indent=4)
        print(json_pretty)
        return json_pretty
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


def find_missing_values(extract_entities_output: Annotated[str, "The JSON object to look in for missing values"], ) -> \
        List[str]:
    result_list = []

    try:
        # Parse the JSON data
        data = json.loads(extract_entities_output)

        # Check if "required" key is present in the JSON
        if "requiredElements" in data and hasattr(data["requiredElements"], '__iter__'):
            required_keys = data["requiredElements"]

            # Loop through the elements in the "required" array
            for element in required_keys:
                # Check if the element is a key in the JSON
                if element in data:
                    # Check if the value for the key is either null or empty
                    if data[element] is None or (isinstance(data[element], str) and not data[element].strip()):
                        result_list.append(missing_value_dict[element])
                else:
                    result_list.append(missing_value_dict[element])
        else:
            print('"requiredElements" key not found in the JSON data.')
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON: {e}')

    return result_list


def config_agents():
    llm_config = {
        "config_list": config_list,
        "seed": 41,
        "temperature": 0,
        "timeout": 60,
        "functions": [
            {
                "description": "Function to be called when text based entities need to be extracted from Call Transcripts.",
                "name": "extract_entities",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "call_transcript_id": {
                            "type": "string",
                            "description": "The id of the call transcript to be processed"
                        }
                    },
                    "required": [
                        "call_transcript_id"
                    ]
                }
            },
            {
                "description": "Function to be called to determine if there are missing values from the response returned by the extract_entities function. If there are missing values, then that list should be sent to the user_proxy for follow up with the human.",
                "name": "find_missing_values",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "extract_entities_output": {
                            "type": "string",
                            "description": "The JSON output from the extract_entities function"
                        }
                    },
                    "required": [
                        "extract_entities_output"
                    ]
                }
            },
            {
                "description": "Function to be called when content needs to be formatted to look nice.",
                "name": "style_output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "input_json": {
                            "type": "string",
                            "description": "The JSON string to be formatted"
                        }
                    },
                    "required": [
                        "input_json"
                    ]
                }
            }
        ]
    }

    llm_config_short = {
        "config_list": config_list,
        "seed": 41,
        "temperature": 0,
        "timeout": 60
    }

    # software_engineer_agent_prompt = '''
    #     Do not respond as the agent named in the NEXT tag if your name is not in the NEXT tag.
    #     You are responsible for parsing the output from the entity_extractor_agent and making sure that all the required keys and values
    #     are there.
    #     If you find that there are no missing values, then respond with "NEXT: styling_agent",
    #     otherwise respond with "NEXT: user_proxy" and provide the user_proxy with the list of missing values so that the
    #     user_proxy can follow up with the human to get the values for those required keys.
    #     '''

    software_engineer_agent_prompt = '''
            Do not respond as the agent named in the NEXT tag if your name is not in the NEXT tag.
            You are responsible for parsing the output from the entity_extractor_agent and making sure that all the required keys and values
            are there.
            If you find that there are no missing values, then respond with "NEXT: styling_agent", 
            If there are missing values, then that list of missing values must be sent to user_proxy agent so that the user_proxy can follow up
            to get values for those required keys.
            '''

    software_engineer_agent = AssistantAgent(
        name="software_engineer_agent",
        system_message=software_engineer_agent_prompt,
        llm_config=llm_config,
        # description="""
        # This agent is responsible for parsing the output from the entity_extractor_agent and making sure that all the required keys and values
        # are there.
        # If there are missing values, then that list of missing values must be sent to user_proxy agent so that the user_proxy can follow up
        # with the human to get values for those required keys.
        # If there are no missing values, then the chat manager should work with the styling_agent to format the output before terminating the chat.
        # """
    )

    entity_extractor_agent_prompt = '''
        Do not respond as the agent named in the NEXT tag if your name is not in the NEXT tag.
        You are a helpful assistant that can extract text based entities from call transcripts. 
        Please note if the software_engineer_agent has performed its work and there are missing values identified, the user_proxy will provide
        values for those missing values and after those are provided, you should once again extract the entities from the provided
        call transcript, however, this time, you must replace the missing values with what the user_proxy provided.
        Once you have completed assisting the user respond with "NEXT: software_engineer_agent"
        '''

    entity_extractor_agent = AssistantAgent(
        name="entity_extractor_agent",
        system_message=entity_extractor_agent_prompt,
        llm_config=llm_config,
        # description='''
        #  This agent is responsible for extracting entities from call transcripts.
        #  There are two scenarios where the this agent will extract entities from the provided call transcript:
        #  1.) When the chat manager is initially sent a request by the user_agent. This is always the first step to occur in the workflow.
        #  2.) The other time is after the software_engineer_agent has performed its work and there are missing values identified, the human will provide
        #  values for those missing values and after those are provided, this agent should once again extract the entities from the provided
        #  call transcript, however, this time, the agent will replace the missing values with what the human provided.
        #  When this agent completes its task, the chat manager should then work with the software_engineer_agent to see if there are any missing values
        #  in the extracted entities output.
        # '''
    )

    styling_agent_prompt = '''
        Do not respond as the agent named in the NEXT tag if your name is not in the NEXT tag.
        This agent is a helpful assistant that can format content to look very pleasing to the user.
        Once you have completed assisting the user output TERMINATE
        '''

    styling_agent = AssistantAgent(
        name="styling_agent",
        system_message=styling_agent_prompt,
        llm_config=llm_config,
        # description="""
        #     This agent is responsible for formatting the final output returned from this group chat. This agent will always be the last agent to run.
        # """
    )

    # description = """
    #            This agent is responsible for formatting the final output returned from this group chat. This agent will always be the last agent to run and should only run only run under the following scenarios:
    #            1.) after the software_engineer_agent has finished and it was determine that there were 0 missing values
    #            2.) after the software_engineer has finished and if it was determined that there were missing values, then this agent will need to wait until
    #            after the human has provided the missing values and the entity_extractor_agent has had a chance to reprocess the call transcript using the missing values
    #            provided by the human. Only then can this agent do its thing.
    #        """

    assistant = autogen.ConversableAgent(name="assistant",
                                         system_message=f"You are an AI assistant. You can ask for help from a human expert using the ask_human_expert function.",
                                         llm_config=llm_config)
    #user_proxy = autogen.UserProxyAgent(name="user_proxy")

    user_proxy = ChainlitUserProxyAgent(
        name="user_proxy",
        system_message="""
               A human that will provide the necessary information to the group chat manager. Execute suggested function calls.
               If the "user" ever provides you missing information, then respond with 'NEXT: entity_extractor_agent' and
               be sure to pass the value the "user" provided to the entity_extractor_agent.
               """,
        function_map={
            "extract_entities": extract_entities,
            "find_missing_values": find_missing_values,
            "style_output": style_output,
        },
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        code_execution_config={"work_dir": "groupchat", "use_docker": False},
        human_input_mode="TERMINATE",

    )

    @assistant.register_for_llm(description="Function for asking human expert.")
    @user_proxy.register_for_execution()
    def ask_human_expert(question: Annotated[str, "The question you want to ask the human expert."]) -> Annotated[
        str, "Answer"]:
        answer = input(f"Please answer the question: {question}\n")
        return answer



    # speaker_transitions_dict = {
    #     entity_extractor_agent: [software_engineer_agent, user_proxy],
    #     software_engineer_agent: [styling_agent, user_proxy],
    #     user_proxy: [entity_extractor_agent, software_engineer_agent, styling_agent],
    # }

    speaker_transitions_dict = {
        entity_extractor_agent: [software_engineer_agent],
        software_engineer_agent: [styling_agent, user_proxy],
        user_proxy: [entity_extractor_agent]
    }


    # groupchat = ExecutorGroupchat(
    #     agents=[user_proxy, entity_extractor_agent, software_engineer_agent, styling_agent],
    #     messages=[],
    #     max_round=20,
    #     allowed_or_disallowed_speaker_transitions=speaker_transitions_dict,
    #     speaker_transitions_type="allowed",
    #     dedicated_executor=user_proxy)

    groupchat = GroupChat(
        agents=[user_proxy, entity_extractor_agent, software_engineer_agent, styling_agent],
        messages=[],
        max_round=20,
        allowed_or_disallowed_speaker_transitions=speaker_transitions_dict,
        speaker_transitions_type="allowed",
    )

    manager = autogen.GroupChatManager(groupchat=groupchat, code_execution_config=False, llm_config=llm_config_short)

    return user_proxy, manager


def start_chat(message, is_test=False):
    print(f"MESSAGE: {message}")
    if not is_test:
        autogen.ConversableAgent._print_received_message = chat_new_message
    user_proxy, manager = config_agents()
    user_proxy.initiate_chat(manager, message=message.content)


if __name__ == "__main__":
    test_message = (
        "For the call transcript with id 1, please extract all the entities "
        "in the corresponding call transcript and resolve any "
        "missing values identified by conversing with the human.")
    start_chat(test_message, is_test=True)


#For the call transcript with id 1, please extract all the entities in the corresponding call transcript
#For the call transcript with id 2, please extract all the entities in the corresponding call transcript