from socket import socket
from threading import Thread, Event
from sys import exit
from os import environ

try:
    import pack_unpack
except ModuleNotFoundError:
    print("Incomplete dependencies")
    exit(1)
port = int(environ.get('PORT', 9999))
central_server = socket()
central_server.bind(('0.0.0.0', port))
central_server.listen(50)
major_event = Event()
connections = {}


def handle_client(client_obj, ip_port, my_event):
    while not my_event.is_set():
        if not pack_unpack.safe_send(client_obj, pack_unpack.Pack(b'--# '), my_event):
            return
        command = pack_unpack.recv_exact_unpack(client_obj, my_event)
        if command is None:
            continue
        command = command.decode()

        if command.lower() == 'connect':
            if not pack_unpack.safe_send(client_obj, pack_unpack.Pack(b'Connect to: '), my_event):
                return
            name = pack_unpack.recv_exact_unpack(client_obj, my_event)
            if name is None:
                continue
            name = name.decode()
            matched_key = None
            for key, val in connections.items():
                if name.lower() == val[1]:
                    matched_key = key
                    break
            if matched_key is None:
                pack_unpack.safe_send(client_obj, pack_unpack.Pack(b'Friend offline, try again later\n'), my_event)
                continue
            
            val = connections[matched_key]
            peer_obj = val[2]
            peer_event = val[3]

            port_event = Event()
            peer_event.set()
            pack_unpack.safe_send(peer_obj, pack_unpack.Pack(f'{ip_port[0]}:{ip_port[1]}:client'.encode()), port_event)
            pack_unpack.safe_send(client_obj, pack_unpack.Pack(f'{matched_key}:{val[0]}:server'.encode()), my_event)

            c1_port = pack_unpack.recv_exact_unpack(client_obj, my_event)
            print('Received client 1 port')
            c2_port = pack_unpack.recv_exact_unpack(peer_obj, port_event)
            print('Both ports received')

            if c1_port:
                pack_unpack.safe_send(peer_obj, pack_unpack.Pack(c1_port), port_event)
            if c2_port:
                pack_unpack.safe_send(client_obj, pack_unpack.Pack(c2_port), my_event)
            print('Cross-forwarded ports')

            try:
                client_obj.close()
            except OSError:
                pass
            try:
                peer_obj.close()
            except OSError:
                pass

            my_event.set()
            try:
                connections.pop(matched_key)
            except KeyError:
                pass
            try:
                connections.pop(ip_port[0])
            except KeyError:
                pass
            return

        elif command.lower() == 'disconnect':
            try:
                client_obj.close()
            except OSError:
                pass
            my_event.set()
            try:
                connections.pop(ip_port[0])
            except KeyError:
                pass
            return


def accept_conn(main_event):
    while not main_event.is_set():
        try:
            client, ip_port = central_server.accept()
            client.settimeout(2)
            print(f'Connected: {ip_port}')
            local_event = Event()
            local_event_for_recv = Event()
            name = pack_unpack.recv_exact_unpack(client, local_event_for_recv)
            if name is None:
                client.close()
                continue
            name = name.decode().lower()
            connections[ip_port[0]] = (ip_port[1], name, client, local_event)
            t = Thread(target=handle_client, args=(client, ip_port, local_event))
            t.start()
        except Exception as e:
            print(f'Accept error: {e}')
            continue


thread_main = Thread(target=accept_conn, args=(major_event,))
thread_main.start()
thread_main.join()
central_server.close()
