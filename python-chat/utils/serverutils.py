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
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(message)s")

"""
| ===================================================================
| get_client_type: returns type of client based on id
| ===================================================================
"""

def get_client_type(client_id):
    if client_id in range(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX):
        return "viewer"
    elif client_id in range(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX):
        return "sender"
    return None

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

def get_clist(client_list):
    clist = ''
    clist_len = 0
    for client in client_list:
        if client["viewer_id"]:
            clist = clist + struct.pack("!H", client["viewer_id"])
            clist_len += 1
        if client["sender_id"]:
            clist = clist + struct.pack("!H", client["sender_id"])
            clist_len += 1
    return clist, clist_len

"""
| ===================================================================
| broadcast: sends a message to all connected clients
| ===================================================================
"""

def broadcast(client_list, message_type, from_id, seq_number, message):
    header = struct.pack(chatutils.HEADER_FORMAT, type, from_id, 0, seq_number)

    for client in client_list:
        if client["viewer_sock"] is not None:
            chatutils.deliver_message(client["viewer_sock"], header, message_type, len(message), message)
        if client["sender_sock"] is not None:
            chatutils.deliver_message(client["sender_sock"], header, message_type, len(message), message)

"""
| ===================================================================
| handle_shutdown: handles a CTRL-C from server shutting down clients
| ===================================================================
"""

def handle_shutdown(client_list):
    for client in client_list:
        if client["viewer_sock"] is not None:
            while True:
                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID,
                                                   client["viewer_id"], chatutils.ERROR_FLAG)
                chatutils.deliver_message(client["viewer_sock"], header)
                try:
                    answer = client["viewer_sock"].recv(chatutils.HEADER_SIZE)
                    message_type = struct.unpack(chatutils.HEADER_FORMAT, answer)[0]
                    if message_type == chatutils.MESSAGE_TYPES["OK"]:
                        break
                except:
                    raise
            dettach_client(client, "viewer")

        if client["sender_sock"] is not None:
            while True:
                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID,
                                                   client["sender_id"], chatutils.ERROR_FLAG)
                chatutils.deliver_message(client["sender_sock"], header)
                try:
                    answer = client["sender_sock"].recv(chatutils.HEADER_SIZE)
                    message_type = struct.unpack(chatutils.HEADER_FORMAT, answer)[0]
                    if message_type == chatutils.MESSAGE_TYPES["OK"]:
                        break
                except:
                    raise
            dettach_client(client, "sender")

        if not client["viewer_sock"] and not client["sender_sock"]:
            client_list.remove(client)

"""
| ===================================================================
| attach_client: randomly finds an id for new client
| ===================================================================
"""

def attach_client(client_list, client_type):
    while True:
        if client_type == "viewer":
            client_id = random.randint(chatutils.VIEWER_RANGE_MIN, chatutils.VIEWER_RANGE_MAX)
        else:
            client_id = random.randint(chatutils.SENDER_RANGE_MIN, chatutils.SENDER_RANGE_MAX)

        if not get_client_by_parameter(client_list, client_type + "_id", client_id):
            return client_id
        else:
            continue

"""
| ===================================================================
| dettach_client: clears client information based on type
| ===================================================================
"""

def dettach_client(client, client_type):
    client[client_type + "_id"], client[client_type + "_sock"] = None, None

"""
| ===================================================================
| is_valid_client: checks if sock matches its client
| ===================================================================
"""

def is_valid_client(sock, client_list, client_id):
    client_type = get_client_type(client_id)
    if client_type == 'viewer' or client_type == 'sender':
        client = get_client_by_parameter(client_list, client_type + "_id", client_id)
        if not client or not client[client_type + "_sock"] == sock:
            return False
        else:
            return True
    else:
        return False

"""
| ===================================================================
| validate_peers: checks if from and to clients are known and correct
| ===================================================================
"""

def validate_peers(client_list, sock, client_from_id, client_to_id):
    valid_from = True
    if client_from_id != chatutils.SRV_ID and not is_valid_client(sock, client_list, client_from_id):
        valid_from = False

    valid_to = True
    if client_to_id != chatutils.SRV_ID and not is_valid_client(sock, client_list, client_to_id):
        valid_to = False

    return valid_from and valid_to

"""
| ===================================================================
| process_message: processes a received message
| ===================================================================
"""

