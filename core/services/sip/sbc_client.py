from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from shared.config import settings

HTTP_TIMEOUT = 15


class SbcError(RuntimeError):
    pass


class SbcClient:
    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self._base_url = (base_url or settings.SIP_SBC_CONTROL_URL or "").rstrip("/")
        self._api_key = api_key or settings.SIP_SBC_API_KEY or ""

    @property
    def configured(self) -> bool:
        return bool(self._base_url)

    def _require_configured(self) -> None:
        if not self.configured:
            raise SbcError(
                "SIP_SBC_CONTROL_URL is not set — the SBC control API address is needed "
                "to provision trunks and place SIP calls."
            )

    def _request(
        self, method: str, path: str, payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        self._require_configured()
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        try:
            response = requests.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=payload,
                timeout=HTTP_TIMEOUT,
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.HTTPError:
            logger.exception("[sip] sbc {} {} failed", method, path)
            raise SbcError(self._error_detail(response))
        except requests.RequestException as exc:
            logger.exception("[sip] sbc {} {} unreachable", method, path)
            raise SbcError(f"SBC control API is unreachable: {exc}")

    @staticmethod
    def _error_detail(response) -> str:
        try:
            body = response.json()
        except ValueError:
            body = {}
        return body.get("detail") or f"SBC control API error (HTTP {response.status_code})"

    def sync_trunk(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("PUT", f"/trunks/{payload['trunk_id']}", payload)

    def remove_trunk(self, trunk_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/trunks/{trunk_id}")

    def originate(
        self,
        trunk_id: str,
        from_number: str,
        to_uris: List[str],
        media_ws_url: str,
        params: Dict[str, Any],
        media_encryption: str = "none",
        diversion_header: Optional[str] = None,
        timeout_seconds: int = 45,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "trunk_id": trunk_id,
            "from": from_number,
            "to": to_uris,
            "media_ws_url": media_ws_url,
            "params": params,
            "media_encryption": media_encryption,
            "timeout_seconds": timeout_seconds,
        }
        if diversion_header:
            payload["diversion"] = diversion_header
        return self._request("POST", "/calls", payload)

    def hangup(self, call_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/calls/{call_id}")

    def call_status(self, call_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/calls/{call_id}")

    def refer(
        self, call_id: str, sip_address: str, headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"sip_address": sip_address}
        if headers:
            payload["custom_headers"] = headers
        return self._request("POST", f"/calls/{call_id}/refer", payload)
