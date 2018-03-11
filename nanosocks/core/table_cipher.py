from nanosocks import config

class TableCipher(object):
  def __init__(self, table_str=config.table_str, offset=config.offset):
    self.table_str = table_str
    self.prepare_tables(offset)

  def prepare_tables(self, offset):
    self.p = bytearray(self.table_str[offset:] + self.table_str[:offset])
    self.q = bytearray(self.p)
    for i, n in enumerate(self.p):
      self.q[n] = i

  def set_offset(self, offset):
    self.prepare_tables(offset)

  def enc(self, s):
    t = bytearray(s)
    for i, n in enumerate(t):
      t[i] = self.p[n]
    return str(t)

  def dec(self, t):
    s = bytearray(t)
    for i, n in enumerate(s):
      s[i] = self.q[n]
    return str(s)
