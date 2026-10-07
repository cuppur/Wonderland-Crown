"""Explicitly saved EVA settings, encrypted for the current Windows account."""
from __future__ import annotations

import ctypes
import json
import os
import threading
from pathlib import Path
from urllib.parse import urlsplit


def default_settings_file():
    return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'WonderlandCrown' / 'eva-settings.dpapi'


def validate_settings(data):
    if not isinstance(data, dict) or data.get('schemaVersion') != 1:
        raise ValueError('Invalid settings')
    result = {'schemaVersion': 1}
    providers = {'mock', 'openai', 'compatible', 'anthropic', 'gemini', 'deepseek', 'custom'}
    for side in ('player', 'enemy'):
        source = data.get(side)
        if not isinstance(source, dict) or source.get('provider') not in providers:
            raise ValueError('Invalid provider')
        c = {}
        for name in ('provider', 'baseUrl', 'apiKey', 'model', 'reasoning', 'transport', 'reasoningProtocol'):
            value = source.get(name, '')
            if not isinstance(value, str) or len(value) > 4096:
                raise ValueError('Invalid settings field')
            c[name] = value.strip()
        if c['provider'] != 'mock':
            url = urlsplit(c['baseUrl'])
            if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('Invalid API URL')
            if url.scheme == 'http' and url.hostname not in ('localhost', '127.0.0.1', '::1'):
                raise ValueError('Remote API requires HTTPS')
            if not c['model']:
                raise ValueError('Model ID required')
        for name, allowed in [('interval', {2, 3, 5, 10}), ('timeout', {10, 20, 30, 60}), ('maxTokens', {2048, 4096, 8192, 16384, 32768})]:
            if type(source.get(name)) is not int or source[name] not in allowed:
                raise ValueError('Invalid numeric option')
            c[name] = source[name]
        if c['reasoning'] not in {'auto', 'none', 'minimal', 'low', 'medium', 'high', 'max'} or c['transport'] not in {'relay', 'direct'} or c['reasoningProtocol'] not in {'auto', 'none', 'effort'}:
            raise ValueError('Invalid request option')
        c['jsonMode'] = source.get('jsonMode') is True
        result[side] = c
    options = data.get('options', {})
    if not isinstance(options, dict) or options.get('map', 'cross') not in {'cross', 'straight'} or str(options.get('duration', 'unlimited')) not in {'unlimited', '180', '300'}:
        raise ValueError('Invalid match option')
    result['options'] = {'map': options.get('map', 'cross'), 'duration': str(options.get('duration', 'unlimited')), 'fair': options.get('fair', True) is True, 'debug': options.get('debug', False) is True}
    return result


def crypt(data, decrypt=False):
    if os.name != 'nt':
        raise OSError('Windows encrypted storage is unavailable')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source, target = Blob(len(data), buffer), Blob()
    api = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    operation = api.CryptUnprotectData if decrypt else api.CryptProtectData
    operation.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    operation.restype = wintypes.BOOL
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(target)):
        raise OSError('Windows encryption operation failed')
    try:
        return ctypes.string_at(target.data, target.size)
    finally:
        kernel.LocalFree(target.data)


class LocalSettings:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.Lock()

    def load(self):
        with self.lock:
            if not self.path.is_file():
                return None
            return validate_settings(json.loads(crypt(self.path.read_bytes(), decrypt=True)))

    def save(self, data):
        encrypted = crypt(json.dumps(validate_settings(data), ensure_ascii=False).encode('utf-8'))
        with self.lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_bytes(encrypted)
            os.replace(temporary, self.path)

    def clear(self):
        with self.lock:
            self.path.unlink(missing_ok=True)
