from dotenv import load_dotenv, find_dotenv

from model.models import CaseSchema
from transcripts.transcripts import call_transcript_dict

_ = load_dotenv(find_dotenv())  # read local .env file

import autogen
import os
from agents.chainlit_agents import ChainlitAssistantAgent, ChainlitUserProxyAgent
from autogen.agentchat.groupchat import GroupChat, Agent  # noqa E402
from dataclasses import dataclass
from typing import List, Tuple, Union, Annotated, Dict, Any

from pydantic import ValidationError

from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

from langchain.utils.openai_functions import convert_pydantic_to_openai_function

from langchain.output_parsers.openai_functions import JsonOutputFunctionsParser, JsonKeyOutputFunctionsParser

import psycopg2
import json

#logging_session_id = autogen.runtime_logging.start(config={"dbname": "logs.db"})



missing_value_dict = {}
missing_value_dict['orderNumber'] = "Please provide the Order Number"
missing_value_dict['productSKU'] = "Please provide the Product SKU"


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


def extract_entities(call_transcript_id):

    model = ChatOpenAI(temperature=0, model="gpt-4-turbo-preview")

    prompt = ChatPromptTemplate.from_messages([
        ("system", """Extract the relevant information, if not explicitly provided do not guess. 
            If there is no value do not substitute a value in its place (e.g. "N/A", ""), just leave the value as None.
            """),
        ("human", "{input}")
    ])

    case_extraction_functions = [convert_pydantic_to_openai_function(CaseSchema)]
    extraction_model = model.bind(
        functions=case_extraction_functions,
        function_call={"name":"CaseSchema"}
    )
    extraction_chain = prompt | extraction_model | JsonOutputFunctionsParser()

    # Run
    json_output = extraction_chain.invoke({"input": call_transcript_dict[str(call_transcript_id)]})

    # the model sometimes wants to use empty strings instead of None
    for key, value in json_output.items():
        if isinstance(value, str) and value == '':
            json_output[key] = None

    return json.dumps(json_output)


def loc_to_dot_sep(loc: Tuple[Union[str, int], ...]) -> str:
    path = ''
    for i, x in enumerate(loc):
        if isinstance(x, str):
            if i > 0:
                path += '.'
            path += x
        elif isinstance(x, int):
            path += f'[{x}]'
        else:
            raise TypeError('Unexpected type')
    return path


def convert_errors(e: ValidationError) -> List[Dict[str, Any]]:
    new_errors: List[Dict[str, Any]] = e.errors()
    for error in new_errors:
        error['loc'] = loc_to_dot_sep(error['loc'])
    return new_errors


def find_missing_field_values(extracted_entity_output: Annotated[str, "The JSON object to look in for missing values"], ) -> \
        List[str]:
    result_list = []

    try:
        CaseSchema.model_validate_json(extracted_entity_output)
    except ValidationError as e:
        pretty_errors = convert_errors(e)
        for error in pretty_errors:
            result_list.append(missing_value_dict[error['loc']])
         #   result_list.append(error['loc'])

    print(f"Missing Field List: {result_list}")
    print(f"engineering output: {extracted_entity_output}")

    # print("Inserting into Postgress...")
    #
    # _json = json.loads(extracted_entity_output)

    #insertTranscriptSummary(_call_transcript_id, json.dumps(_json))
    return result_list



def insert_transcript_summary_to_database(call_transcript_id, final_extracted_entity_output):
    """ Connect to the PostgreSQL database server """
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="mysecretpassword",
            host="127.0.0.1",
            port="5432",
            database="iw25_gen_ai"
        )
        cursor = connection.cursor()

        _json = json.loads(final_extracted_entity_output)
        postgres_insert_query = """ INSERT INTO transcript_summaries (transcript_id, transcript_summary) VALUES (%s,%s)"""
        record_to_insert = (str(call_transcript_id), json.dumps(_json))
        cursor.execute(postgres_insert_query, record_to_insert)
        connection.commit()
        count = cursor.rowcount
        print(count, "Record inserted successfully into transcript_summaries table")
 
    except (Exception, psycopg2.Error) as error:
        print("Failed to insert record into transcript_summaries table: ", error)
 
    finally:
        try:
            connection
        except NameError:
            print("connection variable was NOT created")
            return
        
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")
 
 

config_list = [
    {
        'model': 'gpt-4-turbo-preview',
        'api_key': os.getenv("OPENAI_API_KEY"),
    },
]

llm_config = {
    "config_list": config_list,
    "seed": 41,
    "temperature": 0,
    "timeout": 60,
    "functions":[
        {
            "name": "extract_entities",
            "description": "This function is called when text based entities need to be extracted from call transcripts",
            "parameters": {
                "type": "object",
                "properties": {
                    "call_transcript_id": {
                        "type": "string",
                        "description": "The id of the call transcript that needs to be processed"
                    }
                },
                "required": ["call_transcript_id"]
            }
        },
        {
            "name": "find_missing_field_values",
            "description": "Finds required field values that might be missing from extracted entity JSON output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "extracted_entity_output": {
                        "type": "string",
                        "description": "The JSON output from the extract_entities function"
                    }
                },
                "required": ["extracted_entity_output"]
            }
        },
        {
            "name": "insert_transcript_summary_to_database",
            "description": "Inserts the final version of the extracted entity JSON output to a database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "call_transcript_id": {
                        "type": "string",
                        "description": "The id of the call transcript that was processed"
                    },
                    "final_extracted_entity_output": {
                        "type": "string",
                        "description": "The complete JSON output, after missing field values have been applied if necessary."
                    }
                },
                "required": ["call_transcript_id", "final_extracted_entity_output"]
            }
        }
    ]
}

