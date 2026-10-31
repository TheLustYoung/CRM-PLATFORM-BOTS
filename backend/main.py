"""Central FastAPI backend shared by all Telegram bots and the admin dashboard."""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from backend.api import routers
from backend.config import settings
from backend.services.security import DomainError

logging.basicConfig(level=logging.INFO, format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":%(message)r}')

app = FastAPI(title="Telegram Media Platform", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(CORSMiddleware, allow_origins=[settings().admin_origin], allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Content-Type"])
for router in routers:
    app.include_router(router)

from backend.services import i18n, translations  # noqa: E402
from backend import observability  # noqa: E402
i18n.use_loader(translations.loader)  # texts and languages edited in the dashboard
observability.setup("api")  # error tracking when SENTRY_DSN is set

STATUS = {"rate_limit": 429, "premium_limit": 429, "not_found": 404, "banned": 403, "disabled": 403,
          "premium_quality": 402, "premium_size": 402, "premium_feature": 402, "storage_quota": 402}


@app.exception_handler(DomainError)
async def domain_error(_request, error):
    code = str(error)
    return JSONResponse({"detail": code}, status_code=STATUS.get(code, 400))
