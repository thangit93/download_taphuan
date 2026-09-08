import unittest
from unittest.mock import Mock, patch

import http_client


class CreateSessionTests(unittest.TestCase):
    @patch("http_client.requests.Session")
    @patch("http_client.ssl.create_default_context")
    def test_adds_missing_intermediate_to_verified_context(
        self, create_default_context, session_class
    ):
        context = Mock()
        create_default_context.return_value = context

        http_client.create_session()

        create_default_context.assert_called_once_with(cafile=http_client.certifi.where())
        context.load_verify_locations.assert_called_once_with(
            cafile=http_client.MISSING_INTERMEDIATE
        )
        session_class.return_value.mount.assert_called_once()
