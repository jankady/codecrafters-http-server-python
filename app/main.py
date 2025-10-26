import argparse
import socket  # noqa: F401
from multiprocessing import Process
import os
import gzip

def check_file_exists(path_to_file, directory):
    get_file = os.path.basename(path_to_file)

    try:
        files_in_directory = os.listdir(directory)  # list of files in the directory
        if get_file in files_in_directory:
            return True
    except Exception:
        return False

    return False


def check_directory_exists(directory):
    try:
        if os.path.exists(directory) and os.path.isdir(directory):
            return True
    except Exception:
        return False

    return False


def create_file(path_to_file, directory, content_type, content_length, content_body):
    get_file = os.path.basename(path_to_file)
    target_file = os.path.join(directory, get_file)

    try:
        with open(target_file, 'w') as file:
            file.write(content_body)
        return True
    except Exception:
        return False

    return False


def validate_encoding(encoding_type):
    result = []
    for encoding in encoding_type:
        if encoding in ["gzip", "deflate", "br"]:
            result.append(encoding)
    return result


def gzip_encode(data):
    compressed_data = gzip.compress(data if isinstance(data, bytes) else data.encode())
    return compressed_data

def generate_response(http_method, http_full_path, http_version, host,
                      content_type, content_length, user_agent, request_body, directory, encoding_type):
    http_response = b""
    match http_method:
        case "GET":
            if check_file_exists(http_full_path, directory):
                target_file = os.path.join(directory, os.path.basename(http_full_path))
                http_code = "200 OK"
                with open(target_file, 'r') as file:
                    response_body = file.read()
                content_type = "application/octet-stream"
                content_length = os.path.getsize(target_file)

                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"\r\n"
                    f"{response_body}"
                ).encode()

            elif http_full_path.split("/")[1] == "echo":
                http_code = "200 OK"
                content_type = "text/plain"
                content_length = len(http_full_path.split("/")[2])
                response_body = http_full_path.split("/")[2]
                encoding_list = validate_encoding(encoding_type)

                if len(encoding_list) > 0:
                    content_encoding = ", ".join(encoding_list)
                    compresed_body = gzip_encode(response_body)
                    http_response = (
                        f"{http_version} {http_code}\r\n"
                        f"Content-Encoding: {content_encoding}\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"Content-Length: {len(compresed_body)}\r\n"
                        f"\r\n"
                    ).encode() + compresed_body
                else:
                    http_response = (
                        f"{http_version} {http_code}\r\n"
                        f"Content-Type: {content_type}\r\n"
                        f"Content-Length: {content_length}\r\n"
                        f"\r\n"
                        f"{response_body}"
                    ).encode()

            elif user_agent is not None:
                http_code = "200 OK"
                content_type = "text/plain"
                response_body = user_agent
                content_length = len(response_body)
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"\r\n"
                    f"{response_body}"
                ).encode()
            elif http_full_path == "/":
                http_code = "200 OK"
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"\r\n"
                    f"{request_body}"
                ).encode()
            else:
                http_code = "404 Not Found"
                http_response = (
                    f"{http_version} {http_code}\r\n\r\n"
                ).encode()

        case "POST":
            if check_directory_exists(directory):
                create_file(http_full_path, directory, content_type, content_length, request_body)
                http_code = "201 Created"
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"\r\n"
                ).encode()

            else:
                http_code = "404 Not Found"
                http_response = (
                    f"{http_version} {http_code}\r\n\r\n"
                ).encode()

    return http_response


def parse_request(request):
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

    request_body = request.split("\r\n\r\n")[1] if "\r\n\r\n" in request else None
    return method, path, version, header_host, content_type, content_length, user_agent, request_body, encoding_type


def handle_client(conn, addr):

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", help="Host directory filepath")
    args = parser.parse_args()

    while True:
        data = conn.recv(1024).decode().strip()
        if not data:
            break

        (http_method, http_full_path, http_version, host, content_type, content_length, user_agent,
         request_body, encoding_type) = parse_request(data)

        http_response = generate_response(http_method, http_full_path, http_version, host, content_type,
                                          content_length, user_agent, request_body, args.directory, encoding_type)

        conn.send(http_response)

    conn.close()


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221))

    while True:
        conn, addr = server_socket.accept()  # wait for client

        process = Process(target=handle_client, args=(conn, addr))
        process.start()
        conn.close()


if __name__ == "__main__":
    main()
