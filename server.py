import struct
import zlib
import socket
import sys
import getopt
import time

PTYPE_DATA = 1
PTYPE_ACK = 2
PTYPE_SACK = 3

MAX_WINDOW = 63
MAX_SEQNUM = 2047
MAX_LENGTH = 1024

def create_server(server_addr: str, port: int):
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.bind((server_addr, port))
        print(f"Serveur UDP IPv6 écoute sur {server_addr}:{port} ...", file=sys.stderr)

        raw_path, client_addr = sock.recvfrom(2048)
        path = raw_path.decode().strip()
        print(f"Client connecté depuis {client_addr}, path='{path}'", file=sys.stderr)

        payload = b"Hello, client from SRTP server!"
        timestamp = int(time.time() * 1000) & 0xffffffff  # Masque 32-bit
        segment = encode("PTYPE_DATA", 0, 0, timestamp, payload)
        sock.sendto(segment, client_addr)
        print(f"Segment DATA envoyé ({len(payload)} bytes)", file=sys.stderr)

    except socket.error as err:
        print(f'Erreur socket: {err}', file=sys.stderr)
        return -1
    except Exception as e:
        print(f'Erreur inattendue: {e}', file=sys.stderr)
        return -1
    return 0

def encode(type_str, window, seqnum, timestamp, payload):
    match type_str:
        case "PTYPE_DATA": type_bits = 1
        case "PTYPE_ACK": type_bits = 2
        case "PTYPE_SACK": type_bits = 3
        case _: type_bits = 0

    length = len(payload)
    # MASQUE 32-bit pour éviter overflow struct 'I'
    word = ((type_bits << 30) | (window << 24) | (length << 11) | seqnum) & 0xffffffff

    # Header 8 bytes
    header_bytes = struct.pack('!II', word, timestamp & 0xffffffff)
    
    # CRC1 sur header 8 bytes
    crc1_calc = zlib.crc32(header_bytes) & 0xffffffff
    crc1 = struct.pack('>I', crc1_calc)

    message = [header_bytes, crc1]
    if payload:
        message.append(payload)
        crc2_calc = zlib.crc32(payload) & 0xffffffff
        crc2 = struct.pack('>I', crc2_calc)
        message.append(crc2)
    
    return b''.join(message)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 server.py hostname port", file=sys.stderr)
        sys.exit(1)

    server_addr = sys.argv[1]
    port = int(sys.argv[2])

    result = create_server(server_addr, port)
    if result != 0:
        sys.exit(1)
