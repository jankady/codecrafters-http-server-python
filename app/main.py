"""
Simple HTTP/1.1 server

This module implements a tiny HTTP server intended for educational use and for
the codecrafters exercise. It supports:
- Basic GET and POST handling
- Persistent TCP connections (reads multiple requests per connection)
- Simple echo behaviour and basic file serving/creation inside a host directory

Notes:
- This is not a production-ready HTTP server. There are many simplifications:
  * limited header parsing
  * no chunked transfer decoding
  * naive Content-Length handling
  * minimal security checks on paths
"""

import argparse
import socket  # noqa: F401 - socket is used by server setup in main()
import os
import gzip
import threading


def check_file_exists(path_to_file, directory):
    """
    Return True if a file (basename of `path_to_file`) exists in `directory`.

    Args:
        path_to_file (str): full or partial path; only basename is considered.
        directory (str): directory to look into.

    Returns:
        bool: True when the file exists, False otherwise.
    """
    get_file = os.path.basename(path_to_file)

    try:
        # Directly return the membership check; if listing fails, return False.
        return get_file in os.listdir(directory)
    except Exception:

        return False


def check_directory_exists(directory):
    """
    Check whether `directory` exists and is a directory.

    Args:
        directory (str): path to check.

    Returns:
        bool: True if directory exists and is a directory.
    """
    try:
        # Return the boolean directly; exceptions -> False.
        return os.path.exists(directory) and os.path.isdir(directory)

    except Exception:
        return False

def create_file(path_to_file, directory, content_type, content_length, content_body):
    """
    Create a file inside `directory` using the basename of `path_to_file`.

    Args:
        path_to_file (str): requested path (only basename is used to create a file).
        directory (str): directory where the file will be created.
        content_type (str): unused
        content_length (int): unused
        content_body (str): content to write into the file.

    Returns:
        bool: True on success, False on error.
    """
    get_file = os.path.basename(path_to_file)
    target_file = os.path.join(directory, get_file)

    try:
        # Write as text – this mirrors the original behaviour.
        with open(target_file, 'w') as file:
            file.write(content_body)
        return True
    except Exception:

        return False


def validate_encoding(encoding_type):
    """
    Filter a list of Accept-Encoding values and keep supported encodings.

    Supported encodings in this server are: 'gzip', 'deflate', 'br'.

    Args:
        encoding_type (list[str]): list of encodings taken from request header.

    Returns:
        list[str]: filtered list containing only supported encodings.
    """
    result = []
    for encoding in encoding_type:
        if encoding in ["gzip", "deflate", "br"]:
            result.append(encoding)
    return result


def gzip_encode(data):
    """
    Compress `data` using gzip.

    The helper accepts either bytes or str. If a str is provided it will be
    encoded with the default encoding (utf-8) before compression.

    Returns:
        bytes: gzip-compressed bytes.
    """
    compressed_data = gzip.compress(data if isinstance(data, bytes) else data.encode())
    return compressed_data


def generate_response(http_method, http_full_path, http_version, host,
                      content_type, content_length, user_agent, request_body, directory, encoding_type, connection):
    """
    Build an HTTP response for a single request.

    This function implements the small set of behaviors required by the
    exercise: serve existing files, echo path segments, return User-Agent,
    handle POST to create files, and return simple status codes.

    Important: This helper returns raw bytes ready to be sent on the socket.

    Args (all strings except where noted):
        http_method: 'GET' or 'POST' (others will be ignored by the caller).
        http_full_path: request path from the request-line (e.g. '/foo').
        http_version: HTTP version from request-line (e.g. 'HTTP/1.1').
        host: Host header value or None.
        content_type: Content-Type header value or None.
        content_length: Content-Length header as integer (0 if absent).
        user_agent: User-Agent header value or None.
        request_body: request body as string or None.
        directory: host directory used for file operations.
        encoding_type: list of Accept-Encoding tokens.
        connection: Connection header value or None (e.g. 'close').

    Returns:
        bytes: full HTTP response (headers + optional body).
    """

    # If client requested connection close, include header in responses.
    connection_close = ""
    if connection == "close":
        connection_close = "Connection: close\r\n"

    http_response = b""
    match http_method:
        case "GET":
            # Serve file if it exists in the host directory.
            if check_file_exists(http_full_path, directory):
                target_file = os.path.join(directory, os.path.basename(http_full_path))
                http_code = "200 OK"
                # Read as text (keeps original behaviour) and determine length.
                with open(target_file, 'r') as file:
                    response_body = file.read()
                content_type = "application/octet-stream"
                content_length = os.path.getsize(target_file)

                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"{connection_close}"
                    f"\r\n"
                    f"{response_body}"
                ).encode()

            # Simple echo handler: GET /echo/<message>
            elif http_full_path.split("/")[1] == "echo":
                http_code = "200 OK"
                content_type = "text/plain"
                content_length = len(http_full_path.split("/")[2])
                response_body = http_full_path.split("/")[2]
                encoding_list = validate_encoding(encoding_type)

                if len(encoding_list) > 0:
                    # compress response when client accepts gzip/deflate/br
                    content_encoding = ", ".join(encoding_list)
                    compresed_body = gzip_encode(response_body)
                    http_response = (
                        f"{http_version} {http_code}\r\n"
                        f"Content-Encoding: {content_encoding}\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"Content-Length: {len(compresed_body)}\r\n"
                        f"{connection_close}"
                        f"\r\n"
                    ).encode() + compresed_body
                else:
                    http_response = (
                        f"{http_version} {http_code}\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"Content-Length: {content_length}\r\n"
                        f"{connection_close}"
                        f"\r\n"
                        f"{response_body}"
                    ).encode()

            # If present, return the User-Agent string as the response body.
            elif user_agent is not None:
                http_code = "200 OK"
                content_type = "text/plain"
                response_body = user_agent
                content_length = len(response_body)
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"{connection_close}"
                    f"\r\n"
                    f"{response_body}"
                ).encode()

            # Root path returns an empty 200 response (keeps original behaviour).
            elif http_full_path == "/":
                http_code = "200 OK"

                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"{connection_close}"
                    f"\r\n"
                ).encode()
            else:
                # Not found
                http_code = "404 Not Found"
                http_response = (
                    f"{http_version} {http_code}\r\n\r\n"
                    f"{connection_close}"
                ).encode()

        case "POST":
            # Create a file using the request body.
            if check_directory_exists(directory):
                create_file(http_full_path, directory, content_type, content_length, request_body)
                http_code = "201 Created"
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"{connection_close}"
                    f"\r\n"
                ).encode()

            else:
                http_code = "404 Not Found"
                http_response = (
                    f"{http_version} {http_code}\r\n\r\n"
                    f"{connection_close}"
                ).encode()

    return http_response


