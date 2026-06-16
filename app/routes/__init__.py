"""Route contract registry for the current stdlib River FIS server.

`app.server` owns live HTTP dispatch in this pass. This registry makes the route
modules machine-readable so tests/tools can verify that documented contracts map to
callable server endpoints during the future framework split.
"""
from __future__ import annotations

from app.routes.action_routes import ENDPOINTS as ACTION_ENDPOINTS
from app.routes.folderbrain_routes import ENDPOINTS as FOLDERBRAIN_ENDPOINTS
from app.routes.intelligence_routes import ENDPOINTS as INTELLIGENCE_ENDPOINTS
from app.routes.preference_routes import ENDPOINTS as PREFERENCE_ENDPOINTS
from app.routes.rename_routes import ENDPOINTS as RENAME_ENDPOINTS
from app.routes.review_routes import ENDPOINTS as REVIEW_ENDPOINTS
from app.routes.scan_routes import ENDPOINTS as SCAN_ENDPOINTS

ROUTE_CONTRACTS = {
    **ACTION_ENDPOINTS,
    **FOLDERBRAIN_ENDPOINTS,
    **INTELLIGENCE_ENDPOINTS,
    **PREFERENCE_ENDPOINTS,
    **RENAME_ENDPOINTS,
    **REVIEW_ENDPOINTS,
    **SCAN_ENDPOINTS,
}

def is_declared_route(method: str, path: str) -> bool:
    return f"{method.upper()} {path}" in ROUTE_CONTRACTS
