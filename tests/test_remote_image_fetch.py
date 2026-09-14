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
            with self.assertRaisesRegex(ValueError, 'Only public http\\(s\\) image URLs are allowed'):
                REMOTE_FETCH['download_public_image']('https://example.com/avatar.png')

    def test_download_public_image_rejects_redirects(self):
        with patch.dict(REMOTE_FETCH, {
            'resolve_public_ip': lambda hostname, port: '93.184.216.34',
            'fetch_public_image': lambda parsed, resolved_ip: (302, b''),
        }):
            with self.assertRaisesRegex(ValueError, 'Failed to fetch URL: HTTP 302'):
                REMOTE_FETCH['download_public_image']('https://example.com/avatar.png')

    def test_resolve_public_ip_prefers_global_addresses(self):
        with patch.object(REMOTE_FETCH['socket'], 'getaddrinfo', return_value=[
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.1', 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 443)),
        ]):
            resolved_ip = REMOTE_FETCH['resolve_public_ip']('example.com', 443)

        self.assertEqual(resolved_ip, '93.184.216.34')


if __name__ == '__main__':
    unittest.main()
