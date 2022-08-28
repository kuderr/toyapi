import io
from dataclasses import dataclass
from typing import Any


@dataclass
class Request:
    method: str
    target: str
    http_version: str
    headers: dict[str, str]
    rfile: io.BufferedReader

    def body(self) -> bytes | None:
        if not (size := self.headers.get("Content-Length")):
            return None

        # TODO: check size type
        return self.rfile.read(size)  # type: ignore


@dataclass
class Response:
    status: int
    reason: str
    body: str | None = None
    headers: dict[str, Any] | None = None
