import ast
import http.client
import ipaddress
import socket
import ssl
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse


APP_PATH = Path('/home/runner/work/vuln-banking/vuln-banking/app.py')
TARGET_NAMES = {
    'MAX_REMOTE_IMAGE_BYTES',
    'InvalidRemoteImageURLError',
    'RemoteImageTooLargeError',
    'RemoteImageHTTPStatusError',
    'remote_image_size_limit_message',
    'parse_public_image_url',
    'resolve_public_ip',
    'ValidatedHTTPConnection',
    'ValidatedHTTPSConnection',
    'fetch_public_image',
    'download_public_image',
}


def load_remote_fetch_namespace():
    source = APP_PATH.read_text()
    tree = ast.parse(source, filename=str(APP_PATH))
    selected_nodes = []

    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in TARGET_NAMES for name in targets):
                selected_nodes.append(node)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in TARGET_NAMES:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        'http': http,
        'ipaddress': ipaddress,
        'socket': socket,
        'ssl': ssl,
        'urlparse': urlparse,
    }
    exec(compile(module, str(APP_PATH), 'exec'), namespace)
    return namespace


REMOTE_FETCH = load_remote_fetch_namespace()


class RemoteImageFetchTests(unittest.TestCase):
    def test_download_public_image_accepts_public_url(self):
        with patch.dict(REMOTE_FETCH, {
            'resolve_public_ip': lambda hostname, port: '93.184.216.34',
            'fetch_public_image': lambda parsed, resolved_ip: (200, b'image-bytes'),
        }):
            parsed, response_body = REMOTE_FETCH['download_public_image']('https://example.com/avatar.png')

        self.assertEqual(parsed.hostname, 'example.com')
        self.assertEqual(response_body, b'image-bytes')

    def test_download_public_image_rejects_private_destination(self):
        with patch.dict(REMOTE_FETCH, {'resolve_public_ip': lambda hostname, port: None}):
            with self.assertRaisesRegex(REMOTE_FETCH['InvalidRemoteImageURLError'], 'Only public http\\(s\\) image URLs are allowed'):
                REMOTE_FETCH['download_public_image']('https://example.com/avatar.png')

    def test_download_public_image_rejects_redirects(self):
        with patch.dict(REMOTE_FETCH, {
            'resolve_public_ip': lambda hostname, port: '93.184.216.34',
            'fetch_public_image': lambda parsed, resolved_ip: (302, b''),
        }):
            with self.assertRaises(REMOTE_FETCH['RemoteImageHTTPStatusError']) as ctx:
                REMOTE_FETCH['download_public_image']('https://example.com/avatar.png')

        self.assertEqual(ctx.exception.status_code, 302)

    def test_download_public_image_rejects_embedded_credentials(self):
        with self.assertRaisesRegex(REMOTE_FETCH['InvalidRemoteImageURLError'], 'Only public http\\(s\\) image URLs are allowed'):
            REMOTE_FETCH['download_public_image']('******example.com/avatar.png')

    def test_resolve_public_ip_prefers_global_addresses(self):
        with patch.object(REMOTE_FETCH['socket'], 'getaddrinfo', return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
        ]):
            resolved_ip = REMOTE_FETCH['resolve_public_ip']('example.com', 443)

        self.assertEqual(resolved_ip, '93.184.216.34')

    def test_resolve_public_ip_handles_scoped_ipv6_addresses(self):
        with patch.object(REMOTE_FETCH['socket'], 'getaddrinfo', return_value=[
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('fe80::1%eth0', 443, 0, 0)),
            (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('2606:2800:220:1:248:1893:25c8:1946', 443, 0, 0)),
        ]):
            resolved_ip = REMOTE_FETCH['resolve_public_ip']('example.com', 443)

        self.assertEqual(resolved_ip, '2606:2800:220:1:248:1893:25c8:1946')

    def test_fetch_public_image_rejects_large_content_length(self):
        class FakeResponse:
            status = 200

            def getheader(self, name):
                return str(REMOTE_FETCH['MAX_REMOTE_IMAGE_BYTES'] + 1) if name == 'Content-Length' else None

            def read(self, size=-1):
                return b''

        class FakeConnection:
            def request(self, method, path, headers):
                self.request_args = (method, path, headers)

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        parsed = REMOTE_FETCH['parse_public_image_url']('http://example.com/avatar.png')
        with patch.dict(REMOTE_FETCH, {'ValidatedHTTPConnection': lambda *args, **kwargs: FakeConnection()}):
            with self.assertRaisesRegex(REMOTE_FETCH['RemoteImageTooLargeError'], str(REMOTE_FETCH['MAX_REMOTE_IMAGE_BYTES'])):
                REMOTE_FETCH['fetch_public_image'](parsed, '93.184.216.34')

    def test_fetch_public_image_rejects_streaming_overflow(self):
        class FakeResponse:
            status = 200

            def __init__(self):
                self.chunks = [b'12345678', b'9', b'']

            def getheader(self, name):
                return None

            def read(self, size=-1):
                return self.chunks.pop(0)

        class FakeConnection:
            def request(self, method, path, headers):
                self.request_args = (method, path, headers)

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        parsed = REMOTE_FETCH['parse_public_image_url']('http://example.com/avatar.png')
        with patch.dict(REMOTE_FETCH, {
            'MAX_REMOTE_IMAGE_BYTES': 8,
            'ValidatedHTTPConnection': lambda *args, **kwargs: FakeConnection(),
        }):
            with self.assertRaisesRegex(REMOTE_FETCH['RemoteImageTooLargeError'], '8 bytes'):
                REMOTE_FETCH['fetch_public_image'](parsed, '93.184.216.34')

    def test_fetch_public_image_formats_ipv6_host_header(self):
        class FakeResponse:
            status = 200

            def getheader(self, name):
                return None

            def read(self, size=-1):
                return b''

        class FakeConnection:
            def request(self, method, path, headers):
                self.request_args = (method, path, headers)

            def getresponse(self):
                return FakeResponse()

            def close(self):
                pass

        fake_connection = FakeConnection()
        parsed = REMOTE_FETCH['parse_public_image_url']('http://[2001:4860:4860::8888]:8443/avatar.png')
        with patch.dict(REMOTE_FETCH, {'ValidatedHTTPConnection': lambda *args, **kwargs: fake_connection}):
            status_code, response_body = REMOTE_FETCH['fetch_public_image'](parsed, '2001:4860:4860::8888')

        self.assertEqual(status_code, 200)
        self.assertEqual(response_body, b'')
        self.assertEqual(fake_connection.request_args[2]['Host'], '[2001:4860:4860::8888]:8443')


if __name__ == '__main__':
    unittest.main()
