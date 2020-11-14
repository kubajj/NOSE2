import socket
import os
import time


grades = ["B", "KB", "MB", "GB", "TB", "PB"]  # Last two are a bit unnecessary


# This method enables sender to send a file through given socket
def send_file(sock, filename):
    try:
        # Check if file exists
        if not os.path.isfile(filename):
            print(filename)
            if os.path.isdir(filename):
                # File is directory
                print(filename, "is directory.")
                sock.send("d".encode('utf-8'))
            else:
                # File does not exists
                print("File", filename, "does not exist.")
                sock.send("-1".encode('utf-8'))
            # Return with failure code
            return 1

        # Check if file is too large e.g. > 5 GB
        actual_size = os.path.getsize(filename)
        if actual_size > 5*2**30:
            sock.send("-5".encode('utf-8'))
            print("File too large.")
            # Return with failure code
            return 1

        # Load data
        now1 = time.time()
        with open(filename, "rb", ) as file:
            data = file.read()
        now2 = time.time()
        # Print information about loading
        size = len(data)
        loading_time = now2 - now1
        speed, filesize = stats_for_nerds(size, loading_time)
        if loading_time > 1:
            print(f"Took {loading_time:.2f}", "seconds to load",
                  filename, "of size", filesize, "at", speed)
        else:
            print(f"Took {loading_time:.2e}", "seconds to load",
                  filename, "of size", filesize, "at", speed)

        # Check if data loaded correctly
        if not size == actual_size:
            # Size of data read does not match size of file
            sock.send("-2".encode('utf-8'))
            print("File reading error occurred.")
            # Return with failure code
            return 1

        # Send size of file to recipient
        sock.send(str(size).encode('utf-8'))
        # Receive confirmation from recipient
        received = int(sock.recv(1024).decode('utf-8'))
        if received == -3:
            # Received error "File already exists" from recipient
            print(filename, "already exists. Overwriting files is not allowed.")
        elif not size == received:
            # Bad transmission, filesize does not match filesize transferred
            print("Transmission error occurred.")
            # Send error message to recipient
            sock.send("-4".encode('utf-8'))
            # Return with failure code
            return 1
        else:
            # Send confirmation to recipient
            sock.send("0".encode('utf-8'))
            # Allow recipient to prepare for receiving and prevent collating
            time.sleep(0.1)
            # Send data
            sock.sendall(data)
        status = int(sock.recv(1024).decode('utf-8'))
        if status == 0:
            # Return with success code
            return 0
        else:
            # Bad transmission, filesize does not match size of file written
            print("Transmission error occurred.")
            # Return with failure code
            return 1
    except Exception as exp:
        print(exp)
        return 1


# This method enables recipient to receive a file through given socket
def recv_file(sock, filename):
    try:
        filesize = sock.recv(1024).decode('utf-8')
        # Check for error messages from sender
        if filesize == "d":
            # File is directory code received
            print("File is directory.")
            # Return with failure code
            return 1
        elif filesize == "-5":
            # File is bigger than 5 GB
            print("File too large.")
            # Return with failure code
            return 1
        elif int(filesize) == -1:
            # File does not exists code received
            print("File does not exist.")
            # Return with failure code
            return 1
        elif int(filesize) == -2:
            # File size does not match loaded size
            print("File reading error occurred.")
            # Return with failure code
            return 1
        # Check if file exists
        elif os.path.isfile(filename):
            # File already exists
            print(filename, "already exists. Overwriting files is not allowed.")
            # Send error code to sender
            sock.send("-3".encode('utf-8'))
            # Return with failure code
            return 1
        # Send confirmation to sender
        else:
            sock.sendall(str(filesize).encode('utf-8'))
        # Receive confirmation from sender
        size_check = int(sock.recv(1024).decode('utf-8'))

        # One of the transmissions of filesize went wrong
        if size_check == -4:
            print("Transmission error occurred.")
            # Return with failure code
            return 1
        else:
            filesize = int(filesize)

        # Calculate optimal size of buffer
        buffer_size = 1
        while filesize / 2 ** (5 * buffer_size) > 32:
            buffer_size += 1
        buffer_size = 2 ** (5 * (buffer_size - 1))
        packets = 0
        received_size = 0

        # Receive data and write to file,
        number_of_empty_packets = 0
        now1 = time.time()
        file = open(filename, "ab")
        while received_size < filesize:
            packets += 1
            received_data = sock.recv(buffer_size)
            if len(received_data) == 0:
                number_of_empty_packets += 1
                if number_of_empty_packets >= 10:
                    print("Transmission timeout")
                    # Return with failure code
                    return 1
            else:
                number_of_empty_packets = 0
            received_size += len(received_data)
            file.write(received_data)
        file.close()
        now2 = time.time()

        # Check if file was transmitted correctly
        if os.path.getsize(filename) == filesize:
            # Stats for nerds
            transmission_time = now2 - now1
            speed, filesize = stats_for_nerds(filesize, transmission_time)
            if transmission_time > 1:
                print(f"Took {transmission_time:.2f}", "seconds to receive",
                      filename, "of size", filesize, "in", packets, "packets at", speed)
            else:
                print(f"Took {transmission_time:.2e}", "seconds to receive",
                      filename, "of size", filesize, "in", packets, "packets at", speed)
            sock.sendall(str(0).encode('utf-8'))
        else:
            print("Error occurred: File corrupted.")
            os.remove(filename)
            sock.sendall(str(-1).encode('utf-8'))
            # Return with failure code
            return 1
        # Return with success code
        return 0
    except Exception as exp:
        print(exp)
        return 1


