import struct
import zlib
import socket
import sys
import getopt
import time
import os
import argparse

PTYPE_DATA = 1
PTYPE_ACK = 2
PTYPE_SACK = 3

MAX_WINDOW = 63
MAX_SEQNUM = 2047
MAX_LENGTH = 1024

DEFAULT_DIRECTORY = '.'


#pour lire les ack
def decode_ack(raw: bytes):
    if len(raw) < 12:
        return None, None, b""
    
    header_bytes = raw[0:8]
    crc1_recv = int.from_bytes(raw[8:12], byteorder='big')
    crc1_calc = zlib.crc32(header_bytes) & 0xffffffff
    
    if crc1_recv != crc1_calc:
        #crc mauvais don on ignore le ack
        return None, None, b""
        
    word = int.from_bytes(raw[0:4], byteorder='big')
    ptype = (word >> 30) & 0x3
    length = (word >> 11) & 0x1fff
    seqnum = word & 0x7ff
    
    payload = b""
    #si sack => on extrait le payload
    if ptype == PTYPE_SACK and length > 0:
        expected_total_length = 12 + length + 4
        if len(raw) < expected_total_length:
            return None, None, b""
        payload = raw[12:12+length]        
        crc2_recv = int.from_bytes(raw[12+length:12+length+4], byteorder='big')
        crc2_calc = zlib.crc32(payload) & 0xffffffff
        
        if crc2_recv != crc2_calc:
            return None, None, b""
            
    return ptype, seqnum, payload

#payload binaire en liste de num 
def decode_sack_payload(payload: bytes):
    if not payload:
        return []
    bit_string = ""
    for byte in payload:
        #format(byte, '08b') transforme un octet en texte de 8carct
        octet_binaire = format(byte, '08b')
        bit_string += octet_binaire
        
    out_of_order = []
    #decoupe la chaine en 11 bits et convertit chaque morceau en nb entier
    for i in range(0, len(bit_string) - 10, 11):        
        chunk = bit_string[i : i + 11]
        #comment savoir si padding ou si paquet 0 ? regarder si un 1 est present dans le reste de la chaine
        reste_de_la_chaine = bit_string[i:]
        if chunk == "00000000000" and "1" not in reste_de_la_chaine:
            break
        seq = int(chunk, 2)
        out_of_order.append(seq)

    return out_of_order

def create_server(server_addr: str, port: int, directory: str):
    try:
        sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        sock.bind((server_addr, port))
        print(f"Serveur UDP IPv6 écoute sur {server_addr}:{port} ...", file=sys.stderr)

        while True:
            raw_request, client_addr = sock.recvfrom(2048)
            try:
                request_str = raw_request.decode('ascii').strip()
            except UnicodeDecodeError:
                #si corrompu on l'ignore
                continue   

            # Si c'est le bon format on recoit la requete sous le format: 
            # "GET /llmsmall\r\n" de la part du client.

            if request_str.startswith('GET '):  #si ca commence bien par "GET " alors c'est bien une requete HTTP 0.9
                path = request_str[4:].rstrip('\r\n')
                file_path = os.path.join(directory, path.lstrip("/"))
                try:
                    with open(file_path, 'rb') as f: #read binary
                        payload = f.read()
                except FileNotFoundError:
                    print("File not found")
                    payload = b""
            else:
                print("Request is not in the valid format.")
                

            timestamp = int(time.time() * 500) & 0xffffffff  # Masque 32-bit
            seqnum = 0
            #remplacer par 500 pour pouvoir faire passer les tests link simulator (max 528 et avant on avait 1024 + header donc 1040)
            if len(payload) > 500:
                seq_payloads = [payload[i:i+500] for i in range(0, len(payload), 500)]
            else:
                seq_payloads = [payload]
            # dernier seg vide ajouté pour qu'il soit géré par la window coulissante
            seq_payloads.append(b"")
            total_chunks = len(seq_payloads)
            base = 0
            next_to_send = 0
            window_size = 10 
            max_retries = 50
            retries = 0
            acked_indices = set() #memoire des morceaux deja valides
            sock.settimeout(0.5) #attendre les acks

            while base < total_chunks:
                # envoi de paquets (dans la limite de la fenetre)
                while next_to_send < base + window_size and next_to_send < total_chunks:
                    if next_to_send in acked_indices:
                        next_to_send += 1
                        continue
                    elements = seq_payloads[next_to_send]
                    current_seqnum = next_to_send % 2048
                    
                    segment = encode(type_str="PTYPE_DATA", window=0, seqnum=current_seqnum, timestamp=timestamp, payload=elements)
                    sock.sendto(segment, client_addr)
                    
                    if not elements:
                        print(f"Dernier segment DATA envoyé (Seq: {current_seqnum}, 0 bytes)", file=sys.stderr)
                    else:
                        print(f"Segment DATA envoyé (Seq: {current_seqnum}, {len(elements)} bytes)", file=sys.stderr)
                    
                    next_to_send += 1

                #écoute des ack
                try:
                    raw_ack, _ = sock.recvfrom(2048)
                    ptype, ack_seqnum, payload = decode_ack(raw_ack)
                    if ptype == PTYPE_ACK or ptype == PTYPE_SACK:
                        retries = 0
                        #avance la base
                        expected_base_seq = base % 2048
                        diff = (ack_seqnum - expected_base_seq) % 2048
                        
                        #si l'ecart est dans notre fenetre on le garde sinon c'est un ancien truc qui arrive en retard
                        if 0 < diff <= window_size:
                            base += diff
                        
                        if ptype == PTYPE_SACK and payload:
                            sack_seqnums = decode_sack_payload(payload)
                            print(f"SACK reçu (base: {ack_seqnum}) -> Paquets futurs validés : {sack_seqnums}", file=sys.stderr)
                            
                            for sq in sack_seqnums:
                                for i in range(base, min(base + window_size, total_chunks)):
                                    if (i % 2048) == sq:
                                        acked_indices.add(i)  #ne pas renvoyer
                                        break
                        else:
                            print(f"ACK reçu -> le client attend le seq {ack_seqnum}", file=sys.stderr)
                            
                except socket.timeout:
                    retries += 1
                    if retries > max_retries:
                        #permet de prevenir le cas ou on perd le dernier ack et que le serveur tourne dans le vide
                        print(f"Trop de timeouts consécutifs ({max_retries})", file=sys.stderr)
                        break
                    #si on recoit rien apres 0.5s, on recule et on renvoie
                    print("Timeout ! On renvoie uniquement les paquets de la fenêtre NON acquittés.", file=sys.stderr)
                    next_to_send = base
            
            
            sock.settimeout(None) #pour ecouter le prochain client
            print(f"Fichier envoyé pour un total de {len(payload)} bytes")
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
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--root", '-r',
        default=DEFAULT_DIRECTORY,
        help=f"Directory is the root folder from which the server retrieves the file requested by the client (default : {DEFAULT_DIRECTORY})"
    )

    parser.add_argument(
        'hostname',
        help= "Hostname being the name of the domain or IPv6 address on which the server listens to incoming client requests"
    )

    parser.add_argument(
        'port',
        type=int,
        help="Port being the UDP port number to which the server attaches"
    )

    args = parser.parse_args()
    
    result = create_server(args.hostname, args.port, args.root)
    
    if result != 0:
        sys.exit(1)

