import argparse
import socket  # noqa: F401
from multiprocessing import Process
import os


def check_file_exists(path_to_file, directory):
    get_file = os.path.basename(path_to_file)

    try:
        files_in_directory = os.listdir(directory)  # Seznam souborů ve složce
        if get_file in files_in_directory:
            return True
    except Exception:
        return False

    return False


def generate_response(http_method, http_full_path, http_version, user_agent, path_to_file, directory):
    http_response = ""
    match http_method:
        case "GET":
            if check_file_exists(path_to_file, directory):
                target_file = os.path.join(directory, os.path.basename(path_to_file))
                http_code = "200 OK"
                content_type = "application/octet-stream"
                with open(target_file, 'r') as file:
                    response_body = file.read()
                content_length = os.path.getsize(target_file)
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"\r\n"
                    f"{response_body}"
                )

            elif http_full_path.split("/")[1] == "echo":
                http_code = "200 OK"
                content_type = "text/plain"
                content_length = len(http_full_path.split("/")[2])
                response_body = http_full_path.split("/")[2]
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"\r\n"
                    f"{response_body}"
                )
            elif http_full_path.split("/")[1].lower() == "user-agent":
                http_code = "200 OK"
                content_type = "text/plain"
                content_length = len(user_agent)
                response_body = user_agent
                http_response = (
                    f"{http_version} {http_code}\r\n"
                    f"Content-Type: {content_type}\r\n"
                    f"Content-Length: {content_length}\r\n"
                    f"\r\n"
                    f"{response_body}"
                )

            elif http_full_path == "/":
                http_code = "200 OK"
                content_type = "text/plain"
                content_length = 1
                response_body = ''
                http_response = (
                    f"{http_version} {http_code}\r\n"


                    f"\r\n"
                    f"{response_body}"
                )
            else:
                http_code = "404 Not Found"
                http_response = (
                    f"{http_version} {http_code}\r\n\r\n"
                )

        case "POST":
            pass

    return http_response


def handle_client(conn, addr):
    data = conn.recv(1024).decode().strip().split(" ")

    print(f"Received request decoded: {data}")

    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", help="Host directory filepath")
    args = parser.parse_args()

    http_method = data[0]
    http_full_path = data[1]
    http_version = data[2].split("\r\n")[0]
    user_agent = data[4].lower() if len(data) > 4 else ""

    http_response = generate_response(http_method, http_full_path, http_version, user_agent, http_full_path,
                                      args.directory)

    print(f"Sending response: {http_response}")
    conn.send(http_response.encode())
    conn.close()


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)

    while True:
        conn, addr = server_socket.accept()  # wait for client

        process = Process(target=handle_client, args=(conn, addr))
        process.start()
        conn.close()


if __name__ == "__main__":
    main()