# This method enables sender to send a listing of current directory
def send_listing(sock):
    try:
        # Get listing
        listing = os.listdir()

        # Send recipient expected size of list
        size = len(listing)
        sock.send(str(size).encode('utf-8'))
        # Get confirmation from recipient
        received = int(sock.recv(1024).decode('utf-8'))
        if not size == received:
            # Bad transmission, size does not match size transferred
            print("Transmission error occurred.")
            # Send error message to recipient
            sock.send("-1".encode('utf-8'))
            # Return with failure code
            return 1
        else:
            sock.send("0".encode('utf-8'))
            # Allow recipient to prepare for receiving and prevent collating
            time.sleep(0.1)
        # add / tag to the beginning and the end of the name
        # as it cannot be contained in a name of file because
        # it is a symbol for directories
        to_send = "/" + "//".join(listing) + "/"
        # Each file is now surrounded by two "/", so we know where it starts and ends
        sock.sendall(to_send.encode('utf-8'))
        # Accept status code from recipient
        status = int(sock.recv(1024).decode('utf-8'))
        if status == 0:
            # Return with success code
            return 0
        else:
            # Bad transmission, listing size does not match size of received list
            print("Transmission error occurred.")
            # Return with failure code
            return 1
    except Exception as exp:
        print(exp)
        return 1


# This method enables recipient to receive a listing of sender's current directory
def recv_listing(sock):
    try:
        # Receive a size of listing
        list_size = sock.recv(1024).decode('utf-8')
        # Send received value to sender for check
        sock.sendall(list_size.encode('utf-8'))

        # Receive confirmation from sender
        size_check = int(sock.recv(1024).decode('utf-8'))
        # One of the transmissions of filesize went wrong
        if size_check == -1:
            print("Transmission error occurred.")
            # Return with failure code
            return 1

        # Receive listing of files
        # All special characters except "/" which cannot be in a filename should be supported
        list_size = int(list_size)
        current_filename = ""
        filename_too_long = False
        listing = []
        while len(listing) < list_size:
            received_data = sock.recv(1024).decode('utf-8')
            # Filename did not fit into packet
            if filename_too_long:
                # Check if filename ends in the current packet
                if "/" in received_data:
                    index_of_slash = received_data.find("/")
                    # Remove part of current packet containing current filename
                    # and add filename to listing
                    listing.append(current_filename + received_data[:index_of_slash])
                    current_filename = ""
                    filename_too_long = False
                    received_data = received_data[index_of_slash + 1:]
                # If not, add current packet to filename and continue
                else:
                    current_filename += received_data
            # Split current packet into filenames
            received_names = received_data.split("/")
            # Check if there is a file which did not fit into packet
            if not received_data[-1] == "/":
                current_filename = received_names[-1]
                received_names = received_names[:-1]
                filename_too_long = True
            # Add filenames to listing
            for filename in received_names:
                if not filename == "":
                    listing.append(filename)
        if len(listing) == list_sizeb.com\
                :
            # Print listing
            for file in listing:
                print(file)
            # Send status code to sender
            sock.sendall(str(0).encode('utf-8'))
            # Return with success code
            return 0
        else:
            # Bad transmission, listing size does not match size of received list
            print("Transmission error occurred.")
            # Send status code to sender
            sock.sendall(str(-1).encode('utf-8'))
            # Return with failure code
            return 1
    except Exception as exp:
        print(exp)
        return 1


# This method checks if parsing on server side was correct
def parsing_check(sock, mode, filename=""):
    try:
        parsing_code = int(sock.recv(1024).decode('utf-8'))
        # Analyse parsing codes
        if parsing_code == -1:
            print("Invalid mode code received.")
            return 1
        elif not int(parsing_code) == mode + len(filename):
            print("Transmission error during parsing phase.")
            return 1
        return 0
    except Exception as exp:
        print(exp)
        return 1


# This method sends parsing check to client and returns status of this operation
def send_parsing_check(sock, error_occurred, *args):
    try:
        # error occurred on the server side
        if error_occurred:
            message = -1
        elif len(args) == 1:
            message = args[0]  # mode
        else:
            message = args[0] + len(args[1])  # mode + len(filename)
        sock.sendall(str(message).encode('utf-8'))
        parsing_status = int(sock.recv(1024).decode('utf-8'))
        if not parsing_status == 0:
            print("Parsing went wrong.")
        # If parsing status is 0, everything was right, otherwise error
        return parsing_status
    except Exception as exp:
        print(exp)
        return 1


# This method calculates speed of transmission and better looking filesize (in B, KB, MB, ...)
def stats_for_nerds(size, t):
    grade = 0
    if not size == 0:
        while size / 2 ** (10 * grade) > 1:
            grade += 1
        grade -= 1
    size = size / 2 ** (10 * grade)
    speed = f"{size / t:.2f}" + " " + grades[grade] + "ps"
    filesize = f"{size:.2f}" + " " + grades[grade]
    return speed, filesize
