from nanosocks.core.iostream import IOStream
from nanosocks.core.table_cipher import TableCipher as Cipher

class IOStreamMixup(IOStream):
  def __init__(self, socket, io_loop=None, max_buffer_size=104857600,
               read_chunk_size=4096):
    super(IOStreamMixup, self).__init__(socket, io_loop, max_buffer_size, read_chunk_size)
    self._cipher = Cipher()

  def _read_from_socket(self):
    chunk = super(IOStreamMixup, self)._read_from_socket()
    if chunk:
      chunk = self._cipher.dec(chunk)
    return chunk

  def write(self, data, callback=None):
    data = self._cipher.enc(data)
    super(IOStreamMixup, self).write(data, callback)
    
