"""Tests for core.llm_client and main entry point logic."""

import unittest
from unittest.mock import MagicMock, patch

from core.llm_client import LLMClient, get_llm_response
import main


class TestLLMClient(unittest.TestCase):
    def test_fallback_mock_response_when_no_keys(self):
        client = LLMClient(gemini_api_key=None, ollama_url=None)
        res = client.query("Привет, как дела?")
        self.assertIn("API-ключ Gemini (GEMINI_API_KEY) или Ollama (OLLAMA_URL) не настроен", res)

    @patch("requests.post")
    def test_ollama_query(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"response": "Привет! Всё отлично."}
        mock_post.return_value = mock_resp

        client = LLMClient(ollama_url="http://localhost:11434")
        res = client.query("Привет")
        self.assertEqual(res, "Привет! Всё отлично.")

    def test_gemini_query_mock(self):
        client = LLMClient()
        mock_gemini_client = MagicMock()
        mock_gen_content = MagicMock()
        mock_gen_content.text = "Здравствуйте! Чем я могу помочь?"
        mock_gemini_client.models.generate_content.return_value = mock_gen_content
        client.gemini_client = mock_gemini_client

        res = client.query("Привет")
        self.assertEqual(res, "Здравствуйте! Чем я могу помочь?")

    def test_module_get_llm_response(self):
        with patch("core.llm_client.LLMClient.query", return_value="Test response"):
            res = get_llm_response("Hello")
            self.assertEqual(res, "Test response")


class TestMainEntryPoint(unittest.TestCase):
    def test_init_app_index_background(self):
        mock_app_finder = MagicMock()
        main.init_app_index_background(mock_app_finder)
        mock_app_finder.scan_directories.assert_called_once()


if __name__ == "__main__":
    unittest.main()
