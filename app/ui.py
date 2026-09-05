"""Painel lateral: status, avaliação, histórico e controles."""

from js import document
from pyodide.ffi import create_proxy


status_tag = document.getElementById('status-tag')
evaluation_value = document.getElementById('evaluation-value')
evaluation_bar = document.getElementById('evaluation-bar')
evaluation_detail = document.getElementById('evaluation-detail')
history_body = document.getElementById('history')
restart_button = document.getElementById('restart')
level_select = document.getElementById('level')
sound_button = document.getElementById('sound')
overlay = document.getElementById('overlay')


LEVELS = {
    # força do engine, de 0 a 20, e tempo de reflexão em ms
    '1': (0, 100),
    '2': (5, 200),
    '3': (10, 400),
    '4': (15, 800),
    '5': (20, 1500),
}


def movetime() -> int:
    return LEVELS[level_select.value][1]


def bind(app):
    "Liga os controles do painel à instância do jogo."

    restart_button.addEventListener('click', create_proxy(lambda _event: app.restart()))
    level_select.addEventListener('change', create_proxy(lambda _event: _on_level(app)))
    sound_button.addEventListener('click', create_proxy(lambda _event: _on_sound(app)))

    _on_level(app)


def _on_level(app):
    app.engine.set_skill(LEVELS[level_select.value][0])


def _on_sound(app):
    app.sounds.enabled = not app.sounds.enabled

    sound_button.textContent = 'Som' if app.sounds.enabled else 'Som desligado'


def set_ready():
    overlay.classList.add('is-hidden')
    document.body.dataset.ready = '1'


def set_status(text: str, busy: bool = False):
    status_tag.textContent = text
    status_tag.className = f'tag is-medium {"is-warning" if busy else "is-success"}'


def set_evaluation(info):
    "Mostra a avaliação sempre do ponto de vista das brancas (o jogador)."

    if info is None:
        evaluation_value.textContent = '0.00'
        evaluation_detail.textContent = ''
        evaluation_bar.value = 50

        return

    # O engine reporta do ponto de vista de quem joga, e quem pensa é o preto.
    if info.mate is not None:
        mate = -info.mate
        evaluation_value.textContent = f'M{abs(mate)}'
        evaluation_bar.value = 100 if mate > 0 else 0
    else:
        score = -(info.score or 0) / 100
        evaluation_value.textContent = f'{score:+.2f}'

        # Uma sigmoide simples mantém a barra legível em vantagens grandes.
        evaluation_bar.value = round(50 + 50 * (score / (abs(score) + 3)))

    evaluation_detail.textContent = f'profundidade {info.depth}, {info.nodes / 1000:.0f}k nós'


def set_history(history: list[str]):
    history_body.replaceChildren()

    for index in range(0, len(history), 2):
        row = document.createElement('tr')

        for text in (f'{index // 2 + 1}.',
                     history[index],
                     history[index + 1] if index + 1 < len(history) else ''):
            cell = document.createElement('td')
            cell.textContent = text
            row.append(cell)

        history_body.append(row)

    history_body.parentElement.parentElement.scrollTop = 10 ** 6
