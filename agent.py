from __future__ import annotations

from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field

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

from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, ConversableAgent
from agents.chainlit_agents import ChainlitAssistantAgent, ChainlitUserProxyAgent

from dotenv import load_dotenv, find_dotenv

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


# Pydantic Models used for extraction


class ContactType(Enum):
    Phone = 'Phone'
    Text = 'Text'


class CustomerNeed(Enum):
    Complete_purchase_support = 'Complete purchase support'
    Technical_support = 'Technical support'
    Membership_management = 'Membership management'
    Other = 'Other'


class EmployeeResponse(Enum):
    Added_protection_plan_to_product = 'Added protection plan to product'
    Engaged_manager_or_support = 'Engaged manager or support'
    Fixed_in_the_moment = 'Fixed in the moment'
    Gave_recommendation_or_advice = 'Gave recommendation or advice'
    Started_remote_support_session = 'Started remote support session'
    Unable_to_resolve_to_satisfaction = 'Unable to resolve to satisfaction'
    Canceled_membership = 'Canceled membership'
    Explained_membership_benefits = 'Explained membership benefits'
    Referred_to_other_team___unable_to_help = 'Referred to other team - unable to help'
    Renewed_membership = 'Renewed membership'
    Other = 'Other'


class CustomerSentimentGoingIn(Enum):
    Positive = 'Positive'
    Negative = 'Negative'
    Neutral = 'Neutral'


class CustomerSentimentGoingOut(Enum):
    Positive = 'Positive'
    Negative = 'Negative'
    Neutral = 'Neutral'


class GiftCard(BaseModel):
    giftCardOffered: bool = Field(..., title="Was a gift card offered to the customer?")
    giftCardAmount: str = Field(..., title="Dollar amount of the gift card offered")
    giftCardAccepted: bool = Field(..., title="If gift card was offered, did the customer accept the gift card?")


class CaseSchema(BaseModel):
    """ Information about the Customer's Case Conversation """
    summary: str = Field(...,
                         title='A detailed summary of the entire call transcript. Be sure to include why the customer was calling and if the customers issue was resolved, please provide those details in your summary. Do not use the customer or agents actual name in the summary, just refer to them as either "Agent" or "Customer"!')
    required: List[str] = Field(...,
                                title="List of elements that are required to be present in the extracted entities output")
    orderNumber: str = Field(..., title="The customer's order number")
    productSKU: str = Field(..., title="The SKU associated to the product the customer might be calling about")
    driver: str = Field(...,
                        title="A name or description that could be used to identify the individual delivering and/or doing service at the customer's house")
    photos: bool = Field(...,
                         title="where photos captured at the customer's house showing damage or product condition?")
    agentCall: bool = Field(..., title="Did the agent or delivery person make a call while at the customer's house?")
    contactType: ContactType = Field(..., title='Contact Channel')
    productSafteyFlag: bool = Field(..., title='Is there a product safety concern?')
    customerNeed: CustomerNeed = Field(..., title='Customer Need')
    employeeResponse: EmployeeResponse = Field(..., title='Employee Response')
    customerSentimentGoingIn: CustomerSentimentGoingIn = Field(...,
                                                               title="The customer's sentiment going into the conversation with agent")
    customerSentimentGoingOut: CustomerSentimentGoingOut = Field(...,
                                                                 title="The customer's sentiment at the end of the conversation with agent")
    agentName: Optional[str] = Field(None, title='The name of the agent')
    customerName: Optional[str] = Field(None, title='The name of the customer')
    giftCards: GiftCard = Field(..., title="Were gift cards offered and if so, were they accepted by the customer?")

# End Pydantic Models


call_transcript_sample = {
    "transcript": [{
        "source": "agent",
        "timestamp": "2024-01-17T18:26:17.671956",
        "message": "Hi Thanks for calling geek squad. My name is Valerie before we start. May I please have your full name and your phone number."
    }, {
        "source": "customer",
        "timestamp": "2024-01-17T18:26:27.609811",
        "message": "No. Yes, I just I'm sorry I think I was in the wrong department I need to talk to somebody about printer I bought, the order number is 12345."
    }, {
        "source": "agent",
        "timestamp": "2024-01-17T18:26:33.117753",
        "message": "Uh Yes, I am from computing services, but what do you need? I'm sorry I cannot hear you properly."
    }, {
        "source": "customer",
        "timestamp": "2024-01-17T18:26:37.875478",
        "message": "I need to know if you sell a specific type of printer in."
    }, {
        "source": "agent",
        "timestamp": "2024-01-17T18:26:41.890700",
        "message": "Okay, I am going to provide you the phone number of the right department. Okay?"
    }, {
        "source": "customer",
        "timestamp": "2024-01-17T18:26:48.074268",
        "message": "No cause I already called and was on hold for 12 minutes and I got disconnected. So can you connect me."
    }, {
        "source": "agent",
        "timestamp": "2024-01-17T18:26:52.816488",
        "message": "Uh, yes, for sure. Thank you so much for calling geek squad and have a wonderful day."
    }, {
        "source": "customer",
        "timestamp": "2024-01-17T18:26:54.107702",
        "message": "Thank you."
    }, {
        "source": "agent",
        "timestamp": "2024-01-17T18:26:52.816488",
        "message": "For your trouble, I would like to offer you a $20 gift card, would that be acceptable?"
    }, {
        "source": "customer",
        "timestamp": "2024-01-17T18:26:54.107702",
        "message": "No, that is ok.."
    }, {
        "source": "agent",
        "timestamp": "2024-01-17T18:27:39.057198",
        "message": "All agents are busy at this time. Please hold."
    }, {
        "source": "system",
        "message": "Based on this call, the following elements are required:  ['orderNumber', 'productSKU']"
    }]
}


