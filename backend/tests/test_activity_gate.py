"""
tests/test_activity_gate.py
------------------------------
O chat tem prioridade sobre a sincronização: a sincronização espera
enquanto houver conversa, mas nunca "passa fome" (tem teto de espera).
"""

import asyncio
import time

from app.core.activity import ActivityGate


async def test_wait_idle_volta_na_hora_quando_ninguem_conversa():
    gate = ActivityGate(poll_seconds=0.01, max_wait_seconds=5)

    inicio = time.monotonic()
    await gate.wait_idle()

    assert time.monotonic() - inicio < 0.1


async def test_wait_idle_espera_enquanto_ha_chat_e_libera_quando_termina():
    gate = ActivityGate(poll_seconds=0.01, max_wait_seconds=5)
    liberou = asyncio.Event()

    async def conversa():
        async with gate.chat():
            await liberou.wait()

    tarefa = asyncio.create_task(conversa())
    await asyncio.sleep(0.05)
    assert gate.active_chats == 1

    espera = asyncio.create_task(gate.wait_idle())
    await asyncio.sleep(0.1)
    assert not espera.done(), "a sincronização deveria esperar o chat terminar"

    liberou.set()
    await asyncio.wait_for(espera, timeout=1)
    await tarefa
    assert gate.active_chats == 0


async def test_espera_tem_teto_para_nao_passar_fome():
    gate = ActivityGate(poll_seconds=0.01, max_wait_seconds=0.05)

    async with gate.chat():  # chat "eterno"
        inicio = time.monotonic()
        await gate.wait_idle()

    assert time.monotonic() - inicio < 1


async def test_contador_volta_a_zero_mesmo_com_erro_no_chat():
    gate = ActivityGate()

    try:
        async with gate.chat():
            raise RuntimeError("falhou")
    except RuntimeError:
        pass

    assert gate.active_chats == 0
