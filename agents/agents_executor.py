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


@dataclass
class ExecutorGroupchat(GroupChat):
    dedicated_executor: autogen.UserProxyAgent = None

    def select_speaker(
            self, last_speaker: autogen.ConversableAgent, selector: autogen.ConversableAgent
    ):
        """Select the next speaker."""

        try:
            message = self.messages[-1]
            if "function_call" in message:
                return self.dedicated_executor
        except Exception as e:
            print(e)
            pass

        selector.update_system_message(self.select_speaker_msg())
        final, name = selector.generate_oai_reply(
            self.messages
            + [
                {
                    "role": "system",
                    "content": f"Read the above conversation. Then select the next role from {self.agent_names} to play. Only return the role.",
                }
            ]
        )
        if not final:
            # i = self._random.randint(0, len(self._agent_names) - 1)  # randomly pick an id
            return self.next_agent(last_speaker)
        try:
            return self.agent_by_name(name)
        except ValueError:
            return self.next_agent(last_speaker)


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
                "description": "Function to be called to determine if there are missing values from the response returned by the extract_entities function. ",
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
            # {
            #     "description": "Function to be called when content needs to be formatted to look nice.",
            #     "name": "style_output",
            #     "parameters": {
            #         "type": "object",
            #         "properties": {
            #             "input_json": {
            #                 "type": "string",
            #                 "description": "The JSON string to be formatted"
            #             }
            #         },
            #         "required": [
            #             "input_json"
            #         ]
            #     }
            # }
        ]
    }

    llm_config_short = {
        "config_list": config_list,
        "seed": 41,
        "temperature": 0,
        "timeout": 60
    }

    def print_messages(recipient, messages, sender, config):
        if "callback" in config and config["callback"] is not None:
            callback = config["callback"]
            callback(sender, recipient, messages[-1])
        print(f"Messages sent to: {recipient.name} from {sender.name}| message: {messages[-1]}")
        return False, None  # required to ensure the agent communication flow continues

    # entity_extractor_agent_prompt = '''
    #         You are a helpful assistant that can extract text based entities from call transcripts. Do not ask the User for feedback. Once you are done,
    #         the next agent to be called is the software_engineer_agent.
    #         '''

    entity_extractor_agent_prompt = '''
            You are a helpful assistant that has strong Python skills and knows how to use Python to extract text based entities from call transcripts.
            Do not ask any questions. 
            '''

    entity_extractor_agent = ChainlitAssistantAgent(
        name="entity_extractor_agent",
        system_message=entity_extractor_agent_prompt,
        llm_config=llm_config,
        description='''
         This agent has strong Python skills and is responsible for extracting entities from call transcripts. 
        '''
    )

    # entity_extractor_agent.register_reply(
    #     [autogen.Agent, None],
    #     reply_func=print_messages,
    #     config={"callback": None},
    # )

    # software_engineer_agent_prompt = '''
    #     You are responsible for parsing the output from the entity_extractor_agent and making sure that all the required keys and values
    #     are there.
    #     If you find that there are no missing values, then the next agent to be called is the styling_agent,
    #     otherwise you should pass the list of missing values to the user_proxy so that the
    #     user_proxy can follow up with the human to get the values for those required keys.
    #     '''

    software_engineer_agent_prompt = '''
            You are a helpful assistant that has strong Python skills and is primarily responsible for analyzing the output from the entity_extractor_agent 
            to determine if there are any required fields that are missing values in the output.
            Do not ask any questions and specifically do not ask if further assistance is required. Just do your work and move on!
            '''

    software_engineer_agent = ChainlitAssistantAgent(
        name="software_engineer_agent",
        system_message=software_engineer_agent_prompt,
        llm_config=llm_config,
        description="""
        This agent is responsible for a couple different things. Firstly, once the entity_extractor_agent is finished, 
        this agent is responsible for determining if there are any required fields that are missing values. If there are
        missing fields, then those missing fields should be given to the user_proxy for human feedback. Once this feedback
        is provided, this agent is then responsible for updating the output with values provided by the human.
        Once all the required values are provided, the chat_manager needs to work with the styling_agent to generate
        the final output.
        """
    )

    # software_engineer_agent.register_reply(
    #     [autogen.Agent, None],
    #     reply_func=print_messages,
    #     config={"callback": None},
    # )

    styling_agent_prompt = '''
        You are a helpful assistant who is an expert in using Python to take in a JSON object and then generate 
        output that is both pleasing to the eye and useful for the end user.
        Create both a JSON and markdown version of the output.
        Once you have completed assisting the user output TERMINATE
        '''

    styling_agent = ChainlitAssistantAgent(
        name="styling_agent",
        system_message=styling_agent_prompt,
        llm_config=llm_config,
        description="""
            This agent is responsible for working with the user_proxy at the very end to generate the final output that 
            will be presented to the end user.
        """
    )

    # styling_agent.register_reply(
    #     [autogen.Agent, None],
    #     reply_func=print_messages,
    #     config={"callback": None},
    # )

    # description = """
    #            This agent is responsible for formatting the final output returned from this group chat. This agent will always be the last agent to run and should only run only run under the following scenarios:
    #            1.) after the software_engineer_agent has finished and it was determine that there were 0 missing values
    #            2.) after the software_engineer has finished and if it was determined that there were missing values, then this agent will need to wait until
    #            after the human has provided the missing values and the entity_extractor_agent has had a chance to reprocess the call transcript using the missing values
    #            provided by the human. Only then can this agent do its thing.
    #        """

    user_proxy = ChainlitUserProxyAgent(
        name="user_proxy",
        system_message="""
            A human admin that can execute code (for the styling_agent) and function calls and report back the execution results, as well as gather feedback from the human as necessary.
            """,
        function_map={
            "extract_entities": extract_entities,
            "find_missing_values": find_missing_values,
            # "style_output": style_output,
        },
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        code_execution_config={"work_dir": "groupchat", "use_docker": False},
        human_input_mode="ALWAYS",

    )

    # user_proxy.register_reply(
    #     [autogen.Agent, None],
    #     reply_func=print_messages,
    #     config={"callback": None},
    # )


    groupchat = ExecutorGroupchat(
        agents=[user_proxy, entity_extractor_agent, software_engineer_agent, styling_agent],
        messages=[],
        max_round=20,
        dedicated_executor=user_proxy)

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