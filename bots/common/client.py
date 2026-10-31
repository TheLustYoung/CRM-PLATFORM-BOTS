import httpx
from backend.config import settings


class ApiError(Exception):
    """Error code from the backend (a locale key such as 'rate_limit' or 'invalid_url')."""


class ApiClient:
    """Bots hold no business logic: every decision is made by the central backend."""

    def __init__(self, kind: str):
        cfg = settings()
        self.client = httpx.AsyncClient(base_url=cfg.api_internal_url, timeout=20,
                                        headers={"X-Bot-Kind": kind, "X-Service-Key": cfg.service_key(kind)})

    async def post(self, route: str, data: dict) -> dict | list:
        response = await self.client.post("/internal/" + route, json=data)
        if response.is_error:
            try:
                detail = response.json().get("detail", "failed")
            except ValueError:
                detail = "failed"
            raise ApiError(detail if isinstance(detail, str) else "failed")
        return response.json()

    async def close(self):
        await self.client.aclose()
