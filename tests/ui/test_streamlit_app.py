import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import pytest
from unittest.mock import MagicMock, patch
from src.ui.streamlit_app import main

class TestStreamlitApp:
    @patch('src.ui.streamlit_app.st')
    @patch('src.ui.streamlit_app.QueryOrchestrator')
    def test_main(self, mock_orchestrator, mock_st):
        mock_st.chat_input.return_value = "question"
        main()
        mock_st.write.assert_called()
