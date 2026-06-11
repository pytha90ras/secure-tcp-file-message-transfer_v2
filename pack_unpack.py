from struct import pack, unpack


def Pack(msg, name=None, Data=None):
    msg = pack('>I', len(msg)) + msg
    if name is None:
        return msg
    name = pack('>I', len(name)) + name
    Data = pack('>I', len(Data)) + Data
    return msg, name, Data


def safe_send(sock, packed_msg, stop_event):
    if stop_event.is_set():
        return False
    try:
        sock.send(packed_msg)
        return True
    except (ConnectionResetError, OSError):
        stop_event.set()
        return False


def recv_exact_unpack(me, stop_event):
    data = bytearray()
    while len(data) < 4:
        if stop_event.is_set():
            return
        packet = b''
        try:
            packet = me.recv(4 - len(data))
        except TimeoutError:
            continue
        except (ConnectionResetError, OSError):
            stop_event.set()
            return
        if not packet:
            break
        data.extend(packet)
    if not data:
        return
    msglen = unpack('>I', data)[0]
    msg = bytearray()
    while len(msg) < msglen:
        if stop_event.is_set():
            return
        chunk = b''
        try:
            chunk = me.recv(msglen - len(msg))
        except TimeoutError:
            pass
        except (ConnectionResetError, OSError):
            stop_event.set()
            return
        if not chunk:
            return
        msg.extend(chunk)
    return bytes(msg)
