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
    byte1 = struct.pack('!B', (type_bits << 6 | window))
    header.append(byte1)

    length = len(payload)
    header.append(struct.pack('!H', length))
    header.append(struct.pack('!H', seqnum))
    header.append(struct.pack('I', timestamp))

    header_bytes = b''.join(header)
    crc1 = zlib.crc32(header_bytes)

    message.append(header_bytes)
    message.append(struct.pack('!I',crc1))
    message.append(payload)
    if payload:
        crc2 = zlib.crc32(payload)
        message.append(struct.pack('!I', crc2))
    full_message = b''.join(message)
    return full_message





