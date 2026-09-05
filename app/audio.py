"""Efeitos sonoros. É o mesmo conjunto de .ogg da versão desktop."""

from js import Audio


class Sounds:
    def __init__(self, directory: str = 'assets/sounds', names: tuple[str, ...] = ()):
        self.enabled = True
        self.players = {name: Audio.new(f'{directory}/{name}.ogg') for name in names}

        for player in self.players.values():
            player.preload = 'auto'

    def play(self, name: str):
        player = self.players.get(name)

        if player is None or not self.enabled:
            return self

        player.currentTime = 0

        # O navegador rejeita a reprodução até o primeiro gesto do usuário;
        # nesse caso não há o que fazer além de seguir o jogo.
        promise = player.play()

        if promise is not None:
            promise.catch(lambda _error: None)

        return self
