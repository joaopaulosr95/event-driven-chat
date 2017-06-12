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
import socket
import struct
import sys
import select
import logging
from optparse import OptionParser
import chatutils

"""
| ===================================================================
| vararg_callback: takes a variable number of arguments
| ===================================================================
"""

def vararg_callback(option, opt_str, value, parser):
    assert value is None
    value = []

    def floatable(str):
        try:
            float(str)
            return True
        except ValueError:
            return False

    for arg in parser.rargs:
        # stop on --foo like options
        if arg[:2] == "--" and len(arg) > 2:
            break
        # stop on -a, but not on -3 or -3.0
        if arg[:1] == "-" and len(arg) > 1 and not floatable(arg):
            break
        value.append(arg)

    del parser.rargs[:len(value)]
    setattr(parser.values, option.dest, value)

"""
| ===================================================================
| process_opt: parsing command-line options
| ===================================================================
"""

def process_opt():
    usage = "usage: %prog files\n"
    parser = OptionParser(usage=usage)
    parser.add_option("-s", "--sender", dest="sender", action="callback", callback=vararg_callback, help="sender params")
    parser.add_option("-v", "--viewer", dest="viewer", help="viewer params", nargs=1)
    opt, files = parser.parse_args()
    return opt

"""
| ===================================================================
| viewer: runs a viewer client
| ===================================================================
"""

def viewer():
    pass

"""
| ===================================================================
| helper: show usage options for cli
| ===================================================================
"""

def helper():
    print('How to interact:\n'
          + 'CID#hello world: sends "hello world" to viewer #CID. If CID = 0, sends a broadcast\n'
          + 'CID#CREQ: \tprints a list of clients to terminal #CID. If CID = 0, sends a broadcast')

"""
| ===================================================================
| sender: runs a sender client
| ===================================================================
"""

def sender(viewer_id=None):
    logger = logging.getLogger(__name__)

    sender_id = 0
    sender_seq_number = 0
    sender_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sender_sock.connect((host, port))

    initial_message = chatutils.prepare_message(chatutils.MESSAGE_TYPES["OI"], viewer_id if viewer_id else 0, chatutils.SRV_ID, sender_seq_number)
    chatutils.deliver_message(sender_sock, initial_message, chatutils.MESSAGE_TYPES["OI"])

    while True:
        try:
            data = sender_sock.recv(chatutils.HEADER_SIZE)
            message_type, from_id, sender_id, seq_number = struct.unpack(chatutils.HEADER_FORMAT, data)
            break
        except:
            continue

    print("Just received id #%d" % sender_id)

    sock_list = [sender_sock, sys.stdin]
    while True:
        try:
            # Get the list sockets which are readable
            readable, _, _ = select.select(sock_list, [], [], 0)

            for sock in readable:
                if sock == sender_sock:
                    data = sock.recv(chatutils.HEADER_SIZE)
                    message_type, from_id, to_id, _ = struct.unpack(chatutils.HEADER_FORMAT, data)
                    if message_type == chatutils.MESSAGE_TYPES["OK"]:
                        sender_seq_number += 1

                    # sys.stdout.write(data)
                    sys.stdout.write('You can type help anytime to see commands available\n[Me (#%d)] ' % sender_id)
                    sys.stdout.flush()

                else:
                    user_input = input()
                    if user_input == "help":
                        helper()
                    else:
                        message_split = user_input.split("#")
                        if len(message_split) != 2:
                            logger.warning("Incorrect message format, type again")

                        else:
                            destination_id, message_contents = message_split
                            if message_contents.lower() == "creq":
                                header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["CREQ"], sender_id, destination_id, seq_number)
                                # TODO AGUARDAR OK

                            elif len(message_contents) >= chatutils.MAX_MSG_LEN:
                                logging.error("Cannot read more than %d characters, try again with less amount", chatutils.MAX_BUFFER)
                                helper()
                            else:
                                chatutils.deliver_message(sock, header, chatutils.MESSAGE_TYPES[""], message_contents)
                                message = sock.recv(chatutils.HEADER_SIZE)
                                print(struct.unpack(chatutils.HEADER_FORMAT, message))

                                # sys.stdout.write(data)
                                sys.stdout.write('You can type help anytime to see commands available\n[Me (#%d)] ' % sender_id)
                                sys.stdout.flush()
        except KeyboardInterrupt:
            header = chatutils.prepare_message(chatutils.MESSAGE_TYPES["FLW"], sender_id, chatutils.SRV_ID, sender_seq_number)
            chatutils.deliver_message(sender_sock, header, chatutils.MESSAGE_TYPES["FLW"])
            break

    sender_sock.close()
