import pytest

from orquestrador.config import get_settings


def test_sem_credenciais_o_servico_nao_sobe_e_o_erro_nomeia_as_variaveis(monkeypatch):
    monkeypatch.delenv("ORQUESTRADOR_POSTGRES_URL")
    monkeypatch.delenv("ORQUESTRADOR_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    msg = str(e.value)
    assert "ORQUESTRADOR_POSTGRES_URL" in msg and "ORQUESTRADOR_RABBITMQ_URL" in msg
    assert "guest" not in msg and "teste:teste" not in msg  # nenhuma senha vaza na mensagem


def test_so_uma_variavel_ausente_e_nomeada(monkeypatch):
    monkeypatch.delenv("ORQUESTRADOR_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    assert "ORQUESTRADOR_RABBITMQ_URL" in str(e.value) and "ORQUESTRADOR_POSTGRES_URL" not in str(e.value)


def test_padroes_da_saga():
    s = get_settings()
    assert (s.max_retries, s.backoff_base_ms) == (5, 500)  # ADR-002 §5.3
    assert s.passo3_aguardar_resposta is True and s.timeout_passo3 == 30.0  # contratos §2.1
    assert s.agendamentos_url == "http://ms-agendamentos:8082" and s.doadores_url == "http://ms-doadores:8081"


def test_nao_ha_credencial_padrao_no_codigo():
    import pathlib
    import re

    fonte = pathlib.Path(__file__).parents[1] / "src"
    achados = [
        str(p) for p in fonte.rglob("*.py")
        if re.search(r"guest:guest|orquestrador:orquestrador|://\w+:\w+@", p.read_text())
    ]
    assert achados == []
