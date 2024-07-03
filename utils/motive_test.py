import duckdb
import pandas as pd
import os
import re
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.sqlite import SqliteSaver

from typing_extensions import TypedDict
from typing import List, Annotated, Dict, Any


llm = ChatGroq(temperature=0, model_name="Llama3-70b-8192")
#llm = ChatOpenAI(model="gpt-4")

db_path = 'db/financial_advisor_data.db'

class AgentState(TypedDict):
    subject_grader_answer: str
    user_intent_generator_answer: str
    extract_entities_answer: str
    sql_grader_answer: str
    query: str
    question: str
    data: Dict[str, Any]
    text_answer: str
    no_financial_question_answer: str

def initialize_db():

    client_file_path = 'data/financial_advisor_clients.csv'
    target_file_path = 'data/client_target_allocations.csv'
    # Load CSV files
    financial_advisor_clients = pd.read_csv(client_file_path)
    client_target_allocations = pd.read_csv(target_file_path)

    financial_advisor_clients.columns = [re.sub(r'\W+', '_', col).lower() for col in financial_advisor_clients.columns]
    client_target_allocations.columns = [re.sub(r'\W+', '_', col).lower() for col in client_target_allocations.columns]

    # Connect to DuckDB (or create it if it doesn't exist)
    con = duckdb.connect(db_path)

    # Check if the tables exist
    tables = con.execute("SHOW TABLES").fetchdf()['name'].tolist()

    # Create and insert data into financial_advisor_clients table if it doesn't exist
    if 'financial_advisor_clients' not in tables:
        con.execute("CREATE TABLE financial_advisor_clients AS SELECT * FROM financial_advisor_clients")
    else:
        print("Table 'financial_advisor_clients' already exists.")

    # Create and insert data into client_target_allocations table if it doesn't exist
    if 'client_target_allocations' not in tables:
        con.execute("CREATE TABLE client_target_allocations AS SELECT * FROM client_target_allocations")
    else:
        print("Table 'client_target_allocations' already exists.")

    print(con.execute("SELECT * FROM financial_advisor_clients").fetchdf())
    print(con.execute("SELECT * FROM client_target_allocations").fetchdf())

def get_table_schema(table_name):
    con = duckdb.connect(db_path)
    schema = con.execute(f"SELECT column_name, column_type FROM (DESCRIBE {table_name}) ").fetchdf()
    return schema

def subject_grader(State):
    print("--- SUBJECT GRADER NODE ---")
    question = State.get('question', '')
    
    # Prompt to be improved
    prompt = PromptTemplate(
        template="""
            
            you are a financial advisor to grader if the following question is about financial/price data or about clients portfolio.
            Question: {question}

            Return only yes or no.
            
        """,
        input_variables=["question"],
    )

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "question": question,
    })

    print("Subject grader answer:", answer)

    ##Setted as yes to allow tests
    return {
        "subject_grader_answer": "yes",
    }

def user_intent_generator(State):
    print("--- USER INTENT GENERATOR NODE ---")
    return {
        "user_intent_generator_answer": "yes"
    }

def extract_entities(State):
    print("--- EXTRACT ENTITIES NODE ---")
    return {
        "extract_entities_answer": "yes"
    }

def sql_generator(State):
    print("--- GENERATE QUERY NODE ---")
    question = State.get('question', '')
    financial_advisor_clients_schema = get_table_schema('financial_advisor_clients')
    client_target_allocations_schema = get_table_schema('client_target_allocations')

    print(financial_advisor_clients_schema.to_string(index=False))

    prompt = PromptTemplate(
        template="""
            With this data schema:
            TABLE financial_advisor_clients
            {financial_advisor_clients_schema}
            and this data schema:
            TABLE client_target_allocations
            {client_target_allocations_schema}

            you are a helpful SQL assistant financial advisor to answer the following question:
            {question}

            Return only the sql query that will answer the question. Remember to use ilike without % for case-insensitive matching.
            
        """,
        input_variables=["question", "financial_advisor_clients_schema", "client_target_allocations_schema"],
    )

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "question": question,
        "financial_advisor_clients_schema": financial_advisor_clients_schema.to_string(index=False),
        "client_target_allocations_schema": client_target_allocations_schema.to_string(index=False)
    })

    pattern = r'```(.*?)```'
    match = re.search(pattern, answer, re.DOTALL)
    extracted_answer = match.group(1).strip() if match else answer
    extracted_answer = extracted_answer.replace('\n', ' ')

    print(extracted_answer)
    return {
        "query": extracted_answer,
    }

def sql_grader(State):
    print("--- SQL GRADER NODE ---")
    return {
        "sql_grader_answer": "yes"
    }

def execute_query(State):
    print("--- EXECUTE QUERY NODE ---")
    query = State.get('query', '')
    con = duckdb.connect(db_path)
    result = con.execute(query).fetchdf()
    return {
        'data': result.to_dict(orient='records')
    }

def generate_answer(State):
    print("--- GENERATE ANSWER NODE ---")
    question = State.get('question', '')
    data = State.get('data', {})

    prompt = PromptTemplate(
        template="""
            You are a helpful assistant financial advisor to generate a user-friendly response to the following question:
            {question}
            and this data:
            {data}

            Return only the user-friendly response.
            
        """,
        input_variables=["question", "data"],
    )

    chain = prompt | llm | StrOutputParser()

    answer = chain.invoke({
        "question": question,
        "data": data,
    })

    return {
        "text_answer": answer,
        "no_financial_question_answer": None

    }

def no_financial_question(State):
    print("--- NO FINANCIAL QUESTION ANSWER NODE ---")
    
    return {
        "no_financial_question_answer": "Sorry, I don't know how to answer that question."
    }

def get_subject_grader(State) -> str:
    subject_grader_answer = State.get('subject_grader_answer', '')
    return subject_grader_answer.lower().rstrip()

memory1 = SqliteSaver.from_conn_string(":memory:")
def execute_graph(
        question: str,
        chat_context: str,
):
    thread = {"configurable": {"thread_id": chat_context}}

    workflow = workflow = StateGraph(AgentState)
    workflow.add_node("subject_grader", subject_grader)
    workflow.add_node('user_intent_generator', user_intent_generator)
    workflow.add_node("extract_entities", extract_entities)
    workflow.add_node("sql_generator", sql_generator)
    workflow.add_node("sql_grader", sql_grader)
    workflow.add_node("execute_query", execute_query)
    workflow.add_node("generate_answer", generate_answer)
    
    workflow.add_node("no_financial_question", no_financial_question)

    workflow.set_entry_point("subject_grader")
    workflow.add_conditional_edges(
        "subject_grader",
        get_subject_grader,
        {
            "yes": "user_intent_generator",
            "no": "no_financial_question",
        }
    )
    workflow.add_edge("user_intent_generator", "extract_entities")
    workflow.add_edge("extract_entities", "sql_generator")
    workflow.add_edge("sql_generator", "sql_grader")
    workflow.add_edge("sql_grader", "execute_query")
    workflow.add_edge("execute_query", "generate_answer")
    workflow.add_edge("generate_answer", END)


    workflow.add_edge("no_financial_question", END)

    app = workflow.compile(checkpointer=memory1)

    inputs = {
        "question": question,
    }
    response = app.invoke(inputs, thread)

    if response.get('no_financial_question_answer', None) is not None:
        return {
            "text_answer": response.get('no_financial_question_answer', None),
        }

    return {
        "query": response.get('query', ''),
        "data": response.get('data', ''),
        "text_answer": response.get('text_answer', ''),
    }