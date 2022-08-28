import os

from toyapi.models import Request, Response


# route handlers
def sum_file(request: Request) -> Response:
    filename = request.target[1:]
    if not os.path.exists(filename):
        return Response(404, "Not Found")

    with open(filename, "r") as file:
        # ugly
        data = str(sum(int(_) for _ in file.read().split()))

    headers = {"Content-Type": "text/plain", "Content-Length": len(data)}
    return Response(200, "OK", body=data, headers=headers)


def index(_: Request) -> Response:
    data = "Hello, World!"
    headers = {"Content-Type": "text/plain", "Content-Length": len(data)}
    return Response(200, "OK", body=data, headers=headers)


# {patterns} and normal paths supported
routes = {
    "GET": {
        "/": index,
        "/{filename}": sum_file,
    }
}
