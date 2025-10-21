import socket  # noqa: F401


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    conn, addr = server_socket.accept() # wait for client

    data = conn.recv(1024).decode().strip().split(" ")

    print(f"Received request decoded: {data}")

    http_method = data[0]
    http_full_path = data[1]
    http_version = data[2].split("\r\n")[0]

    http_response = ""
    match http_method:
        case "GET":
            if http_full_path.split("/")[1] == "echo":
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


    print(f"Sending response: {http_response}")
    conn.send(http_response.encode())
    conn.close()



if __name__ == "__main__":
    main()
