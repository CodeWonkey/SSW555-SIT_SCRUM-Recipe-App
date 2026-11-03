import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit
import ssl
import urllib3


def resolve_recipe_url(url: str) -> tuple[SplitResult, str]:
    parsed = urlsplit(url)

    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Enter a complete http:// or https:// URL.")

    if parsed.username is not None or parsed.password is not None:
        raise ValueError("URLs containing login credentials are not supported.")

    expected_port = 443 if parsed.scheme == "https" else 80

    if parsed.port not in {None, expected_port}:
        raise ValueError("Only standard website ports are supported.")

    try:
        results = socket.getaddrinfo(
            parsed.hostname,
            expected_port,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ValueError("Could not find that website.") from exc

    addresses = sorted({result[4][0] for result in results})

    if not addresses or any(
        not ipaddress.ip_address(address).is_global
        for address in addresses
    ):
        raise ValueError("Only public website addresses are supported.")

    return parsed, addresses[0]
def fetch_recipe_html(url: str) -> bytes:
    parsed, address = resolve_recipe_url(url)
    hostname = parsed.hostname.encode("idna").decode("ascii")

    if ipaddress.ip_address(address).is_multicast:
        raise ValueError("Only public website addresses are supported.")

    timeout = urllib3.Timeout(connect=5, read=10)

    if parsed.scheme == "https":
        pool = urllib3.HTTPSConnectionPool(
            address,
            port=443,
            server_hostname=hostname,
            assert_hostname=hostname,
            ssl_context=ssl.create_default_context(),
            timeout=timeout,
        )
    else:
        pool = urllib3.HTTPConnectionPool(
            address,
            port=80,
            timeout=timeout,
        )

    target = parsed.path or "/"
    if parsed.query:
        target += "?" + parsed.query

    try:
        with pool:
            response = pool.urlopen(
                "GET",
                target,
                headers={
                    "Host": hostname,
                    "User-Agent": "RecipeJournal/0.1",
                    "Accept": "text/html, application/xhtml+xml",
                    "Accept-Encoding": "identity",
                },
                redirect=False,
                retries=False,
                preload_content=False,
                assert_same_host=False,
            )

            try:
                if 300 <= response.status < 400:
                    raise ValueError(
                        "This URL redirects. Use the final URL from your browser."
                    )

                if response.status != 200:
                    raise ValueError(
                        f"The website returned HTTP {response.status}."
                    )

                content_type = response.headers.get(
                    "Content-Type", ""
                ).split(";")[0].strip().lower()

                if content_type not in {"text/html", "application/xhtml+xml"}:
                    raise ValueError("This URL does not contain an HTML page.")

                encoding = response.headers.get(
                    "Content-Encoding", "identity"
                ).strip().lower()

                if encoding not in {"", "identity"}:
                    raise ValueError("Compressed responses are not supported yet.")

                html = response.read(2_000_001, decode_content=False)

                if len(html) > 2_000_000:
                    raise ValueError("This page is too large to import.")

                return html
            finally:
                response.close()

    except (urllib3.exceptions.HTTPError, OSError) as exc:
        raise ValueError(
            "Could not download the page. Check the URL and try again."
        ) from exc