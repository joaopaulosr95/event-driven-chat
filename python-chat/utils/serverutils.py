#!/usr/bin/env python
# coding=utf-8

"""
Copyright (c) 2017 
Gabriel Pacheco     <gabriel.pacheco@dcc.ufmg.br> 
Guilherme Sousa     <gadsousa@gmail.com>
Joao Paulo Bastos   <joaopaulosr95@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

==> Gabriel de Oliveira Campos Pacheco  <gabriel.pacheco@dcc.ufmg.br>   2013062898
==> Guilherme Augusto de Sousa          <gadsousa@gmail.com>            2013062944
==> Joao Paulo Sacchetto Ribeiro Bastos <joaopaulosr95@gmail.com>       2013073440
==> Trabalho pratico 2
==> 19-06-2017
"""
import logging
import socket
import struct
import random
import select
import chatutils

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s]%(message)s")

"""
| ===================================================================
| is_valid_client: checks if sock matches its client
| ===================================================================
"""

def is_valid_client(sock, client_list, client_id):
    invalid_client = False

    if client_id in range(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX):
        client = get_client_by_parameter(client_list, "viewer_id", client_id)
        if not client or not client["viewer_sock"] == sock:
            invalid_client = True

    elif client_id in range(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX):
        client = get_client_by_parameter(client_list, "sender_id", client_id)
        if not client or not client["sender_sock"] == sock:
            invalid_client = True
    return invalid_client

"""
| ===================================================================
| get_client_by_parameter: searches client by sender_id or viewer_id
| ===================================================================
"""

def get_client_by_parameter(client_list, parameter_key, parameter_val):
    for client in client_list:
        if client[parameter_key] == parameter_val:
            return client
    return None

"""
| ===================================================================
| clist: searches and sorts clients by id
| ===================================================================
"""

def clist(client_list):
    l = ["%d" % client["viewer_id"] for client in client_list if client["viewer_id"] is not None]
    l = l + ["%d" % client["sender_id"] for client in client_list if client["sender_id"] is not None]
    return l.sort()

"""
| ===================================================================
| broadcast: sends a message to all connected clients
| ===================================================================
"""

def broadcast(client_list, header, message_type, message):
    for client in client_list:
        if client["viewer_sock"] is not None:
            try:
                chatutils.deliver_message(client["viewer_sock"], header, message_type, len(message), message)
            except:
                pass

"""
| ===================================================================
| handle_shutdown: handles a CTRL-C from server shutting down clients
| ===================================================================
"""

def handle_shutdown(client_list):
    for client in client_list:
        if client["viewer_sock"] is not None:
            while True:
                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID, client["viewer_id"], chatutils.ERROR_FLAG)
                try:
                    chatutils.deliver_message(client["viewer_sock"], header)
                    answer = client["viewer_sock"].recv(chatutils.HEADER_SIZE)
                    message_type = struct.unpack(chatutils.HEADER_FORMAT, answer)[0]
                    if message_type == chatutils.MESSAGE_TYPES["OK"]:
                        break
                except:
                    pass
            client["viewer_id"], client["viewer_sock"] = None, None

        if client["sender_sock"] is not None:
            while True:
                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID, client["sender_id"], chatutils.ERROR_FLAG)
                try:
                    chatutils.deliver_message(client["sender_sock"], header)
                    answer = client["sender_sock"].recv(chatutils.HEADER_SIZE)
                    message_type = struct.unpack(chatutils.HEADER_FORMAT, answer)[0]
                    if message_type == chatutils.MESSAGE_TYPES["OK"]:
                        break
                except:
                    pass
            client["sender_id"], client["sender_sock"] = None, None

