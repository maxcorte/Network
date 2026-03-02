import struct
import zlib
import socket
import sys
import getopt




def create_server(server_addr: str, port: int):
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.bind((server_addr, port))
        print(f"Serveur UDP IPv6 écoute sur {server_addr}:{port} ...")
    except socket.error as err:
        print(f'There is an error: ', err)
        return -1
    return 0


def encode(type, window, seqnum, timestamp, payload):
    header = []
    message = []
    match type:
        case "PTYPE_DATA": type_bits = 1
        case "PTYPE_ACK": type_bits = 2
        case "PTYPE_SACK": type_bits = 3
        case _: type_bits = 0

    length = len(payload)

    word = (type_bits << 30) | (window << 24) | (length << 11) | seqnum

    header.append(struct.pack('!I', word))
    header.append(struct.pack('!I', timestamp))

    header_bytes = b''.join(header)
    crc1 = struct.pack('!I', zlib.crc32(header_bytes) & 0xffffffff)

    message.append(header_bytes)
    message.append(crc1)
    message.append(payload)
    if payload:
        crc2 = struct.pack('!I', zlib.crc32(payload) & 0xffffffff)
        message.append(crc2)
    full_message = b''.join(message)
    return full_message

if __name__ == "__main__":
    #print(encode("PTYPE_DATA", 5, 10, 1234567890, b"Hello"))
    if len(sys.argv)>1:
        print("Enough arguments were given.")
        args = sys.argv[1:]
        options = "r:"
        long_options = ["root="]
        try:
            arguments, values= getopt.getopt(args=args, shortopts=options, longopts=long_options)
            for currentArg, currentVal in arguments:
                if currentArg in ('-r', '--root'):
                    print(f"Opening the file from the directory {currentVal}.") 
            create_server(server_addr = str(values[0]), port = int(values[1]))

        except getopt.error as err:
            print("There is an error: ",str(err))
    else: 
        print("No arguments given")




