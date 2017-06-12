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
import random
import select
import socket
import struct

from ..utils import chatutils
from ..utils import serverutils

# Logging setup
logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s]%(message)s")

if __name__ == "__main__":
    logger = logging.getLogger(__name__)

    # connection parameters
    srv_host = socket.gethostbyname(socket.gethostname())
    srv_port = 65535

    srv_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv_sock.setblocking(0)
    srv_sock.bind((srv_host, srv_port))
    srv_sock.listen(chatutils.MAX_CLIENTS)
    logger.info("Server running at %s:%d", srv_host, srv_port)

    serverutils.server(srv_sock)
    srv_sock.close()