missing_value_dict = {}
missing_value_dict['orderNumber'] = "Please provide the customer's order number"
missing_value_dict['productSKU'] = "Please provide the SKU for the customer's product"

@dataclass
class ExecutorGroupchat(GroupChat):
    dedicated_executor: UserProxyAgent = None

    def select_speaker(
            self, last_speaker: ConversableAgent, selector: ConversableAgent
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
             "Extract the relevant information, if not explicitly provided do not guess. Extract partial info"),
            ("human", "{input}")
        ])

        case_extraction_functions = [convert_pydantic_to_openai_function(CaseSchema)]
        extraction_model = model.bind(
            functions=case_extraction_functions,
            function_call={"name": "CaseSchema"}
        )
        extraction_chain = prompt | extraction_model | JsonOutputFunctionsParser()
        # Run
        json_output = extraction_chain.invoke({"input": call_transcript_sample})
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
        if "required" in data:
            required_keys = data["required"]

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
            print('"required" key not found in the JSON data.')
    except json.JSONDecodeError as e:
        print(f'Error decoding JSON: {e}')

    return result_list


def config_agents():
    llm_config = {
        "config_list": config_list,
        "seed": 42,
        "temperature": 0,
        "functions": [
            {
                "description": "Function to be called when text needs to be extracted from Call Transcripts.",
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
        "seed": 42,
        "temperature": 0
    }

    software_engineer_agent_prompt = '''
        You are a helpful assistant that is proficient at using python to parse json and look for missing keys and values.
        Once you have completed assisting the user output TERMINATE
        '''

    software_engineer_agent = AssistantAgent(
        name="software_engineer_agent",
     #   system_message=software_engineer_agent_prompt,
        llm_config=llm_config,
        description="""
        This agent is responsible for parsing the output from the text_extractor_agent and making sure that all the required keys and values
        are there. 
        If there are missing values, then that list of missing values must be sent to user_proxy agent so that the user_proxy can follow up 
        with the human to get values for those required keys.
        If there are no missing values, then the chat manager should work with the styling_agent to format the output before terminating the chat.
        """
    )

    text_extractor_agent_prompt = '''
        This agent is a helpful assistant that can extract text from call transcripts. This agent is NOT responsible for finding missing
        values in the call transcript or extracted entities JSON!
        Once you have completed assisting the user output TERMINATE
        '''

    text_extractor_agent = AssistantAgent(
        name="text_extractor_agent",
   #     system_message=text_extractor_agent_prompt,
        llm_config=llm_config,
        description='''
         This agent is responsible for extracting entities from call transcripts.
         There are two scenarios where the this agent will extract entities from the provided call transcript:
         1.) When the chat manager is initially sent a request by the user_agent. This is always the first step to occur in the workflow.
         2.) The other time is after the software_engineer_agent has performed its work and there are missing values identified, the human will provide
         values for those missing values and after those are provided, this agent should once again extract the entities from the provided 
         call transcript, however, this time, the agent will replace the missing values with what the human provided.
         When this agent completes its task, the chat manager should then work with the software_engineer_agent to see if there are any missing values 
         in the extracted entities output.
        '''
    )

    styling_agent_prompt = '''
        This agent is a helpful assistant that can format content to look very pleasing to the user.
        Once you have completed assisting the user output TERMINATE
        '''

    styling_agent = AssistantAgent(
        name="styling_agent",
        system_message=styling_agent_prompt,
        llm_config=llm_config,
        description="""
            This agent is responsible for formatting the final output returned from this group chat. This agent will always be the last agent to run.
        """
    )

    # description = """
    #            This agent is responsible for formatting the final output returned from this group chat. This agent will always be the last agent to run and should only run only run under the following scenarios:
    #            1.) after the software_engineer_agent has finished and it was determine that there were 0 missing values
    #            2.) after the software_engineer has finished and if it was determined that there were missing values, then this agent will need to wait until
    #            after the human has provided the missing values and the text_extractor_agent has had a chance to reprocess the call transcript using the missing values
    #            provided by the human. Only then can this agent do its thing.
    #        """

    user_proxy = ChainlitUserProxyAgent(
        name="user_proxy",
        system_message="A human that will provide the necessary information to the group chat manager. Execute suggested function calls.",
        function_map={
            "extract_entities": extract_entities,
            "find_missing_values": find_missing_values,
            "style_output": style_output,
        },
        is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
        code_execution_config={"last_n_messages": 4, "work_dir": "groupchat", "use_docker": False},
        human_input_mode="ALWAYS",

    )

    groupchat = ExecutorGroupchat(
        agents=[user_proxy, text_extractor_agent, software_engineer_agent, styling_agent], messages=[],
        max_round=20, dedicated_executor=user_proxy)

    manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config_short)

    return user_proxy, manager


def start_chat(message, is_test=False):
    print(f"MESSAGE: {message}")
    if not is_test:
        ConversableAgent._print_received_message = chat_new_message
    user_proxy, manager = config_agents()
    user_proxy.initiate_chat(manager, message=message.content)


if __name__ == "__main__":
    test_message = (
        "For the call transcript with id 1, please extract all the entities "
        "in the corresponding call transcript and resolve any "
        "missing values identified by conversing with the human.")
    start_chat(test_message, is_test=True)


#For the call transcript with id 1, please extract all the entities in the corresponding call transcript