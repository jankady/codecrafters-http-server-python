import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    conn, addr = server_socket.accept() # wait for client

    data = conn.recv(1024).decode().strip().split(" ")

    http_method = data[0]
    http_path = data[1]
    http_version = data[2].split("\r\n")[0]
    http_code = ""

    if http_path != "/":
        http_code = "404 Not Found"
    else:
        http_code = "200 OK"

    http_response = ""
    match http_method:
        case "GET":
            http_response = (
                f"{http_version} {http_code}\r\n\r\n"

            )
        case "POST":
            pass

    conn.send(http_response.encode())
    conn.close()



if __name__ == "__main__":
    main()
