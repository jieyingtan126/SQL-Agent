import os
from dotenv import load_dotenv
import streamlit as st
import sqlite3
import json
from agent import app

# Load environment variables
load_dotenv()
    
def get_table_columns(table_name):
    """
    Fetches the column names for a specified table using SQLite PRAGMA.
    Used for displaying schema metadata in the Streamlit sidebar.
    """
    try:
        db_path = os.getenv("DATABASE_URL", "data/ecommerce.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # PRAGMA table_info returns (id, name, type, notnull, default_value, pk)
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        return {"error": f"Error loading columns: {str(e)}"}
    
def load_business_rules():
    """
    Returns business definitions and formulas.
    """
    try:
        br_path = os.getenv("BUSINESS_RULES_URL", "data/business_rules.json")
        with open(br_path, "r") as f:
            return json.load(f)
    except Exception as e:
        return {"error": f"Business rules error: {str(e)}"}
    
st.set_page_config(page_title="SQL Agent", page_icon="📊")

# Initialize session state
if "provider" not in st.session_state:
    env_provider = os.getenv("MODEL_PROVIDER", "OLLAMA (local)")
    if env_provider == "OLLAMA (local)":
        st.session_state.provider = "OLLAMA (local)"
    else:
        st.session_state.provider = env_provider

# Define the callback function
def on_provider_change():
    # Update the state immediately when the user clicks
    st.session_state.provider = st.session_state.provider_select
    # Update the environment variable so the agent's os.getenv() sees it
    os.environ["MODEL_PROVIDER"] = st.session_state.provider_select

with st.sidebar:
    st.header("Settings")

    # Selectbox for the user to switch providers
    available_providers = ["GROQ", "HUGGINGFACE", "OPENROUTER", "OLLAMA (local)"]
    st.selectbox(
        "Model Provider",
        options=available_providers,
        index=available_providers.index(st.session_state.provider),
        key="provider_select",
        on_change=on_provider_change
    )
    provider = st.session_state.provider

    # Display model name
    if provider == "GROQ":
        active_model = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
    elif provider == "HUGGINGFACE":
        active_model = os.getenv("HUGGINGFACE_MODEL_NAME", "meta-llama/Llama-3.3-70B-Instruct")
    elif provider == "OPENROUTER":
        active_model = os.getenv("OPENROUTER_MODEL_NAME", "openai/gpt-oss-120b:free")
    else:
        active_model = os.getenv("OLLAMA_MODEL_NAME", "qwen3.5:9b")

    st.caption("Model")
    st.code(active_model, language="yaml")

    st.markdown("---")

    st.header("About the Database")
    st.markdown("This agent has access to an e-commerce SQLite database.")
    tables = ["Customers", "Products", "Orders", "Order_Items"]
    for table in tables:
        with st.expander(f"{table}"):
            columns = get_table_columns(table)
            st.write(", ".join(columns))
    st.markdown("---")

    st.header("Business Rules")
    rules = load_business_rules()
    for rule_name, description in rules.items():
        display_name = rule_name.replace("_", " ").title()
        with st.expander(display_name):
            st.write(description)

st.title("SQL Agent")

st.markdown("I bridge the gap between natural language and data insights.")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask me anything about the e-commerce data"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        with st.spinner("Thinking and Querying Database..."):
            inputs = {"messages": [("user", prompt)]}
            result = app.invoke(inputs, config={"recursion_limit": 25,"configurable": {"provider": st.session_state.provider}})

            with st.expander("🔍 Show Agent Thought Process"):
                # Skip the first message (the user prompt) and the last (final answer)
                process_messages = result["messages"][1:-1]
                
                for msg in process_messages:
                    # Show what actions the agent decided to take (Tool Calls)
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            st.write(f"**Step:** Agent decided to use `{tool_call['name']}`")
                            if "query" in tool_call["args"]:
                                st.code(tool_call["args"]["query"], language="sql")
                            elif "table_name" in tool_call["args"]:
                                st.write(f"Inspecting table: `{tool_call['args']['table_name']}`")
                    
                    # Show the raw result from the database (Tool Messages)
                    elif msg.type == "tool":
                        st.caption("Data retrieved:")
                        # Truncate long results for UI cleanliness
                        content = str(msg.content)
                        st.text(content[:300] + "..." if len(content) > 300 else content)

            # Extract the final response
            final_message = result["messages"][-1]
            full_response = final_message.content
            
            # Display the final response
            message_placeholder.markdown(full_response)
    
    # Persist the assistant's response to the session history
    st.session_state.messages.append({"role": "assistant", "content": full_response})