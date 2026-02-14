"""
Streamlit Chat UI for GenAI Data Platform.

This provides an interactive chat interface for querying data.
"""

import streamlit as st
import requests
import pandas as pd
import os
from typing import Dict, Any
from src.utils.constants import AppMetadata

# API Configuration
API_URL = os.getenv('API_URL', 'http://localhost:8000')

st.set_page_config(
    page_title=AppMetadata.TITLE,
    page_icon=AppMetadata.ICON,
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def login_user(username, password):
    """Login user and get access token."""
    try:
        response = requests.post(
            f"{API_URL}/token",
            data={"username": username, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()
        else:
            return None
    except:
        return None

def get_headers():
    """Get request headers with token."""
    if 'token' in st.session_state:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}

def check_api_health() -> bool:
    """Check if API is healthy."""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=AppMetadata.API_TIMEOUT)
        return response.status_code == 200
    except:
        return False

def get_schema_info() -> Dict[str, Any]:
    """Get database schema information from API."""
    try:
        response = requests.get(f"{API_URL}/api/schema", headers=get_headers(), timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def get_metrics() -> Dict[str, Any]:
    """Get performance metrics from API."""
    try:
        response = requests.get(f"{API_URL}/api/metrics", timeout=5) # Metrics is protected? No, checking main.py... it is NOT protected in my previous read?
        # Let's check main.py again. get_metrics was at lines 300+.
        # It was NOT protected in the previous read.
        # But logically it SHOULD be.
        # I'll add headers anyway, it won't hurt.
        response = requests.get(f"{API_URL}/api/metrics", headers=get_headers(), timeout=5)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def execute_query(question: str) -> Dict[str, Any]:
    """Execute a natural language query."""
    try:
        response = requests.post(
            f"{API_URL}/api/query",
            json={"question": question},
            headers=get_headers(),
            timeout=AppMetadata.QUERY_TIMEOUT
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
             return {"success": False, "error_message": "Session expired. Please login again."}
    except Exception as e:
        return {
            "success": False,
            "error_message": f"API request failed: {str(e)}"
        }
    return None



def main():
    # Header
    st.markdown(f'<div class="main-header">{AppMetadata.ICON} DataChat</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'token' not in st.session_state:
        st.session_state.token = None
    
    # Login Flow
    if not st.session_state.token:
        st.markdown('<div class="sub-header">Please login to continue</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                
                if submit:
                    token_data = login_user(username, password)
                    if token_data:
                        st.session_state.token = token_data['access_token']
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
        return

    # Authenticated View
    st.markdown('<div class="sub-header">Ask questions about your data in natural language</div>', unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("⚙️ System Status")
        if st.button("Logout"):
            st.session_state.token = None
            st.rerun()
            
        # Health check
        if check_api_health():
            st.success("✅ API Connected")
        else:
            st.error("❌ API Disconnected")
            st.info(f"Check if API is running at {API_URL}")
        
        st.divider()
        
        # Schema information
        st.header("📊 Database Schema")
        schema_info = get_schema_info()
        
        if schema_info:
            st.write(f"**Database:** {schema_info['source_name']}")
            st.write(f"**Tables:** {len(schema_info['tables'])}")
            
            with st.expander("View Tables"):
                for table in schema_info['tables']:
                    st.write(f"- {table}")
            
            with st.expander("View Full Schema"):
                st.code(schema_info['schema_summary'], language='text')
        else:
            st.warning("Schema information not available")
        
        st.divider()
        
        # Query History
        st.header("📜 Recent Queries")
        if 'messages' in st.session_state and st.session_state.messages:
            user_queries = [m['content'] for m in st.session_state.messages if m['role'] == 'user']
            for i, q in enumerate(reversed(user_queries[-5:])):
                if st.button(f"↻ {q[:40]}...", key=f"hist_{i}", use_container_width=True):
                    st.session_state.current_prompt = q
                    st.rerun()
        else:
            st.caption("No history yet")

        st.divider()
        
        # Metrics Dashboard
        st.header("🚀 Performance")
        metrics = get_metrics()
        if metrics:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Success Rate", metrics.get('success_rate', '0%'))
                st.metric("Total Cost", metrics.get('total_cost', '$0.00'))
            with col2:
                st.metric("Avg Time", metrics.get('avg_query_time', '0s'))
                st.metric("Queries", metrics.get('total_queries', 0))
        else:
            st.warning("Metrics unavailable")

        st.divider()
        
        # Example queries
        st.header("💡 Example Queries")
        example_queries = [
            "What are the top 5 customers by total revenue?",
            "Show me sales trends by month",
            "Which products have the highest profit margin?",
            "Compare revenue between different regions",
            "What is the average order value?"
        ]
        
        for example in example_queries:
            if st.button(example, key=example, use_container_width=True):
                st.session_state.example_query = example

    # Initialize session state for messages
    if 'messages' not in st.session_state:
        st.session_state.messages = []

    if 'example_query' in st.session_state:
        st.session_state.current_question = st.session_state.example_query
        del st.session_state.example_query

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            
            # Display data if available
            if "data" in message and message["data"] is not None:
                df = pd.DataFrame(message["data"])
                st.dataframe(df, use_container_width=True)
            
            # Display SQL if available
            if "sql" in message and message["sql"]:
                with st.expander("📝 View SQL Query"):
                    st.code(message["sql"], language="sql")
            
            # Display metadata
            if "metadata" in message and message["metadata"]:
                with st.expander("ℹ️ Query Details"):
                    meta = message["metadata"]
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Rows", meta.get("row_count", "N/A"))
                    with col2:
                        exec_time = meta.get("execution_time", 0)
                        st.metric("Execution Time", f"{exec_time:.2f}s" if exec_time else "N/A")
                    with col3:
                        tokens = meta.get("tokens_used", "N/A")
                        st.metric("Tokens Used", tokens)

    # Chat input
    if 'current_prompt' in st.session_state:
        prompt = st.session_state.current_prompt
        del st.session_state.current_prompt
        # Auto-submit workaround not robust here without rerun, but simplistic for now.
        pass
    else:
        prompt = st.chat_input("Ask a question about your data...")

    if prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Execute query
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = execute_query(prompt)
            
            if result and result.get("success"):
                # Display interpretation
                st.write(result["interpretation"])
                
                # Display data
                if result.get("data"):
                    st.dataframe(pd.DataFrame(result["data"]), use_container_width=True)
                
                # Display SQL
                if result.get("sql_generated"):
                    with st.expander("📝 View SQL Query"):
                        st.code(result["sql_generated"], language="sql")
                
                # Display metadata
                if result.get("metadata"):
                    with st.expander("ℹ️ Query Details"):
                        meta = result["metadata"]
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Rows", meta.get("row_count", "N/A"))
                        with col2:
                            exec_time = meta.get("execution_time", 0)
                            st.metric("Execution Time", f"{exec_time:.2f}s" if exec_time else "N/A")
                        with col3:
                            tokens = meta.get("tokens_used", "N/A")
                            st.metric("Tokens Used", tokens)
                
                # Add to message history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": result["interpretation"],
                    "data": result.get("data"),
                    "sql": result.get("sql_generated"),
                    "metadata": result.get("metadata")
                })
            else:
                error_msg = result.get("error_message", "Unknown error occurred") if result else "Failed to connect to API"
                st.error(f"❌ Error: {error_msg}")
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"Error: {error_msg}"
                })

    # Footer
    st.divider()
    st.caption(AppMetadata.FOOTER)

if __name__ == "__main__":
    main()
