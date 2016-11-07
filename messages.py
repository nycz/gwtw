"""
A standardized message type for the chat protocol.

Structure:
TYPE SENDER PAYLOAD

Types:
msg - normal message
users - a list of all current users
welcome - the client has been accepted
error - something blew up
join - a user joined
part - a user left
"""
import asyncio


@asyncio.coroutine
def read(reader):
    data = (yield from reader.readline()).decode('utf-8')
    if not data:
        return None
    type_, sender, payload = data.rstrip('\n').split(' ', 2)
    return {'type': type_, 'sender': sender, 'payload': payload}

def write(writer, message):
    _write(writer, '{type} {sender} {payload}'.format(**message))

def send_error(writer, error):
    _write(writer, '{} {} {}'.format('error', '', error))

def send_welcome(writer):
    _write(writer, '{} {} {}'.format('welcome', '', ''))


def _write(writer, text):
    writer.write((text + '\n').encode('utf-8'))


def welcome(message):
    return message['type'] == 'welcome'
