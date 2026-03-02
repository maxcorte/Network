import struct
import zlib


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
    header.append(struct.pack('I', timestamp))

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
    print(encode("PTYPE_DATA", 5, 10, 1234567890, b"Hello"))





