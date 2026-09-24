import unittest
from unittest.mock import patch

from flask import Flask

import auth


class MockCursor:
    def __init__(self):
        self.calls = []
        self._results = [
            (1000.0,),
            ('recipient', 1100.0),
        ]

    def execute(self, query, params=None):
        self.calls.append((query, params))

    def fetchone(self):
        return self._results.pop(0)


class MockConnection:
    def __init__(self):
        self.cursor_obj = MockCursor()
        self.committed = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class TransferSqlInjectionTest(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        auth.init_auth_routes(self.app)
        self.client = self.app.test_client()

    def test_transfer_uses_parameterized_queries(self):
        mock_conn = MockConnection()
        token = auth.generate_token(user_id=1, username='alice')
        malicious_to_account = "ACC002' OR '1'='1"

        with patch('auth.sqlite3.connect', return_value=mock_conn):
            response = self.client.post(
                '/api/transfer',
                query_string={'token': token},
                json={'to_account': malicious_to_account, 'amount': '100'},
            )

        self.assertEqual(response.status_code, 200)

        calls = mock_conn.cursor_obj.calls
        self.assertEqual(calls[0], ("SELECT balance FROM users WHERE id=?", (1,)))
        self.assertEqual(calls[1], ("UPDATE users SET balance = balance - ? WHERE id=?", (100.0, 1)))
        self.assertEqual(
            calls[2],
            ("UPDATE users SET balance = balance + ? WHERE account_number=?", (100.0, malicious_to_account)),
        )
        self.assertEqual(
            calls[3],
            ("SELECT username, balance FROM users WHERE account_number=?", (malicious_to_account,)),
        )


if __name__ == '__main__':
    unittest.main()
