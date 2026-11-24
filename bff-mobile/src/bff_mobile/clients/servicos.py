import httpx


class ServicoIndisponivel(Exception):
    """Falha ao consultar um serviço interno (rede, timeout ou resposta de erro)."""

    def __init__(self, servico: str, motivo: str):
        super().__init__(f"{servico}: {motivo}")
        self.servico, self.motivo = servico, motivo


async def _get(http: httpx.AsyncClient, servico: str, path: str, user_id: str, **params) -> httpx.Response:
    try:
        response = await http.get(path, headers={"X-User-Id": user_id}, params=params or None)
    except httpx.TimeoutException as exc:
        raise ServicoIndisponivel(servico, "timeout") from exc
    except httpx.TransportError as exc:
        raise ServicoIndisponivel(servico, "indisponível") from exc
    if response.status_code >= 400:
        raise ServicoIndisponivel(servico, f"HTTP {response.status_code}")
    return response


class DoadoresClient:
    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def obter(self, doador_id: str) -> dict | None:
        """Perfil do doador; None se ele não estiver cadastrado (404, contratos §2).

        404 é resposta de negócio do ms-doadores, não indisponibilidade: o serviço está no ar.
        """
        try:
            r = await self._http.get(f"/api/v1/doadores/{doador_id}", headers={"X-User-Id": doador_id})
        except httpx.TimeoutException as exc:
            raise ServicoIndisponivel("ms-doadores", "timeout") from exc
        except httpx.TransportError as exc:
            raise ServicoIndisponivel("ms-doadores", "indisponível") from exc
        if r.status_code == 404:
            return None
        if r.status_code >= 400:
            raise ServicoIndisponivel("ms-doadores", f"HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as exc:
            raise ServicoIndisponivel("ms-doadores", "resposta inválida") from exc

    async def salvar(self, doador_id: str, dados: dict) -> tuple[int, dict]:
        """Cadastra ou atualiza o perfil do doador no ms-doadores (PUT /api/v1/doadores/{id})."""
        return await _chamar(
            self._http, "ms-doadores", "PUT", f"/api/v1/doadores/{doador_id}",
            headers={"X-User-Id": doador_id}, json=dados,
        )


class HemocentrosClient:
    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def listar_campanhas(self, user_id: str, tipo_sanguineo: str | None) -> list[dict]:
        # o app só exibe campanhas que ainda não terminaram
        params = {"vigentes": "true"}
        if tipo_sanguineo:
            params["tipo_sanguineo"] = tipo_sanguineo
        r = await _get(self._http, "ms-hemocentros", "/api/v1/campanhas", user_id, **params)
        try:
            return r.json()
        except ValueError as exc:
            raise ServicoIndisponivel("ms-hemocentros", "resposta inválida") from exc


async def _chamar(http: httpx.AsyncClient, servico: str, metodo: str, caminho: str, **kwargs) -> tuple[int, dict]:
    """Chamada cujas respostas de negócio (2xx/4xx) voltam como (status, corpo) para o BFF repassar.

    Falha de rede, timeout, 5xx ou corpo que não é objeto JSON levantam `ServicoIndisponivel`.
    """
    try:
        r = await http.request(metodo, caminho, **kwargs)
    except httpx.TimeoutException as exc:
        raise ServicoIndisponivel(servico, "timeout") from exc
    except httpx.TransportError as exc:
        raise ServicoIndisponivel(servico, "indisponível") from exc
    if r.status_code >= 500:
        raise ServicoIndisponivel(servico, f"HTTP {r.status_code}")
    try:
        corpo = r.json()
    except ValueError as exc:
        raise ServicoIndisponivel(servico, "resposta inválida") from exc
    if not isinstance(corpo, dict):
        raise ServicoIndisponivel(servico, "resposta inválida")
    return r.status_code, corpo


class OrquestradorClient:
    """ms-orquestrador: início e consulta da SAGA de agendamento (contratos §2, "5. orquestrador").

    Respostas de negócio (202, 200, 404, 409, 422) voltam como (status, corpo) para o BFF repassar;
    falha de rede, timeout ou 5xx levantam `ServicoIndisponivel`.
    """

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def iniciar_agendamento(self, doador_id: str, slot_id: str, idempotency_key: str | None) -> tuple[int, dict]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        return await _chamar(
            self._http, "ms-orquestrador", "POST", "/api/v1/sagas/agendamento",
            json={"doadorId": doador_id, "slotId": slot_id}, headers=headers,
        )

    async def consultar(self, saga_id: str) -> tuple[int, dict]:
        return await _chamar(self._http, "ms-orquestrador", "GET", f"/api/v1/sagas/{saga_id}")


class AgendamentosClient:
    """ms-agendamentos: recurso Agendamento com HATEOAS (contratos §2 e §3).

    Respostas de negócio (200, 400, 404, 409) voltam como (status, corpo); falha técnica levanta
    `ServicoIndisponivel`.
    """

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def listar_slots(self, params: dict[str, str]) -> tuple[int, dict]:
        return await _chamar(self._http, "ms-agendamentos", "GET", "/api/v1/slots", params=params)

    async def listar(self, doador_id: str) -> tuple[int, dict]:
        return await _chamar(self._http, "ms-agendamentos", "GET", "/api/v1/agendamentos",
                             params={"doadorId": doador_id})

    async def consultar(self, agendamento_id: str) -> tuple[int, dict]:
        return await _chamar(self._http, "ms-agendamentos", "GET", f"/api/v1/agendamentos/{agendamento_id}")

    async def cancelar(self, agendamento_id: str, motivo: str | None) -> tuple[int, dict]:
        corpo = {"motivo": motivo} if motivo else {}
        return await _chamar(self._http, "ms-agendamentos", "POST",
                             f"/api/v1/agendamentos/{agendamento_id}/cancelamento", json=corpo)


class RagClient:
    """ms-rag: assistente do doador. Erro de rede/timeout/5xx levanta `ServicoIndisponivel`."""

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def perguntar(self, pergunta: str, tipo_sanguineo: str | None) -> dict:
        corpo: dict = {"pergunta": pergunta, "usarRag": True}
        if tipo_sanguineo:
            corpo["tipoSanguineo"] = tipo_sanguineo
        try:
            r = await self._http.post("/api/v1/rag/perguntas", json=corpo)
        except httpx.TimeoutException as exc:
            raise ServicoIndisponivel("ms-rag", "timeout") from exc
        except httpx.TransportError as exc:
            raise ServicoIndisponivel("ms-rag", "indisponível") from exc
        if r.status_code >= 400:
            raise ServicoIndisponivel("ms-rag", f"HTTP {r.status_code}")
        try:
            return r.json()
        except ValueError as exc:
            raise ServicoIndisponivel("ms-rag", "resposta inválida") from exc
