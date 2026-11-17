import pytest

from comunicacao.config import get_settings


def test_sem_credenciais_o_servico_nao_sobe_e_o_erro_nomeia_as_variaveis(monkeypatch):
    monkeypatch.delenv("COMUNICACAO_POSTGRES_URL")
    monkeypatch.delenv("COMUNICACAO_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    msg = str(e.value)
    assert "COMUNICACAO_POSTGRES_URL" in msg and "COMUNICACAO_RABBITMQ_URL" in msg
    assert "guest" not in msg and "teste:teste" not in msg  # nenhuma senha vaza na mensagem


def test_so_uma_variavel_ausente_e_nomeada(monkeypatch):
    monkeypatch.delenv("COMUNICACAO_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    assert "COMUNICACAO_RABBITMQ_URL" in str(e.value) and "COMUNICACAO_POSTGRES_URL" not in str(e.value)


def test_padroes_do_contrato():
    s = get_settings()
    assert s.port == 8004
    assert s.fila_comandos == "comunicacao.saga.comandos" and s.binding_comandos == "saga.comando.comunicacao.*"
    assert s.routing_key_programado == "comunicacao.lembrete.programado"
    assert s.routing_key_falhou == "comunicacao.lembrete.falhou"
    assert s.lembrete_antecedencia.days == 1 and s.doadores_com_falha_simulada == set()


def test_listas_separadas_por_virgula(monkeypatch):
    monkeypatch.setenv("COMUNICACAO_SIMULAR_FALHA_DOADORES", " d1, d2 ,,")
    monkeypatch.setenv("COMUNICACAO_LEMBRETE_ANTECEDENCIA", "PT10S")
    get_settings.cache_clear()
    try:
        s = get_settings()
    finally:
        get_settings.cache_clear()
    assert s.doadores_com_falha_simulada == {"d1", "d2"}
    assert s.lembrete_antecedencia.total_seconds() == 10


def test_nao_ha_credencial_padrao_no_codigo():
    import pathlib
    import re

    fonte = pathlib.Path(__file__).parents[1] / "src"
    achados = [
        str(p) for p in fonte.rglob("*.py")
        if re.search(r"guest:guest|comunicacao:comunicacao|://\w+:\w+@", p.read_text())
    ]
    assert achados == []
