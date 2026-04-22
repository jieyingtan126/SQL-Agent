import os
from dotenv import load_dotenv
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from tools import list_tables, get_schema, execute_query, get_business_rule

# Load environment variables
load_dotenv()

# 1. Define the state
class State(TypedDict):
    messages: Annotated[list, add_messages]

# 2. Initialize the LLM
def get_llm(provider_override=None):
    """
    Initializes and returns the model based on the MODEL_PROVIDER.
    Supports GROQ, HUGGINGFACE, OPENROUTER, and OLLAMA.
    Sets temperature to 0 to ensure deterministic output for SQL generation.
    """
    # Use the override if provided, otherwise fallback to env var
    provider = provider_override or os.getenv("MODEL_PROVIDER", "OLLAMA (local)")
    
    if provider == "GROQ":
        return ChatGroq(
            model=os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile"),
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )
    elif provider == "HUGGINGFACE":
        return ChatOpenAI(
            model=os.getenv("HUGGINGFACE_MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct"),
            openai_api_key=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
            base_url=os.getenv("HUGGINGFACE_BASE_URL", "https://router.huggingface.co/v1"),
            temperature=0
        )
    elif provider == "OPENROUTER":
        return ChatOpenAI(
            model=os.getenv("OPENROUTER_MODEL_NAME", "openai/gpt-oss-120b:free"),
            openai_api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            temperature=0
        )
    else:
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL_NAME", "qwen3.5:9b"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0
        )

llm = get_llm()

# 3. Bind tools
tools = [list_tables, get_schema, execute_query, get_business_rule]
llm_with_tools = llm.bind_tools(tools)

# 4. Define the system prompt
SYSTEM_PROMPT = """
    ### ROLE
    You are a Data Analyst with READ-ONLY access to an e-commerce SQLite database.
    
    ### RULES
    1. Always use the exact casing for table and column names as shown in the schema. Even if the user uses lowercase, ensure the query aligns with the schema's defined casing.
    2. Apply '$' prefix and 2 decimal places only to monetary values such as price, revenue, and profit. Do not apply the '$' or extra decimals to non-monetary values such as counts, ranks, and IDs.
    3. Limit results to 10 rows unless asked for more.
    4. You are strictly prohibited from modifying the database.
    
    ### ERROR HANDLING & SELF-CORRECTION
    1. If `execute_query` fails with a `ValueError` (e.g., not found in database), use `list_tables`.
    2. If `execute_query` fails with a `OperationalError` (e.g., no such column), use `get_schema` on that table again.
    3. Compare your generated query against the table name or column name to find the naming mismatch.
    4. Correct the query and execute again.
"""

# 5. Define the reasoning engine
def call_model(state: State):
    """Processes the current conversation state and determines the next action."""
    messages = [("system", SYSTEM_PROMPT)] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 6. Build the workflow
workflow = StateGraph(State)

# Define the nodes for reasoning and action
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# Set the starting point of execution
workflow.set_entry_point("agent")

# Define the logic for the loop
def should_continue(state: State):
    """Determines if the agent should keep using tools or give a final answer."""
    last_message = state["messages"][-1]
    # If the LLM requests a tool, route to the action node
    if last_message.tool_calls:
        return "tools"
    # Otherwise, terminate the workflow
    return END

# Define the iterative feedback loop
workflow.add_conditional_edges("agent", should_continue)

# Return tool results to the agent for analysis
workflow.add_edge("tools", "agent")

# 7. Compile the workflow
app = workflow.compile()