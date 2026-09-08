"""HTTPS client with a known missing issuer for taphuan.nxbgd.vn."""

from pathlib import Path
import ssl

import certifi
import requests
from requests.adapters import HTTPAdapter


REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
MISSING_INTERMEDIATE = (
    Path(__file__).parent
    / "certs"
    / "sectigo-public-server-authentication-ca-dv-r36.pem"
)


class VerifiedHTTPSAdapter(HTTPAdapter):
    """Adapter that preserves normal TLS checks with an added intermediate."""

    def __init__(self, ssl_context, *args, **kwargs):
        self._ssl_context = ssl_context
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["ssl_context"] = self._ssl_context
        return super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        proxy_kwargs["ssl_context"] = self._ssl_context
        return super().proxy_manager_for(proxy, **proxy_kwargs)


def create_session():
    """Create a session that can validate the site's incomplete TLS chain."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.load_verify_locations(cafile=MISSING_INTERMEDIATE)

    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)
    session.mount("https://", VerifiedHTTPSAdapter(context))
    return session


HTTP_SESSION = create_session()


def fetch_url(url, timeout=30):
    """Fetch a resource while retaining certificate and hostname validation."""
    return HTTP_SESSION.get(url, timeout=timeout)
