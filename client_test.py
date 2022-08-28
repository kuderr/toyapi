"""
Origin https://github.com/urllib3/urllib3/issues/52#issuecomment-109756116
"""

from http import client


def pipeline(host, *requests):
    "Pipeline requests (method, path[, body[, headers]]) and generate responses."
    conn = client.HTTPConnection(host)
    responses = []
    for request in requests:
        conn.request(*request)
        responses.append(conn.response_class(conn.sock, method=conn._method))
        conn._HTTPConnection__state = "Idle"
    return (response.begin() or response for response in responses)


def sequential(host, *requests):
    "Send requests (method, path[, body[, headers]]) and generate responses serially."
    conn = client.HTTPConnection(host)
    return (conn.request(*request) or conn.getresponse() for request in requests)


def concurrent(host, *requests):
    "Send requests (method, path[, body[, headers]]) in parallel and generate responses."
    conns = []
    for request in requests:
        conns.append(client.HTTPConnection(host))
        conns[-1].request(*request)
    return (conn.getresponse() for conn in conns)


if __name__ == "__main__":
    import time

    requests = [
        ("GET", "/file.txt"),
        ("GET", "/file.txt"),
    ]
    for func in (
        pipeline,
        sequential,
        concurrent,
    ):
        print(func.__name__)
        responses = func("127.0.0.1:8080", *requests)
        start = time.time()
        for response in responses:
            print(response.status, response.read())
            print(time.time() - start)
