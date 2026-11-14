"""
core/activity.py
------------------
Dá prioridade ao CHAT sobre a SINCRONIZAÇÃO em segundo plano.

Problema: o Ollama roda em uma única máquina (muitas vezes um PC básico) e
atende duas coisas ao mesmo tempo — gerar a resposta do chat e gerar os
embeddings da sincronização. Se as duas competirem, quem está perguntando
sente lentidão. Solução: a sincronização consulta este "porteiro" antes de
cada arquivo/trecho e espera enquanto houver alguém conversando.

Funciona porque a aplicação é single-thread assíncrona (asyncio): somar e
subtrair o contador não precisa de lock.

Para não "passar fome" caso sempre haja alguém conversando, a espera tem um
teto (`max_wait_seconds`): depois dele, a sincronização segue mesmo assim.
"""

import asyncio
from contextlib import asynccontextmanager


class ActivityGate:
    def __init__(self, poll_seconds: float = 0.5, max_wait_seconds: float = 300.0):
        self._active_chats = 0
        self._poll_seconds = poll_seconds
        self._max_wait_seconds = max_wait_seconds

    @property
    def active_chats(self) -> int:
        return self._active_chats

    @asynccontextmanager
    async def chat(self):
        """Use em volta do tratamento de uma pergunta: `async with gate.chat(): ...`"""
        self._active_chats += 1
        try:
            yield
        finally:
            self._active_chats -= 1

    async def wait_idle(self) -> None:
        """Espera até não haver chat em andamento (ou até o teto de espera)."""
        waited = 0.0
        while self._active_chats > 0 and waited < self._max_wait_seconds:
            await asyncio.sleep(self._poll_seconds)
            waited += self._poll_seconds
