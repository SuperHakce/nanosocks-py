import socket
import errno
import struct
import logging

from nanosocks.core.ioloop import IOLoop
from nanosocks.core.iostream import IOStream
from nanosocks.core.iostream_mixup import IOStreamMixup

from nanosocks import config

class SocksHandler(object):
  
  def __init__(self, conn_fd, addr):
    self.a_addr = addr
    self.a_stream = IOStreamMixup(conn_fd)
    logging.debug("new conn: {}:{}".format(addr[0], addr[1]))
    self.b_addr = None
    self.b_stream = None
    self.read_conn_ver()

  def read_conn_ver(self):
    self.a_stream.read_bytes(2, self.read_conn_methods)

  def read_conn_methods(self, data):
    """
                    +----+----------+----------+
                    |VER | NMETHODS | METHODS  |
                    +----+----------+----------+
                    | 1  |    1     | 1 to 255 |
                    +----+----------+----------+
    """
    if ord(data[0]) != 0x5:
      self.close()
      return
    
    self.a_stream.read_bytes(ord(data[1]), self.send_conn_resp)

  def send_conn_resp(self, data):
    self.a_stream.write('\x05\x00')
    self.a_stream.read(self.read_conn_req)

  def read_conn_req(self, data):
    """
        +----+-----+-------+------+----------+----------+
        |VER | CMD |  RSV  | ATYP | DST.ADDR | DST.PORT |
        +----+-----+-------+------+----------+----------+
        | 1  |  1  | X'00' |  1   | Variable |    2     |
        +----+-----+-------+------+----------+----------+
    """
    if len(data) < 7 or ord(data[1]) != 0x1:
      self.close()
      return

    dstPort = struct.unpack(">H", data[-2:])[0]
    if ord(data[3]) == 0x1:     # IPv4
      dstIP = socket.inet_ntop(socket.AF_INET, data[4:8])
      dstFamily = socket.AF_INET
    elif ord(data[3]) == 0x3:   # domain name
      dstIP = data[4+1:-2]
      dstFamily = None
    elif ord(data[3]) == 0x4:   # IPv6
      dstIP = socket.inet_ntop(socket.AF_INET6, data[4:20])
      dstFamily = socket.AF_INET6

    sock = socket.socket(dstFamily or socket.AF_INET, socket.SOCK_STREAM)
    self.b_stream = IOStream(sock)
    self.b_stream.connect((dstIP, dstPort), self.send_conn_req_resp)

  def send_conn_req_resp(self):
    self.a_stream.write('\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00')
    self.a_stream.read(self.relay_a_to_b, True)
    self.b_stream.read(self.relay_b_to_a, True)

  def relay_a_to_b(self, data):
    self.b_stream.write(data)

  def relay_b_to_a(self, data):
    self.a_stream.write(data)

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
        SocksHandler(conn_fd, addr)
        
def start_server():
  logging.basicConfig(filename="ioloop_server.log", level=logging.DEBUG)
  host, port = config.server_bind_host, config.server_port
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
