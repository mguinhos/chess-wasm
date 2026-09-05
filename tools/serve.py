#!/usr/bin/env python3
"""
Servidor estático para desenvolvimento.

O site é só arquivos. Mesmo assim o navegador exige HTTP para carregar o
worker e o .wasm. Abrir o index.html direto do disco não funciona.

    $ python tools/serve.py
"""

import argparse
import functools
import http.server
import pathlib
import socketserver

ROOT = pathlib.Path(__file__).resolve().parent.parent


class Server(socketserver.ThreadingTCPServer):
    # Sem isso a porta fica presa em TIME_WAIT entre uma execução e outra.
    allow_reuse_address = True
    daemon_threads = True


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        '.wasm': 'application/wasm',
        '.data': 'application/octet-stream',
        '.ogg': 'audio/ogg',
        '.toml': 'text/plain',
    }

    def end_headers(self):
        # Sem cache: em desenvolvimento o .wasm e os .py mudam a cada build.
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        if '404' in fmt % args:
            super().log_message(fmt, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()

    handler = functools.partial(Handler, directory=str(ROOT))

    with Server(('', args.port), handler) as server:
        print(f'servindo {ROOT} em http://localhost:{args.port}/')
        server.serve_forever()


if __name__ == '__main__':
    main()
