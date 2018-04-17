# python-chat

## known issues
|Issue|Fix|
|---|---|
|When an invalid ID is provided the system crashes.|When dettaching a client, the method in charge should remove the client itself from the client list instead of just setting its id and socket values to None|


## usage

- Start the server

		python -m tests.server <port>


- Start a viewer client

		python -m tests.client [host:port] viewer


- Start a sender client

		python -m tests.client [host:port] sender [--viewer_id <viewer_id>]
