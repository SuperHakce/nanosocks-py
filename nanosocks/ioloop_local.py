import socket
import errno
import logging

from nanosocks.core.ioloop import IOLoop
from nanosocks.core.iostream import IOStream
from nanosocks.core.iostream_mixup import IOStreamMixup

from nanosocks import config

class RelayHandler(object):

  server_host, server_port = config.server_host, config.server_port
  
  def __init__(self, conn_fd, addr):
    self.a_addr = addr
    self.a_stream = IOStream(conn_fd)
    logging.debug("new conn: {}:{}".format(addr[0], addr[1]))
    self.b_addr = (RelayHandler.server_host, RelayHandler.server_port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.b_stream = IOStreamMixup(sock)
    self.b_stream.connect(self.b_addr, self.start_relay)

  def start_relay(self):
    self.a_stream.read(self.relay_a_to_b, True)
    self.b_stream.read(self.relay_b_to_a, True)

  def relay_a_to_b(self, data):
    if not self.b_stream.closed():
      self.b_stream.write(data)
    else:
      self.close()

  def relay_b_to_a(self, data):
    if not self.a_stream.closed():
      self.a_stream.write(data)
    else:
      self.close()

  def close(self):
    if self.b_stream and not self.b_stream.closed():
      self.b_stream.close()
    if self.a_stream and not self.a_stream.closed():
      self.a_stream.close()
      

class AcceptHandler(object):
  def __init__(self, sock):
    self.sock = sock
  
  def accept(self, fd, events):
    while True:
      try:
        conn_fd, addr = self.sock.accept()
      except socket.error as e:
        if e[0] not in (errno.EWOULDBLOCK, errno.EAGAIN):
          raise
        return
      else:
        RelayHandler(conn_fd, addr)

def start_local():
  logging.basicConfig(filename="ioloop_local.log", level=logging.DEBUG)
  host, port = config.local_host, config.local_port
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.setblocking(0)
  sock.bind((host, port))
  sock.listen(128)

  io_loop = IOLoop.instance()
  accept_hdl = AcceptHandler(sock)
  io_loop.add_handler(sock.fileno(), accept_hdl.accept, io_loop.READ)

  try:
    io_loop.start()
  except KeyboardInterrupt:
    io_loop.stop()
    print("Server Exit.")
