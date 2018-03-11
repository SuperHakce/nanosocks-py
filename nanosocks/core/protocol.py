import struct

HDR_LEN = 2

def msg_check(buf):
  "check whether buf contains a complete msg"
  if len(buf) <= HDR_LEN:
    return False
  msg_len = struct.unpack_from("<H", buf, 0)[0]
  if len(buf) < HDR_LEN + msg_len:
    return False
  return True

def msg_fetchone(buf):
  "fetch one msg from buf, return (msg, consume length)"
  msg_len = struct.unpack_from("<H", buf, 0)[0]
  msg = buf[HDR_LEN:HDR_LEN+msg_len]
  return msg, HDR_LEN+msg_len

def msg_pack(msg):
  return struct.pack("<H{}s".format(len(msg)), len(msg), msg)
