#!/usr/bin/env python3
import asyncio
import sys

from messages import read, write, send_error, send_welcome
class ChatServer:

    def __init__(self, port, loop):
        self.connections = {}
        self.server = loop.run_until_complete(
                asyncio.start_server(
                    self.accept_connection, 'localhost', port, loop=loop))

    def broadcast(self, message, sender=''):
        for user, (reader, writer) in self.connections.items():
            if sender != user:
                write(writer, {'payload': message, 'sender': sender, 'type': 'msg'})

    @asyncio.coroutine
    def prompt_username(self, reader, writer):
        data = yield from read(reader)
        if not data:
            return None
        assert data['type'] == 'name'
        username = data['payload']
        if not username or ' ' in username or username in self.connections:
            send_error(writer, 'invalid username')
            return None
        else:
            send_welcome(writer)
            self.connections[username] = (reader, writer)
            return username

    def send_online_users(self, user):
        users = [name for name in self.connections.keys() if name != user]
        if not users:
            payload = ''
        else:
            payload = ' '.join(users)
        writer = self.connections[user][1]
        write(writer, {'type': 'users', 'sender': '', 'payload': payload})

    @asyncio.coroutine
    def handle_connection(self, username, reader):
        while True:
            data = yield from read(reader)
            if not data:
                del self.connections[username]
                return None
            print('{} > {}'.format(username, data['type'], data['payload']))
            if data['type'] == 'msg':
                self.broadcast(data['payload'], username)
            elif data['type'] == 'users':
                self.send_online_users(username)

    @asyncio.coroutine
    def accept_connection(self, reader, writer):
        username = (yield from self.prompt_username(reader, writer))
        if username is not None:
            print('user joined: {}'.format(username))
            self.broadcast('User <{}> has joined the room'.format(username))
            self.send_online_users(username)
            yield from self.handle_connection(username, reader)
            self.broadcast('User <{}> has left the room'.format(username))
            print('user left: {}'.format(username))
        yield from writer.drain()


def main(argv):
    print('<< Server starting >>')
    loop = asyncio.get_event_loop()
    server = ChatServer(32311, loop)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print('<< Keyboard interrupt >>')
    finally:
        print('<< Shutting down >>')
        loop.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