def server(port):
    logger = logging.getLogger(__name__)

    # connection parameters
    srv_host = socket.gethostbyname(socket.gethostname())  # localhost
    srv_port = port

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.setblocking(0)
    srv_sock.bind((srv_host, srv_port))
    srv_sock.listen(chatutils.MAX_CLIENTS)
    logger.info("Server running at %s:%d", srv_host, srv_port)

    viewers_connected = 0
    senders_connected = 0
    client_list = []
    sock_list = [srv_sock]
    srv_seq_number = 0

    while True:
        try:
            readable, _, _ = select.select(sock_list, [], [], 0)
            for sock in readable:

                # A new client has arrived
                if sock is srv_sock:
                    client, addr = srv_sock.accept()
                    sock_list.append(client)
                    log = "A new client (%s:%s) has just arrived" % (addr[0], addr[1])
                    logger.info(log)

                # A known client has something to say
                else:
                    data = sock.recv(chatutils.HEADER_SIZE)
                    message_type_id, client_from_id, client_to_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)

                    # This message is like a DHCP discover message: "Who can put me into the network?"
                    if message_type_id == chatutils.MESSAGE_TYPES["OI"]:

                        # Its a viewer
                        if client_from_id == 0 and viewers_connected < (chatutils.VIEWER_RANGE_MAX - chatutils.VIEWER_RANGE_MIN):

                            # Here we randomly find a id for new viewer client
                            while True:
                                viewer_id = random.randint(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX)
                                if not get_client_by_parameter(client_list, "viewer_id", viewer_id):
                                    client_list.append({"viewer_id": viewer_id, "viewer_sock": sock, "sender_id": None, "sender_sock": None})
                                    break

                            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, viewer_id, seq_number)
                            try:
                                chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                            except:
                                pass
                            viewers_connected += 1

                            log = "A new viewer has arrived, its id is #%d" % viewer_id
                            logger.info(log)
                            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, 0, srv_seq_number)
                            broadcast(client_list, header, chatutils.MESSAGE_TYPES["MSG"], log)
                            srv_seq_number += 1

                        # Its a sender
                        elif client_from_id != 0 and senders_connected < (chatutils.SENDER_RANGE_MAX - chatutils.SENDER_RANGE_MIN):

                            # Sender is not gonna attach itself to any viewer
                            if client_from_id not in range(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX):

                                # Here we randomly find a id for new sender client
                                while True:
                                    sender_id = random.randint(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX)
                                    if not get_client_by_parameter(client_list, "sender_id", sender_id):
                                        break
                                client_list.append({"viewer_id": None, "viewer_sock": None, "sender_id": sender_id, "sender_sock": sock})
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, sender_id, seq_number)
                                try:
                                    chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                                except:
                                    pass
                                senders_connected += 1

                                log = "A new sender has arrived, its id is #%d and its not attached to any viewer" % sender_id
                                logger.info(log)
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, 0, srv_seq_number)
                                broadcast(client_list, header, chatutils.MESSAGE_TYPES["MSG"], log)
                                srv_seq_number += 1

                            # Sender already has a predefined viewer
                            else:
                                viewer = get_client_by_parameter(client_list, "viewer_id", client_from_id)

                                # Viewer incorrect id
                                if viewer is None:
                                    logger.warning("Invalid id viewer provided in new sender's attempt")
                                    header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                                                       seq_number)
                                    try:
                                        chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["ERRO"])
                                    except:
                                        pass
                                else:

                                    # Here we randomly find a id for new sender client
                                    while True:
                                        sender_id = random.randint(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX)
                                        if not get_client_by_parameter(client_list, "sender_id", sender_id):
                                            break

                                    viewer["sender_id"] = sender_id
                                    viewer["sender_sock"] = sock
                                    senders_connected += 1

                                    header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, sender_id, seq_number)
                                    try:
                                        chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                                    except:
                                        pass

                                    log = "A new sender has arrived, its id is #%d and its attached to viewer #%d" % (sender_id,
                                                                                                                      viewer["viewer_id"])
                                    logger.info(log)
                                    header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, 0, seq_number)
                                    try:
                                        broadcast(client_list, header, chatutils.MESSAGE_TYPES["MSG"], log)
                                    except:
                                        pass

                        # ERROR
                        else:
                            ''' Possible error causes
                            - No more space for viewers or senders
                            - Sender provided a bad ID '''
                            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["ERRO"], client_from_id, client_to_id, seq_number)
                            chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["ERRO"])

                    elif message_type_id == chatutils.MESSAGE_TYPES["OK"] or message_type_id == chatutils.MESSAGE_TYPES["ERRO"] \
                            or message_type_id == chatutils.MESSAGE_TYPES["FLW"] or message_type_id == chatutils.MESSAGE_TYPES["MSG"] \
                            or message_type_id == chatutils.MESSAGE_TYPES["CREQ"]:

                        # Does the client sock match with proper id?
                        valid_from = True
                        '''if not is_valid_client(sock, client_list, client_from_id) and not client_to_id == chatutils.SRV_ID:
                            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id, seq_number)
                            try:
                                chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["ERRO"])
                            except:
                                pass
                            finally:
                                valid_from = False'''

                        valid_to = True
                        '''if not is_valid_client(sock, client_list, client_to_id) and not client_to_id == chatutils.SRV_ID:
                            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id, seq_number)
                            try:
                                chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["ERRO"])
                            except:
                                pass
                            finally:
                                valid_to = False'''

                        if valid_from and valid_to:

                            # The client wants to disconnect
                            if message_type_id == chatutils.MESSAGE_TYPES["FLW"]:

                                # Checks if client is viewer or sender
                                if client_from_id in range(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX):
                                    client = get_client_by_parameter(client_list, "sender_id", client_from_id)
                                    if client["viewer_sock"]:
                                        header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID, client["viewer_id"],
                                                                           srv_seq_number)
                                        try:
                                            chatutils.deliver_message(client["viewer_sock"], header, chatutils.MESSAGE_TYPES["FLW"])
                                        except:
                                            pass
                                        sock_list.remove(client["viewer_sock"])
                                        client["viewer_id"], client["viewer_sock"] = None, None
                                        viewers_connected -= 1

                                    header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)
                                    try:
                                        chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                                    except:
                                        pass
                                    sock_list.remove(sock)
                                    client["sender_id"], client["sender_sock"] = None, None
                                    senders_connected -= 1

                                elif client_from_id in range(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX):
                                    client = get_client_by_parameter(client_list, "viewer_id", client_from_id)
                                    sock_list.remove(sock)
                                    client["viewer_id"], client["viewer_sock"] = None, None
                                    viewers_connected -= 1

                                # If client isn't associated with no more ids and sockets, remove it from client_list
                                if client["viewer_id"] is None and client["viewer_sock"] is None \
                                        and client["sender_id"] is None and client["sender_sock"] is None:
                                    client_list.remove(client)

                            # The client just sent a message
                            elif message_type_id == chatutils.MESSAGE_TYPES["MSG"]:
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)
                                try:
                                    chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                                except:
                                    raise

                                msg_length = struct.unpack("!H", sock.recv(2))[0]
                                msg_contents = sock.recv(struct.calcsize(str(msg_length)+"s"))

                                # Its a broadcast
                                if client_to_id == 0:
                                    broadcast(client_list, data, chatutils.MESSAGE_TYPES["MSG"], msg_contents)

                                # Message has a specific destination
                                else:
                                    # Destination it's a sender or a viewer?
                                    if client_to_id in range(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX):
                                        client_to = get_client_by_parameter(client_list, "viewer_id", client_to_id)
                                    elif client_to_id in range(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX):
                                        client_to = get_client_by_parameter(client_list, "sender_id", client_to_id)

                                    try:
                                        chatutils.deliver_message(client_to["viewer_sock"], data, chatutils.MESSAGE_TYPES["MSG"],
                                                                  msg_length, msg_contents)
                                    except:
                                        # TODO: better error handling, but which?
                                        pass

                            elif message_type_id == chatutils.MESSAGE_TYPES["CREQ"]:
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)
                                try:
                                    chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES["OK"])
                                except:
                                    raise

                                clist = clist(client_list)
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["CLIST"], chatutils.SRV_ID, client_to_id, srv_seq_number)

                                # Broadcast CLIST
                                if client_to_id == 0:
                                    broadcast(client_list, header, chatutils.MESSAGE_TYPES["CLIST"], clist)
                                else:
                                    client_to = get_client_by_parameter(client_list, "viewer_id", client_to_id)
                                    try:
                                        chatutils.deliver_message(client_to["viewer_sock"], data, chatutils.MESSAGE_TYPES["CLIST"], clist)
                                    except:
                                        # TODO: better error handling, but which?
                                        pass
                                srv_seq_number += 1
                        else:
                            logger.error("Origin or destination don't match")
        except KeyboardInterrupt:
            try:
                handle_shutdown(client_list)
            except:
                log = "Oh no! Something very very messy just happened. Abort mission!"
                logger.error(log)
            finally:
                break
