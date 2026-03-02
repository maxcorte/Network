from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import zlib

PTYPE_DATA = 1
PTYPE_ACK = 2
PTYPE_SACK = 3

MAX_WINDOW = 63  # 6 bits
MAX_SEQNUM = 2047  # 11 bits
MAX_LENGTH = 1024  # 13 bits

HEADER_LEN = 12  # 12 Octets -> 4 pour type/window/length/seqnum, 4 pour timestamp, 4 pour CRC1

class DecodeError(Exception):
    pass

@dataclass
class Segment:
    ptype: int
    window: int
    length: int
    seqnum: int
    timestamp: int
    payload: bytes

def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xffffffff

def decode_segment(raw: bytes) -> Segment: 
    if len(raw) < HEADER_LEN:
        raise DecodeError("Segment too short")
    
    word = int.from_bytes(raw[0:4], byteorder='big')

    ptype = (word >> 30) & 0x3 #bits 31-30
    window = (word >> 24) & 0x3f #bits 29-24
    length = (word >> 11) & 0x1fff #bits 23-11
    seqnum = word & 0x7ff #bits 10-0

    if ptype not in (PTYPE_DATA, PTYPE_ACK, PTYPE_SACK):
        raise DecodeError(f"Invalid packet type: {ptype}")
    if not (0 <= window <= MAX_WINDOW):
        raise DecodeError(f"Invalid window size: {window}")
    if not (0 <= seqnum <= MAX_SEQNUM):
        raise DecodeError(f"Invalid seqnum: {seqnum}")
    if not (0 <= length <= MAX_LENGTH):
        raise DecodeError(f"Invalid length: {length}")
    
    timestamp = int.from_bytes(raw[4:8], byteorder='big')

    crc1_recv = int.from_bytes(raw[8:12], byteorder='big')
    crc1_calc = crc32(raw[0:8])
    if crc1_recv != crc1_calc:
        raise DecodeError("CRC1 mismatch")
    
    payload = b""
    offset = HEADER_LEN

    if length == 0:
        if len(raw) != HEADER_LEN:
            raise DecodeError("Extra bytes in zero-length packet")
        
        return Segment(ptype, window, length, seqnum, timestamp, payload)
    
    expected_total = HEADER_LEN + length + 4
    if len(raw) < expected_total:
        raise DecodeError("Truncated data packet")
    
    payload = raw[offset:offset+length]
    crc2_recv = int.from_bytes(raw[offset+length:offset+length+4], byteorder='big')
    crc2_calc = crc32(payload)
    if crc2_recv != crc2_calc:
        raise DecodeError("CRC2 mismatch")
    return Segment(ptype, window, length, seqnum, timestamp, payload)

if __name__ == "__main__":
    print(decode_segment(bytes.fromhex('4a 00 28 2a 00 bc 61 4e 9c 37 80 b7 68 65 6c 6c 6f 36 10 a6 86')))
    
