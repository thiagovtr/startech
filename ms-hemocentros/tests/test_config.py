import pytest
from hemocentros.config import get_settings


def test_sem_credenciais_o_servico_nao_sobe_e_o_erro_nomeia_as_variaveis(monkeypatch):
    monkeypatch.delenv("HEMOCENTROS_POSTGRES_URL")
    monkeypatch.delenv("HEMOCENTROS_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    msg = str(e.value)
    assert "HEMOCENTROS_POSTGRES_URL" in msg and "HEMOCENTROS_RABBITMQ_URL" in msg
    assert "guest" not in msg and "hemocentros:hemocentros" not in msg  # nenhuma senha vaza na mensagem


def test_so_uma_variavel_ausente_e_nomeada(monkeypatch):
    monkeypatch.delenv("HEMOCENTROS_RABBITMQ_URL")
    get_settings.cache_clear()
    try:
        with pytest.raises(RuntimeError) as e:
            get_settings()
    finally:
        get_settings.cache_clear()
    assert "HEMOCENTROS_RABBITMQ_URL" in str(e.value) and "HEMOCENTROS_POSTGRES_URL" not in str(e.value)


def test_nao_ha_credencial_padrao_no_codigo():
    import pathlib, re

    fonte = pathlib.Path(__file__).parents[1] / "src"
    achados = [
        str(p) for p in fonte.rglob("*.py")
        if re.search(r"guest:guest|hemocentros:hemocentros|://\w+:\w+@", p.read_text())
    ]
    assert achados == []
