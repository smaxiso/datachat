import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.ui.streamlit_app import main

class TestStreamlitApp:
    @patch('src.ui.streamlit_app.st')
    @patch('src.ui.streamlit_app.requests')
    def test_main(self, mock_requests, mock_st):
        # Setup mocks
        class SessionStateMock(dict):
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                self[key] = value
            def __delattr__(self, key):
                try:
                    del self[key]
                except KeyError:
                    raise AttributeError(key)
        
        mock_st.session_state = SessionStateMock()
        mock_st.session_state.token = "fake-token"
        mock_st.chat_input.return_value = "question"
        
        # Mock requests response
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {
            "success": True, 
            "interpretation": "result",
            "data": [],
            "sql_generated": "SELECT *",
            "metadata": {}
        }
        mock_requests.post.return_value = mock_post_response

        # Mock GET responses
        def get_side_effect(url, **kwargs):
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            if "health" in url:
                mock_resp.json.return_value = {"status": "healthy"}
            elif "schema" in url:
                mock_resp.json.return_value = {
                    "source_name": "test_db", 
                    "tables": ["table1"], 
                    "schema_summary": "summary"
                }
            elif "metrics" in url:
                mock_resp.json.return_value = {}
            return mock_resp
            
        mock_requests.get.side_effect = get_side_effect
        
        main()
        
        # Verification
        mock_st.chat_input.assert_called()

    @patch('src.ui.streamlit_app.st')
    @patch('src.ui.streamlit_app.requests')
    def test_login_flow(self, mock_requests, mock_st):
        # Setup mocks
        class SessionStateMock(dict):
            def __getattr__(self, key):
                return self.get(key)
            def __setattr__(self, key, value):
                self[key] = value
            def __delattr__(self, key):
                try:
                    del self[key]
                except KeyError:
                    raise AttributeError(key)
        
        mock_st.session_state = SessionStateMock()
        mock_st.session_state.token = None
        mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
        
        main()
        
        # Verify login form elements called
        mock_st.text_input.assert_any_call("Username")
        mock_st.text_input.assert_any_call("Password", type="password")
        mock_st.chat_input.assert_not_called()