llm_config_manager = {
    "config_list": config_list,
    "seed": 41,
    "temperature": 0,
    "timeout": 60,
}

entities_extractor_agent_prompt = '''
    You are a helpful assistant that has strong Python skills and knows how to use Python to extract text based entities from call transcripts.
    Make sure to include all the fields that are mentioned in the provided schema.
    Do not ask any questions. 
    '''

entities_extractor_agent = ChainlitAssistantAgent(
    name="entities_extractor_agent",
    system_message=entities_extractor_agent_prompt,
    llm_config=llm_config,
    description='''
     This agent has strong Python skills and is responsible for extracting entities from call transcripts. 
    '''
)


engineering_agent_prompt = '''
    You are primarily responsible for analyzing the output from the entities_extractor_agent 
    to determine if there are any required fields that are missing values in the output.
    Use functions provided in the group chat.
    Do not ask any questions and specifically do not ask if further assistance is required. Just do your work and move on!
    '''

engineering_agent = ChainlitAssistantAgent(
    name="engineering_agent",
    system_message=engineering_agent_prompt,
    llm_config=llm_config,
    description="""
    When the entities_extractor_agent is finished, this agent is proficient at using Python to find fields that are missing values
    in JSON objects based on either a JSON or pydantic model schema. If there are missing fields, then those missing fields should be given 
    to the user_proxy for human feedback. This agent is also responsible for updating the JSON output with the missing field values provided
    by the human. 
    """
)

# reporting_agent_prompt = '''
#     You are a helpful assistant who is an expert in taking in a JSON object and then generating
#     output that is both pleasing to the eye and useful for the end user.
#
#     You must create both a JSON and markdown version of the output. The content of the markdown version should be the same
#     as what is in the JSON output.
#     '''
#
# reporting_agent = ChainlitAssistantAgent(
#     name="reporting_agent",
#     system_message=reporting_agent_prompt,
#     llm_config=llm_config,
#     description="""
#         When the database_analyst_agent has finished inserting the call transcript into the database, this agent
#         is responsible for generating the final output that will be presented to the end user.
#     """
# )

reporting_agent_prompt = '''
    You are a helpful assistant who is an expert at using Python to generate markdown reports from JSON. You will create and return a markdown
    report that accurately reflects the final extracted entities output. Do not return any other type of output except for the markdown report.
    '''

reporting_agent = ChainlitAssistantAgent(
    name="reporting_agent",
    system_message=reporting_agent_prompt,
    llm_config=llm_config,
    description="""
        When the database_analyst_agent has finished inserting the call transcript into the database, this agent 
        is responsible for generating the final markdown report that must be presented to the end user. 
    """
)

database_analyst_agent_prompt = '''
    You are a helpful assistant that is proficient with databases and specifically inserting transcript summaries to a database.
    Do not ask any questions. 
    '''

database_analyst_agent = ChainlitAssistantAgent(
    name="database_analyst_agent",
    system_message=database_analyst_agent_prompt,
    llm_config=llm_config,
    description='''
     When the engineering_agent has indicated that there are no missing values for the required fields,
     this agent is responsible for inserting the call transcript summary JSON output to a database.
     IMPORTANT: when this agent is finished, the reporting_agent should be called to generate the final output!
    '''
)

function_executor_agent_prompt = '''
This agent executes all functions and code for the group. 
Anytime an agent needs information they will prompt this agent with the indicated function and arguments.
'''
function_executor_agent = ChainlitAssistantAgent(
    name="function_executor_agent",
    system_message=function_executor_agent_prompt,
    llm_config=llm_config,
    description="""
        Anytime an agent needs information they will prompt this agent with the necessary code, function, and arguments.
    """
)
function_executor_agent.register_function(
    function_map={
        "extract_entities": extract_entities,
        "find_missing_field_values": find_missing_field_values,
        "insert_transcript_summary_to_database": insert_transcript_summary_to_database
    },
)


terminator_agent = ChainlitAssistantAgent(
    name="terminator_agent",
    system_message="You are a helpful assistant that only does one thing and that is to output TERMINATE",
    llm_config=llm_config,
    description="""
        After the reporting_agent has completed its work, this agent should be called so that the chat conversation can be terminated.
    """
)


user_proxy = ChainlitUserProxyAgent(
    name="user_proxy",
    is_termination_msg=lambda msg: "TERMINATE" in msg["content"],
    code_execution_config=False,
    human_input_mode="ALWAYS",
)


groupchat = ExecutorGroupchat(agents=[user_proxy, entities_extractor_agent, engineering_agent, reporting_agent,
        function_executor_agent, database_analyst_agent, terminator_agent],
        messages=[], max_round=50, dedicated_executor=function_executor_agent)

manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config_manager)


def start_chat(message):
    print(f"message: {message}")
    user_proxy.initiate_chat(manager, message=message.content)