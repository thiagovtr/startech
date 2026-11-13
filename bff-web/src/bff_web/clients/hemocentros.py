import httpx
from fastapi import Request


class ServicoIndisponivel(Exception):
    """Falha de comunicação com um serviço interno."""

    def __init__(self, servico: str, timeout: bool):
        self.servico, self.timeout = servico, timeout


class RespostaDoServico(Exception):
    """O serviço interno respondeu com erro (4xx/5xx)."""

    def __init__(self, servico: str, response: httpx.Response):
        self.servico, self.response = servico, response


class HemocentrosClient:
    def __init__(self, http: httpx.AsyncClient):
        self._http = http

    async def _request(self, method: str, path: str, user_id: str | None, **kwargs) -> httpx.Response:
        headers = {"X-User-Id": user_id} if user_id else {}
        try:
            response = await self._http.request(method, path, headers=headers, **kwargs)
        except httpx.TimeoutException:
            raise ServicoIndisponivel("ms-hemocentros", timeout=True)
        except httpx.TransportError:
            raise ServicoIndisponivel("ms-hemocentros", timeout=False)
        if response.status_code >= 400:
            raise RespostaDoServico("ms-hemocentros", response)
        return response

    async def criar_campanha(self, dados: dict, user_id: str | None) -> dict:
        return (await self._request("POST", "/api/v1/campanhas", user_id, json=dados)).json()

    async def listar_campanhas(
        self, tipo_sanguineo: str | None, user_id: str | None, **filtros: str | int | bool | None
    ) -> tuple[list[dict], str | None]:
        """Devolve (campanhas, X-Total-Count). `filtros`: status, vigentes, limit, offset."""
        params = {k: v for k, v in {"tipo_sanguineo": tipo_sanguineo, **filtros}.items() if v is not None}
        if isinstance(params.get("vigentes"), bool):
            params["vigentes"] = str(params["vigentes"]).lower()
        r = await self._request("GET", "/api/v1/campanhas", user_id, params=params or None)
        return r.json(), r.headers.get("X-Total-Count")


def get_hemocentros_client(request: Request) -> HemocentrosClient:
    return request.app.state.hemocentros_client
