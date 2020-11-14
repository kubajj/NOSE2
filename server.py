import socket
import sys
from common_methods import send_file, recv_file, send_listing, send_parsing_check

srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
srv_sock_addr = ("0.0.0.0", int(sys.argv[1]))
try:
    srv_sock.bind(srv_sock_addr)
    print(str(srv_sock_addr), "server up and running")
    # for this purpose, the number could be 1
    # as only one client is going to be connected at once
    srv_sock.listen(5)
except Exception as exp:
    print(exp)
    exit(1)

# Server socket should not ever be closed
server_socket_open = True
while server_socket_open:
    try:
        print("Socket opened. Awaiting connections.")
        # Connect to client
        cli_sock, cli_addr = srv_sock.accept()
        print("Connection with", str(cli_addr), "achieved.")

        # No need for support of longer filenames
        # as the maximum limit of python is 255 (I tested it)
        cli_request = cli_sock.recv(1024).decode('utf-8')

        # the first part of first request has to be in the form of:
        # mode (single value int):
        #   0 -> list content of directory
        #   1 -> upload a file
        #   2 -> download a file
        # if mode is 1 or 2, the second argument will be the filename
        # in case of mode 1, the data of the file should be sent in the following requests
        # arguments have to be separated with "|"
        # Ex.: 1|test.txt|

        # Begin parsing
        arguments = cli_request.split("|")
        mode = int(arguments[0])
        filename = ""
        status_code = 0
        if mode == 0:
            mode_argument = "list"
            # Check if parsing was correct
            parsing_status = send_parsing_check(cli_sock, False, mode)
            if parsing_status == 0:
                # Client want to receive listing of current directory
                status_code = send_listing(cli_sock)
        elif mode == 1 or mode == 2:
            filename = arguments[1]
            # Check if parsing was correct
            parsing_status = send_parsing_check(cli_sock, False, mode, filename)
            if parsing_status == 0:
                if mode == 1:
                    # Client wants to upload a file
                    mode_argument = "put"
                    status_code = recv_file(cli_sock, filename)
                else:
                    # Client wants to download a file
                    mode_argument = "get"
                    status_code = send_file(cli_sock, filename)
        else:
            print("Invalid mode")
            mode_argument = "invalid"
            send_parsing_check(cli_sock, error_occurred=True)

        # Status code has to be 0 to print success,
        # so if parsing did not go through, it is > 0 and hence, status code != 0
        status_code += parsing_status
        status = "Failure"
        if status_code == 0:
            status = "Success"
        # Print status message
        print(str(cli_addr), mode_argument, filename, status, "\n")
    except Exception as exp:
        print(exp)
        continue
    finally:
        # Close client socket
        cli_sock.close()
# Close server socket
srv_sock.close()

# Exit with success code
exit(0)
