import io
import re
import socket
from concurrent.futures import ThreadPoolExecutor

from loguru import logger

from toyapi.models import Request, Response
from toyapi.routes import routes

MAX_REQUEST_LINE = 64 * 1024


def start_server(
    thread_pool_workers: int = 20,
    port: int = 8080,
    socket_backlog: int = 10,
) -> None:
    server_socket = socket.socket(
        family=socket.AF_INET,
        type=socket.SOCK_STREAM,
        proto=0,
    )
    server_socket.bind(("", port))
    server_socket.listen(socket_backlog)

    thread_pool = ThreadPoolExecutor(max_workers=thread_pool_workers)

    logger.info(f"Starting server on http://127.0.0.1:{port}")
    # TODO: gracefull shutdown
    while True:
        client_socket, client_addr = server_socket.accept()
        logger.info(f"Connected by {client_addr}")

        rfile: io.BufferedReader = client_socket.makefile("rb")
        wfile: io.BufferedWriter = client_socket.makefile("wb")
        thread_pool.submit(process_client, conn=client_socket, rfile=rfile, wfile=wfile)


def process_client(
    conn: socket.socket,
    rfile: io.BufferedReader,
    wfile: io.BufferedWriter,
) -> None:
    # TODO: refactor
    try:
        request = parse_request(rfile)
        if request is None:
            wfile.close()
            conn.close()
            return

        logger.debug(request)
        response = handle_request(request)
        logger.debug(response)
        send_response(wfile, response)
    except ConnectionResetError:
        # TODO: process it
        logger.debug("ConnectionReset")
        wfile.close()
        return
    except Exception as err:  # pylint: disable=broad-except
        send_error(wfile, err)
        logger.exception(err)

    # TODO: mypy complain about request is None, refactor this function
    is_close_connection = request.headers.get("Connection", "").lower() == "close"  # type: ignore
    if not is_close_connection:
        process_client(conn, rfile, wfile)

    wfile.close()
    conn.close()


def parse_request(rfile: io.BufferedReader) -> Request | None:
    if not (request_line := parse_request_line(rfile)):
        return None

    method, target, ver = request_line
    headers = parse_headers(rfile)

    return Request(
        method=method,
        target=target,
        http_version=ver,
        headers=headers,
        rfile=rfile,
    )


def parse_request_line(rfile: io.BufferedReader) -> tuple[str, str, str] | None:
    raw = rfile.readline(MAX_REQUEST_LINE + 1)
    if len(raw) > MAX_REQUEST_LINE:
        raise Exception("Request line is too long")

    if len(raw) == 0:
        return None

    req_line = raw.decode("iso-8859-1")
    req_line = req_line.rstrip("\r\n")
    words = req_line.split()
    if len(words) != 3:
        raise Exception("Malformed request line")

    method, target, ver = words
    if ver != "HTTP/1.1":
        raise Exception("Unexpected HTTP version")

    return method, target, ver


def parse_headers(rfile: io.BufferedReader) -> dict[str, str]:
    headers = {}

    while True:
        raw = rfile.readline(MAX_REQUEST_LINE + 1)
        if len(raw) > MAX_REQUEST_LINE:
            raise Exception("Header line is too long")

        if raw in (b"\r\n", b"\n", b""):
            break

        line = raw.decode("iso-8859-1")
        line = line.rstrip("\r\n")

        key, value = line.split(":", 1)
        headers[key] = value.strip()

    return headers


def handle_request(request: Request) -> Response:
    method = request.method
    if method not in routes:
        return Response(405, "Method not allowed")

    for path in routes[method]:
        route_path = re.sub(r"({[\\\w-]+})", r"[\\w-]+", f"^{path}$")
        if re.match(route_path, request.target):
            return routes[request.method][path](request)

    return Response(404, "Not Found")


def send_response(wfile: io.BufferedWriter, response: Response) -> None:
    status_line = f"HTTP/1.1 {response.status} {response.reason}\r\n"
    wfile.write(status_line.encode("iso-8859-1"))

    if response.headers:
        for key, value in response.headers.items():
            header_line = f"{key}: {value}\r\n"
            wfile.write(header_line.encode("iso-8859-1"))

    wfile.write(b"\r\n")

    if response.body:
        wfile.write(response.body.encode("utf-8"))

    wfile.flush()


def send_error(wfile: io.BufferedWriter, err: Exception) -> None:
    return send_response(
        wfile,
        Response(500, "Internal Server Error", body=str(err)),
    )


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        pass
