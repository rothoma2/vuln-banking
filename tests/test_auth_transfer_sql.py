import unittest
from unittest.mock import patch

from flask import Flask

import auth


class MockCursor:
    def __init__(self, recipient_rows=None, fail_update_for=None):
        self.calls = []
        self._recipient_rows = recipient_rows or {"ACC002' OR '1'='1": ('recipient', 1000.0)}
        self._updated_recipient = None
        self._fail_update_for = fail_update_for or set()
        self._last_query = None
        self._last_params = None
        self.rowcount = 0

    def execute(self, query, params=None):
        self.calls.append((query, params))
        self._last_query = query
        self._last_params = params
        self.rowcount = 1
        if query == "UPDATE users SET balance = balance + ? WHERE account_number=?":
            self._updated_recipient = params[1]
            if self._updated_recipient in self._fail_update_for:
                self.rowcount = 0
            else:
                self.rowcount = 1 if self._updated_recipient in self._recipient_rows else 0

    def fetchone(self):
        if self._last_query == "SELECT username, balance FROM users WHERE account_number=?":
            return self._recipient_rows.get(self._last_params[0])
        if self._last_query == "SELECT balance FROM users WHERE id=?":
            return (1000.0,)
        return None


class MockConnection:
    def __init__(self, recipient_rows=None, fail_update_for=None):
        self.cursor_obj = MockCursor(recipient_rows=recipient_rows, fail_update_for=fail_update_for)
        self.committed = False
        self.rolled_back = False
        self.closed = False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

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
        body = response.get_json()
        self.assertEqual(body['recipient'], 'recipient')
        self.assertEqual(body['recipient_new_balance'], 1100.0)

        calls = mock_conn.cursor_obj.calls
        self.assertEqual(calls[0], ("SELECT username, balance FROM users WHERE account_number=?", (malicious_to_account,)))
        self.assertEqual(calls[1], ("SELECT balance FROM users WHERE id=?", (1,)))
        self.assertEqual(
            calls[2],
            ("UPDATE users SET balance = balance - ? WHERE id=?", (100.0, 1)),
        )
        self.assertEqual(
            calls[3],
            ("UPDATE users SET balance = balance + ? WHERE account_number=?", (100.0, malicious_to_account)),
        )
        self.assertTrue(mock_conn.committed)

    def test_transfer_rolls_back_when_recipient_update_affects_no_rows(self):
        token = auth.generate_token(user_id=1, username='alice')
        missing_account = "ACC404"
        mock_conn = MockConnection(
            recipient_rows={missing_account: ('recipient', 1000.0)},
            fail_update_for={missing_account},
        )

        with patch('auth.sqlite3.connect', return_value=mock_conn):
            response = self.client.post(
                '/api/transfer',
                query_string={'token': token},
                json={'to_account': missing_account, 'amount': '100'},
            )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(mock_conn.committed)
        self.assertTrue(mock_conn.rolled_back)


if __name__ == '__main__':
    unittest.main()
