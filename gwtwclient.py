#!/usr/bin/env python3
import asyncio
from datetime import datetime
import logging

import urwid

from messages import read, write, welcome


class LogFrame(urwid.Widget):
    """A basic text box to show the backlog of messages."""
    _sizing = frozenset(['box'])

    def __init__(self, username):
        super().__init__()
        self.username = username
        self.text_widget = urwid.Text('')  # + '\n FILLER'*70)

    def render(self, size, focus=False):
        """Draw the log text, aligned towards the bottom."""
        w, h = size
        log_canvas = self.text_widget.render((w,))
        log_height = log_canvas.rows()
        if log_height < h:
            return urwid.CanvasCombine([
                    (urwid.SolidCanvas(' ', w, h-log_height), None, False),
                    (log_canvas, None, False)])
        # elif log_height > h:
        #     canvas = urwid.CompositeCanvas(log_canvas)
        #     canvas.trim(log_height-h)
        #     return canvas
        # elif log_height == h:
        return log_canvas

    def add_message(self, msgtext, sender=None):
        if sender is None:
            sender = self.username
        if sender:
            text = '{}: {}'.format(sender, msgtext)
        else:
            text = '<server> {}'.format(msgtext)
        self.add_line(text)

    def add_line(self, text):
        timestamp = datetime.now().strftime('%H:%M:%S')
        old_text = self.text_widget.get_text()[0]
        new_text = '{}  {}'.format(timestamp, text)
        if old_text:
            new_text = '{}\n{}'.format(old_text, new_text)
        self.text_widget.set_text(new_text)

    def add_lines(self, textlist):
        timestamp = datetime.now().strftime('%H:%M:%S')
        old_text = self.text_widget.get_text()[0]
        new_text = '\n'.join('{}  {}'.format(timestamp, t) for t in textlist)
        if old_text:
            new_text = '{}\n{}'.format(old_text, new_text)
        self.text_widget.set_text(new_text)

class InputField(urwid.Edit):

    def keypress(self, size, key):
        if key != 'enter':
            return super().keypress(size, key)
        if self.edit_text.startswith('/') and not self.edit_text.startswith('//'):
            urwid.emit_signal(self, 'cmd', self.edit_text)
        else:
            urwid.emit_signal(self, 'msg', self.edit_text)
        self.set_edit_text('')


class Connection:
    def __init__(self, username):
        self.username = username
        self.writer = None
        self.alive = True

    def send_message(self, text, type='msg'):
        if self.writer:
            data = {'type': type, 'sender': self.username, 'payload': text}
            write(self.writer, data)

    def close_connection(self):
        self.writer.close()
        self.reader.feed_data(b'')

    @asyncio.coroutine
    def handle(self, loop):
        self.reader, self.writer = yield from asyncio.open_connection('localhost', 32311, loop=loop)
        self.send_message(self.username, type='name')
        reply = yield from read(self.reader)
        if not welcome(reply):
            urwid.emit_signal(self, 'print', 'Invalid username: {}'.format(repr(reply)))
            yield from asyncio.sleep(2)
            self.writer.close()
            return
        while True:
            data = yield from read(self.reader)
            if not data:
                break
            if data['type'] == 'msg':
                urwid.emit_signal(self, 'msg', data['payload'], data['sender'])
            elif data['type'] == 'users':
                urwid.emit_signal(self, 'users', data['payload'])


class Client:
    def __init__(self, username):
        self.username = username
        self.connection = Connection(username)
        self.log = LogFrame(username)
        self.input_field = InputField(' {} > '.format(username), wrap='clip')
        self.frame = urwid.Frame(self.log, footer=self.input_field)
        self.frame.focus_position = 'footer'
        self.connect_signals(self.connection, self.log, self.input_field)

    def connect_signals(self, connection, log, input_field):
        signals = [
            (input_field, 'msg', log.add_message),
            (input_field, 'msg', connection.send_message),
            (input_field, 'cmd', self.parse_command),
            (input_field, 'print', log.add_line),
            (connection, 'msg', log.add_message),
            (connection, 'users', self.list_users),
            (connection, 'print', log.add_line)
        ]
        def get_signal_names(target):
            return list({name for obj, name, _ in signals if obj == target})
        urwid.register_signal(InputField, get_signal_names(input_field))
        urwid.register_signal(Connection, get_signal_names(connection))
        for signal in signals:
            urwid.connect_signal(*signal)

    def list_users(self, users):
        self.log.add_message('Users online: {}'.format(users), sender='')

    def parse_command(self, text):
        if text == '/quit':
            self.connection.close_connection()
        elif text == '/help':
            self.log.add_lines(['>> /quit - exit the program',
                                '>> /help - print this'])
        elif text == '/names':
            self.connection.send_message('', type='users')

def main(username):
    # Logging
    logging.basicConfig(filename='error.log')
    def exit_program(future):
        if future.exception():
            formatter = logging.Formatter()
            e = future.exception()
            exc = (type(e), e, e.__traceback__)
            error = formatter.formatException(exc)
            logging.error(error)
        raise urwid.ExitMainLoop()
    # Init
    client = Client(username)
    asyncio_loop = asyncio.get_event_loop()
    asyncio_loop.set_debug(True)
    connection = asyncio_loop.create_task(client.connection.handle(asyncio_loop))
    connection.add_done_callback(exit_program)
    loop = urwid.MainLoop(client.frame,
                          event_loop=urwid.AsyncioEventLoop(loop=asyncio_loop),
                          handle_mouse=False)
    loop.screen.set_terminal_properties(colors=256)
    try:
        loop.run()
    except KeyboardInterrupt:
        print('keyboard interrupt')


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('username')
    args = parser.parse_args()
    main(args.username)