def parse_request(request):
    """
    Parse a raw HTTP request string into components.

    This parser is intentionally minimal: it splits headers on CRLF and stops
    parsing headers at the first empty line. It supports extracting a small
    set of headers used by this server (Host, Content-Length, Content-Type,
    User-Agent, Accept-Encoding, Connection).

    Args:
        request (str): raw HTTP request text (headers + optional body).

    Returns:
        tuple: (method, path, version, host, content_type, content_length,
                user_agent, request_body, encoding_type_list, connection)
    """
    sections = request.split("\r\n")
    request_line = sections[0].split(" ")
    method = request_line[0]
    path = request_line[1]
    version = request_line[2]

    header_host = None
    content_length = 0
    content_type = None
    user_agent = None
    encoding_type = []
    connection = None
    for header in sections[1:]:
        if header == "":
            break

        if header.lower().startswith("host:"):
            header_host = header.split(" ", 1)[1].strip()
        elif header.lower().startswith("content-length:"):
            content_length = int(header.split(" ", 1)[1].strip())
        elif header.lower().startswith("content-type:"):
            content_type = header.split(" ", 1)[1].strip()
        elif header.lower().startswith("user-agent:"):
            user_agent = header.split(" ", 1)[1].strip()
        elif header.lower().startswith("accept-encoding:"):
            for enc in header.split(" ", 1)[1].strip().split(","):
                encoding_type.append(enc.strip())
        elif header.lower().startswith("connection:"):
            connection = header.split(" ", 1)[1].strip()

    request_body = request.split("\r\n\r\n")[1] if "\r\n\r\n" in request else None
    return method, path, version, header_host, content_type, content_length, user_agent, request_body, encoding_type, connection


def handle_client(conn):
    """
    Handle a single client TCP connection.

    The function reads requests from the provided socket in a loop so a single
    TCP connection can be reused for multiple HTTP requests (persistent
    connections). It performs minimal parsing and then calls
    `generate_response` to build the reply which is sent back to the client.

    Note: This function reads up to 1024 bytes per recv call and treats the
    received chunk as a complete request for the purposes of parsing.

    Args:
        conn (socket.socket): accepted client socket.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", help="Host directory filepath")
    args = parser.parse_args()


    while True:
        # Read raw bytes from socket and decode to str.
        data = conn.recv(1024).decode().strip()
        if not data:
            print("1) Connection closed")
            break

        (http_method, http_full_path, http_version, host, content_type, content_length, user_agent,
         request_body, encoding_type, connection) = parse_request(data)

        # Generate the HTTP response (headers + optional body)
        http_response = generate_response(http_method, http_full_path, http_version, host, content_type,
                                          content_length, user_agent, request_body, args.directory, encoding_type, connection)

        # Send response back to client
        conn.sendall(http_response)

        # `Connection: close` header by breaking out of request loop.
        if connection == "close":
            print("2) Connection close detected, closing connection.")
            break

    conn.close()


def main():

    server_socket = socket.create_server(("localhost", 4221))


    while True:
        conn, addr = server_socket.accept()  # wait for client

        # Start a new thread to handle the connection so multiple TCP clients
        # can be served concurrently.
        threading.Thread(target=handle_client, args=(conn, )).start()
        print("Started thread for client:", addr)



if __name__ == "__main__":
    main()
