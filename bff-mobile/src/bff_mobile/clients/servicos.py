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

    async def obter(self, doador_id: str) -> dict:
        r = await _get(self._http, "ms-doadores", f"/api/v1/doadores/{doador_id}", doador_id)
        try:
            return r.json()
        except ValueError as exc:
            raise ServicoIndisponivel("ms-doadores", "resposta inválida") from exc


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


class OrquestradorClient:
    """ms-orquestrador: início e consulta da SAGA de agendamento (contratos §2, "5. orquestrador").

    Respostas de negócio (202, 200, 404, 409, 422) voltam como (status, corpo) para o BFF repassar;
    falha de rede, timeout ou 5xx levantam `ServicoIndisponivel`.
    """

    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def _chamar(self, metodo: str, caminho: str, **kwargs) -> tuple[int, dict]:
        try:
            r = await self._http.request(metodo, caminho, **kwargs)
        except httpx.TimeoutException as exc:
            raise ServicoIndisponivel("ms-orquestrador", "timeout") from exc
        except httpx.TransportError as exc:
            raise ServicoIndisponivel("ms-orquestrador", "indisponível") from exc
        if r.status_code >= 500:
            raise ServicoIndisponivel("ms-orquestrador", f"HTTP {r.status_code}")
        try:
            corpo = r.json()
        except ValueError as exc:
            raise ServicoIndisponivel("ms-orquestrador", "resposta inválida") from exc
        if not isinstance(corpo, dict):
            raise ServicoIndisponivel("ms-orquestrador", "resposta inválida")
        return r.status_code, corpo

    async def iniciar_agendamento(self, doador_id: str, slot_id: str, idempotency_key: str | None) -> tuple[int, dict]:
        headers = {"Idempotency-Key": idempotency_key} if idempotency_key else {}
        return await self._chamar(
            "POST", "/api/v1/sagas/agendamento", json={"doadorId": doador_id, "slotId": slot_id}, headers=headers
        )

    async def consultar(self, saga_id: str) -> tuple[int, dict]:
        return await self._chamar("GET", f"/api/v1/sagas/{saga_id}")
