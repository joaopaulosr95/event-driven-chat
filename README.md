# python-chat

This module was built for Python 2.7, compatibility for Python 3 is not warranted


## known issues
|Issue|Fix|
|---|---|
|When an invalid ID is provided the system crashes.|When dettaching a client, the method in charge should remove the client itself from the client list instead of just setting its id and socket values to None|


## usage

- Start the server

		python server.py <port>


- Start a viewer client

		python client.py [host:port] viewer


- Start a sender client

		python client.py [host:port] sender [--viewer_id <viewer_id>]
