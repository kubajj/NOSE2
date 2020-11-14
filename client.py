import socket
import sys
from common_methods import recv_listing, send_file, recv_file, parsing_check

# Initialize necessary variables
filename = ""
status = "Failure"
status_code = 0

# Attempt for connection
try:
    cli_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_addr = (sys.argv[1], int(sys.argv[2]))
    mode_argument = sys.argv[3]
except Exception as exp:
    print(exp)
    # Print status message and terminate
    print(str(srv_addr), mode_argument, filename, status)
    # Exit with failure code
    exit(1)

try:
    # Parse arguments
    if mode_argument == "list":
        mode = 0
    elif mode_argument == "put":
        mode = 1
        filename = sys.argv[4]
    elif mode_argument == "get":
        mode = 2
        filename = sys.argv[4]
    else:
        print("Invalid request argument.")
        # Print status message and terminate
        print(str(srv_addr), mode_argument, filename, status)
        # Exit with failure code
        exit(1)

    # Filename limit reached
    if len(filename) > 255:
        print("Python cannot open files with more than 255 characters in name.")
    else:
        # Connect to server
        cli_sock.connect(srv_addr)

        # the first part of first request has to be in the form of:
        # mode (single value int):
        #   0 -> list content of directory
        #   1 -> upload a file
        #   2 -> download a file
        # if mode is 1 or 2, the second argument will be the filename
        # in case of mode 1, the data of the file should be sent in the following requests
        # arguments have to be separated with "|"
        # Ex.: 1|test.txt|
        message = str(mode) + "|"

        # Add filename to request
        if mode == 1 or mode == 2:
            message += filename + "|"
        # Send request to server
        cli_sock.sendall(message.encode('utf-8'))
        # Check if parsing was successful on the server side
        parsing_status = parsing_check(cli_sock, mode, filename)
        # Inform server about parsing status
        cli_sock.send(str(parsing_status).encode('utf-8'))
        # Execute request
        if parsing_status == 0:
            if mode == 0:
                # Request listing
                status_code = recv_listing(cli_sock)
            elif mode == 1:
                # Request upload
                status_code = send_file(cli_sock, filename)
            elif mode == 2:
                # Request download
                status_code = recv_file(cli_sock, filename)

except Exception as exp:
    print(exp)
    # Print status message and terminate, socket will be closed by server
    print(str(srv_addr), mode_argument, filename, status)
    # Exit with failure code
    exit(1)

# If the execution returned 0 then it was success, otherwise not
if status_code == 0:
    status = "Success"
# Print status message and terminate, socket will be closed by server
print(str(srv_addr), mode_argument, filename, status)
