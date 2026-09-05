#!/usr/bin/env python3
"""
Teste end-to-end: sobe o site, joga alguns lances e confere que o Stockfish
responde de dentro do navegador.

    $ pip install playwright && playwright install chromium
    $ python tests/test_browser.py [--headed] [--screenshot arquivo.png]
"""

import argparse
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
PORT = 8177
URL = f'http://localhost:{PORT}/'
FILES = 'abcdefgh'


def serve():
    "Sobe o servidor estático e espera ele atender."

    process = subprocess.Popen(
        [sys.executable, str(ROOT / 'tools' / 'serve.py'), '--port', str(PORT)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    for _ in range(100):
        try:
            urllib.request.urlopen(URL, timeout=0.5)
            return process
        except (urllib.error.URLError, ConnectionError):
            time.sleep(0.1)

    process.terminate()
    raise RuntimeError('o servidor não respondeu')


def wait_for_board(page):
    "Espera o tabuleiro parar de deslizar, para os cliques caírem na casa certa."

    previous = None

    for _ in range(60):
        box = page.locator('#board').bounding_box()
        current = (box['x'], box['width'])

        if current == previous:
            return

        previous = current
        page.wait_for_timeout(100)


def click_square(page, name: str):
    "Clica no centro da casa. Por exemplo e2."

    box = page.locator('#board').bounding_box()

    x = box['x'] + box['width'] * (FILES.index(name[0]) + 0.5) / 8
    y = box['y'] + box['height'] * (8 - int(name[1]) + 0.5) / 8

    page.mouse.move(x, y)
    page.wait_for_timeout(60)
    page.mouse.click(x, y)


PLIES = ('Array.from(document.querySelectorAll("#history td:not(:first-child)"))'
         '.filter(node => node.textContent).length')


def move(page, origin: str, destination: str):
    "Faz um lance das brancas e espera a resposta do engine."

    played = page.evaluate(PLIES)

    click_square(page, origin)
    click_square(page, destination)

    # O lance do jogador mais a resposta do engine.
    page.wait_for_function(f'{PLIES} >= {played + 2}', timeout=30000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headed', action='store_true')
    parser.add_argument('--screenshot')
    args = parser.parse_args()

    server = serve()
    failures = []

    def check(label, condition, detail=''):
        print(('  ok  ' if condition else ' FALHA') + f'  {label}' + (f': {detail}' if detail else ''))

        if not condition:
            failures.append(label)

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={'width': 1280, 'height': 1000})

            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)

            page.goto(URL, wait_until='load')
            page.wait_for_function('document.body.dataset.ready === "1"', timeout=120000)
            wait_for_board(page)

            check('a página carrega Python e o engine', True)
            check('o status indica a vez do jogador',
                  page.text_content('#status-tag') == 'Sua vez',
                  page.text_content('#status-tag'))

            for origin, destination in (('e2', 'e4'), ('g1', 'f3'), ('f1', 'c4'), ('b1', 'c3')):
                move(page, origin, destination)

            history = page.eval_on_selector_all(
                '#history td:not(:first-child)', 'nodes => nodes.map(node => node.textContent)')

            check('quatro lances de cada lado no histórico', len(history) == 8, str(history))
            check('as brancas jogaram o que foi clicado',
                  history[0::2] == ['e2e4', 'g1f3', 'f1c4', 'b1c3'], str(history[0::2]))
            check('o engine respondeu a todos', all(history[1::2]), str(history[1::2]))

            check('a avaliação foi atualizada',
                  page.text_content('#evaluation-value') != '0.00',
                  page.text_content('#evaluation-value'))

            if args.screenshot:
                page.screenshot(path=args.screenshot)

            page.click('#restart')
            page.wait_for_timeout(300)

            check('nova partida limpa o histórico', page.locator('#history tr').count() == 0)
            check('sem erros no console', not errors, '; '.join(errors[:3]))

            browser.close()
    finally:
        server.terminate()

    print()

    if failures:
        print(f'{len(failures)} verificação(ões) falharam')
        return 1

    print('tudo certo')
    return 0


if __name__ == '__main__':
    sys.exit(main())