def process_message(data, sock, sock_list, client_list, srv_seq_number, viewers_connected=0, senders_connected=0):
    logger = logging.getLogger(__name__)
    message_type_id, client_from_id, client_to_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)

    # This message is like a DHCP discover message: "Who can put me into the network?"
    if message_type_id == chatutils.MESSAGE_TYPES["OI"]:
        if client_to_id == chatutils.SRV_ID:

            # Its a viewer
            if client_from_id == 0 and viewers_connected < (chatutils.VIEWER_RANGE_MAX - chatutils.VIEWER_RANGE_MIN):
                viewer_id = attach_client(client_list, "viewer")
                client_list.append(
                    {"viewer_id": viewer_id, "viewer_sock": sock, "sender_id": None, "sender_sock": None})

                chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, viewer_id, seq_number)
                log = "A new viewer has arrived, its id is #%d" % viewer_id
                logger.info(log)
                broadcast(client_list, chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, srv_seq_number, log)
                srv_seq_number += 1
                viewers_connected += 1

            # Its a sender
            elif client_from_id != 0 and senders_connected < (chatutils.SENDER_RANGE_MAX - chatutils.SENDER_RANGE_MIN):

                # Sender is not gonna attach itself to any viewer
                if get_client_type(client_from_id) is not 'viewer':
                    sender_id = attach_client(client_list, "sender")
                    client_list.append(
                        {"viewer_id": None, "viewer_sock": None, "sender_id": sender_id, "sender_sock": sock})

                    chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, sender_id,
                                              seq_number)
                    log = "A new sender has arrived, its id is #%d and its not attached to any viewer" % sender_id
                    logger.info(log)
                    broadcast(client_list, chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, srv_seq_number, log)
                    srv_seq_number += 1
                    senders_connected += 1

                # Sender already has a predefined viewer
                else:
                    viewer = get_client_by_parameter(client_list, "viewer_id", client_from_id)

                    # Viewer incorrect id
                    if viewer is None:
                        chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID,
                                                  client_from_id, seq_number)

                        log = "Invalid id viewer provided in new sender's attempt"
                        logger.warning(log)
                    else:
                        sender_id = attach_client(client_list, "sender")
                        viewer["sender_id"] = sender_id
                        viewer["sender_sock"] = sock

                        chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, sender_id,
                                                  seq_number)
                        log = "A new sender has arrived, its id is #%d and its attached to viewer #%d" % (
                            sender_id, viewer["viewer_id"])
                        logger.info(log)
                        broadcast(client_list, chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, seq_number, log)
                        srv_seq_number += 1
                        senders_connected += 1
        else:
            ''' Possible error causes
            - No more space for viewers or senders
            - Sender provided a bad ID '''
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                      seq_number)

    # The client wants to disconnect
    elif message_type_id == chatutils.MESSAGE_TYPES["FLW"]:

        if client_to_id == chatutils.SRV_ID and is_valid_client(sock, client_list, client_from_id):
            client_type = get_client_type(client_from_id)
            client = get_client_by_parameter(client_list, client_type + "_id", client_from_id)

            # Checks if client is viewer or sender
            if client_type == 'sender':
                if client["viewer_sock"]:
                    chatutils.deliver_message(client["viewer_sock"], chatutils.MESSAGE_TYPES["FLW"], chatutils.SRV_ID,
                                              client["viewer_id"], srv_seq_number)
                    log = "Client #%d left" % client_from_id
                    logger.info(log)

                    sock_list.remove(client["viewer_sock"])
                    dettach_client(client, "viewer")
                    viewers_connected -= 1
                    srv_seq_number += 1

                senders_connected -= 1

            elif client_type == 'viewer':
                viewers_connected -= 1

            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)
            log = "Client #%d left" % client_from_id
            logger.info(log)
            broadcast(client_list, chatutils.MESSAGE_TYPES["MSG"], chatutils.SRV_ID, srv_seq_number, log)
            srv_seq_number += 1

            dettach_client(client, client_type)
            sock_list.remove(sock)
            sock.close()

            # If client isn't associated with no more ids and sockets, remove it from client_list
            if client["viewer_id"] is None and client["viewer_sock"] is None \
                    and client["sender_id"] is None and client["sender_sock"] is None:
                client_list.remove(client)
        else:
            ''' Possible error causes
            - Invalid client_from_id '''
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                      seq_number)

    # The client just sent a message
    elif message_type_id == chatutils.MESSAGE_TYPES["MSG"]:

        if is_valid_client(sock, client_list, client_from_id):
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)
            message_len = struct.unpack("!H", sock.recv(2))[0]
            message = sock.recv(message_len)

            if client_to_id == chatutils.SRV_ID:
                logger.info(message)

            # Its a broadcast
            elif client_to_id == 0:
                broadcast(client_list, chatutils.MESSAGE_TYPES["MSG"], client_from_id, srv_seq_number, message)
                srv_seq_number += 1

            else:
                client_type = get_client_type(client_to_id)
                client_to = get_client_by_parameter(client_list, client_type + "_id", client_to_id)
                if client_to:
                    chatutils.deliver_message(client_to[client_type + "_sock"], data, chatutils.MESSAGE_TYPES["MSG"],
                                              message_len, message)
                else:
                    chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                              seq_number)
        else:
            log = "client_from_id #%d does not match expected id behind socket" % client_from_id
            logger.error(log)
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                      seq_number)

    # The client asked for a list of clients
    elif message_type_id == chatutils.MESSAGE_TYPES["CREQ"]:
        if client_to_id == chatutils.SRV_ID and is_valid_client(sock, client_list, client_from_id):
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["OK"], chatutils.SRV_ID, client_from_id, seq_number)

            clist, clist_len = get_clist(client_list)

            # Broadcast CLIST
            if client_to_id == 0:
                broadcast(client_list, chatutils.MESSAGE_TYPES["CLIST"], chatutils.SRV_ID, srv_seq_number, clist)
            else:
                client_to = get_client_by_parameter(client_list, "viewer_id", client_to_id)
                chatutils.deliver_message(client_to["viewer_sock"], data, chatutils.MESSAGE_TYPES["CLIST"], clist)
            srv_seq_number += 1
        else:
            ''' Possible error causes
            - Invalid client_from_id
            - client_to_id is not SRV_ID '''
            chatutils.deliver_message(sock, chatutils.MESSAGE_TYPES["ERRO"], chatutils.SRV_ID, client_from_id,
                                      seq_number)
