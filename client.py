import struct
import zlib
import socket
import sys
import getopt

def connect_client(server_name : str):
    #Format of server name is http://hostname:port/path/to/file 
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        server_list = server_name.split('//') # ['http:', 'hostname:port/path/to/file']
        hostname, port = server_list[1].split('/')[0].split(':') # ['hostname', 'port']
        path = ('/').join(server_list[1].split('/')[1:]) # path/to/file
        sock.connect((hostname, port))
        print(f"Connected to the server at hostname {hostname} and port {port}")
        
    except socket.error as err:
        print("There is an error: ", err)
        return -1
    return 0



if __name__ == "__main__":
    if len(sys.argv)>1:
        print("Enough arguments were given.")
        args = sys.argv[1:]
        options = "s:"
        long_options = ["save="]
        try:
            arguments, values= getopt.getopt(args=args, shortopts=options, longopts=long_options)
            for currentArg, currentVal in arguments:
                if currentArg in ('-s', '--save'):
                    print(f"Saving the file to the directory {currentVal}.") 

        except getopt.error as err:
            print("There is an error: ",str(err))
    else: 
        print("No arguments given")

