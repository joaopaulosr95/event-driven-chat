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
"""

import logging
import select
import socket
import struct
import sys

from pythonchat import chatutils

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(message)s")

"""
| ===================================================================
| viewer: runs a viewer client
| ===================================================================
"""

def viewer(host, port):
    logger = logging.getLogger(__name__)
    viewer_id = 0
    viewer_seq_number = 0
    viewer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to remote host
    try:
        viewer_sock.connect((host, port))
    except:
        logger.error('Unable to connect')
        sys.exit()

    chatutils.deliver_message(viewer_sock, chatutils.MESSAGE_TYPES["OI"], 0, chatutils.SRV_ID, viewer_seq_number)
    while True:
        try:
            data = viewer_sock.recv(chatutils.HEADER_SIZE)
            message_type, from_id, sender_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)
            break
        except:
            continue
    viewer_seq_number += 1
    logger.info("Just received id #%d" % sender_id)

    while True:
        try:
            data = viewer_sock.recv(chatutils.HEADER_SIZE)
            message_type_id, client_from_id, client_to_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)
            if message_type_id == chatutils.MESSAGE_TYPES["MSG"]:
                chatutils.deliver_message(viewer_sock, chatutils.MESSAGE_TYPES["OK"], viewer_id, client_from_id,
                                          seq_number)

                msg_length = struct.unpack("!H", viewer_sock.recv(2))[0]
                msg_contents = viewer_sock.recv(msg_length)

                if client_to_id == 0:
                    logger.info("BROADCAST: %s" % msg_contents)
                elif client_from_id == chatutils.SRV_ID:
                    logger.info("Server says: %s" % msg_contents)
                else:
                    logger.info("#%d says: %s" % (client_from_id, msg_contents))

            elif message_type_id == chatutils.MESSAGE_TYPES["CLIST"]:
                chatutils.deliver_message(viewer_sock, chatutils.MESSAGE_TYPES["OK"], viewer_id, chatutils.SRV_ID,
                                          seq_number)

                clist_size = struct.unpack("!H", viewer_sock.recv(2))[0]
                clist = ''
                for i in range(clist_size):
                    clist = clist + str(struct.unpack("!H", viewer_sock.recv(2))[0])
                    if i < clist_size - 1:
                        clist = clist + ', '

                logger.info("Client list (%d connected clients)" % clist_size)
                print(clist)

            elif message_type_id == chatutils.MESSAGE_TYPES["FLW"]:
                chatutils.deliver_message(viewer_sock, chatutils.MESSAGE_TYPES["OK"], viewer_id, chatutils.SRV_ID,
                                          seq_number)
                break
        except KeyboardInterrupt:
            chatutils.deliver_message(viewer_sock, chatutils.MESSAGE_TYPES["FLW"], viewer_id, chatutils.SRV_ID,
                                      viewer_seq_number)
            viewer_seq_number += 1
            break

    viewer_sock.close()

"""
| ===================================================================
| helper: show usage options for cli
| ===================================================================
"""

def helper():
    print('How to interact:\n'
          + 'CID#message: sends "message" to viewer #CID. If CID = 0, sends a broadcast\n'
          + 'CID#CREQ: prints a list of clients to terminal #CID. If CID = 0, sends a broadcast\n'
          + 'Ctrl-C: leave chat')

"""
| ===================================================================
| sender: runs a sender client
| ===================================================================
"""

def sender(host, port, viewer_id=None):
    logger = logging.getLogger(__name__)
    sender_seq_number = 0
    sender_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # connect to remote host
    try:
        sender_sock.connect((host, port))
    except:
        logger.error('Unable to connect')
        sys.exit()

    chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["OI"], viewer_id if viewer_id else 9999,
                              chatutils.SRV_ID, sender_seq_number)
    while True:
        try:
            data = sender_sock.recv(chatutils.HEADER_SIZE)
            message_type, from_id, sender_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)
            break
        except:
            continue
    sender_seq_number += 1
    logger.info("Just received id #%d" % sender_id)

    def flush():
        sys.stdout.write('Press help to see commands available\nMe (#%d): ' % sender_id)
        sys.stdout.flush()

    flush()
    sock_list = [sender_sock, sys.stdin]
    while True:
        try:
            # Get the list sockets which are readable
            readable, _, _ = select.select(sock_list, [], [], 0)

            for sock in readable:
                if sock == sender_sock:
                    data = sock.recv(chatutils.HEADER_SIZE)
                    message_type, from_id, to_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)
                    if message_type == chatutils.MESSAGE_TYPES["FLW"]:
                        chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["OK"], sender_id, from_id,
                                                  seq_number)
                        sys.exit(1)
                else:
                    user_input = raw_input()
                    if user_input.lower() == "help":
                        helper()
                    elif user_input.lower() == 'exit':
                        chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["FLW"], sender_id,
                                                  chatutils.SRV_ID, sender_seq_number)
                        sys.exit(2)
                    else:
                        message_split = user_input.split("#")
                        if len(message_split) != 2:
                            logger.warning("Incorrect message format, type again")
                        else:
                            destination_id, message_contents = message_split
                            destination_id = int(destination_id)
                            if message_contents.lower() == "creq":
                                chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["CREQ"], sender_id,
                                                          int(destination_id), sender_seq_number)
                                sender_seq_number += 1

                            elif len(message_contents) >= chatutils.MAX_MSG_LEN:
                                logger.warning("Cannot read more than %d characters, try again with less amount",
                                               chatutils.MAX_MSG_LEN)
                            else:
                                chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["MSG"], sender_id,
                                                          int(destination_id), sender_seq_number, len(message_contents),
                                                          message_contents)
                                sender_seq_number += 1
                    flush()
        except KeyboardInterrupt:
            chatutils.deliver_message(sender_sock, chatutils.MESSAGE_TYPES["FLW"], sender_id, chatutils.SRV_ID,
                                      sender_seq_number)
            sender_seq_number += 1
            break

    sender_sock.close()
