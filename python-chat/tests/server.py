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
import argparse
import socket

import logging

import select

from ..utils import chatutils
from ..utils import serverutils

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, default='65535', metavar="port", help="host and port of running server")
    opt = parser.parse_args()

    # connection parameters
    srv_host = '0.0.0.0'  # socket.gethostbyname(socket.gethostname())
    srv_port = int(opt.port)

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
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
                    serverutils.process_message(data, sock, sock_list, client_list, srv_seq_number, viewers_connected,
                                                senders_connected)
        except:
            pass
        '''except KeyboardInterrupt:
            try:
                serverutils.handle_shutdown(client_list)
            except:
                log = "Oh no! Something very very messy just happened. Abort mission!"
                logger.error(log)
            finally:
                break'''
    srv_sock.close()
