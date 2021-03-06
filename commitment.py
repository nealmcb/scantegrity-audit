"""
The Scantegrity commitment scheme

Ben Adida
ben@adida.net
2009-09-21
"""

import base64, hashlib, binascii
from Crypto.Cipher import AES

def aes_ecb(message, key):
  """
  A simple AES ECB wrapper for a single block
  """
  aes_cipher = AES.new(key, AES.MODE_ECB)
  return aes_cipher.encrypt(message)

def sha256(message):
  """
  A simple wrapper around SHA256 with byte-array output
  """
  return hashlib.sha256(message).digest()

DEBUG = False

def debug(message):
  if DEBUG:
    print message

def commit(message, key_b64, constant):
  """
  commit to a message with a given key and constant.
  
  the message is a string / byte array
  the key is a base64-encoded key
  the constant is a byte array, not base64-encoded
  Return the result base64-encoded
  """

  debug("message: %s, len %d" % (binascii.hexlify(message), len(message)))
  
  # decode the base64 inputs
  key = base64.b64decode(key_b64)
  debug("key: %s " % binascii.hexlify(key))
  
  # now feeding it decoded
  #constant = base64.b64decode(constant_b64)
  debug("constant: %s " % binascii.hexlify(constant))
  
  # compute sak from const
  sak = aes_ecb(constant, key)
  debug("sak: %s " % binascii.hexlify(sak))
  
  # compute h1 and h2
  h1 = sha256(message + sak)
  debug("h1: %s " % binascii.hexlify(h1))
  h2 = sha256(message + aes_ecb(h1, sak))
  debug("h2: %s " % binascii.hexlify(h2))
  
  # concatenate and encode
  return base64.b64encode(h1 + h2)
  
##
## TEST VECTOR
##
if __name__ == '__main__':
  DEBUG = True
  message = binascii.unhexlify('3004030102000301000200030104020001')
  key_b64 = 'dWvJjTDof3YHWyOYvkIFoA=='
  constant_b64 = 'UHJpbmNldG9uRWxlY3Rpbw=='
  constant = 'PrincetonElectio'
  
  expected_b64 = 'EaYe2BToq529uzV7Re2vMdlqh38Wx3sjbcvnE/7qiWC6be1ytPGzQDsOotAUx2jkOpVThQo9zq+RRwDIQGxrjA=='
  
  result = commit(message, key_b64, constant)
  debug("result: %s" % result)
  
  if result == expected_b64:
    print "GOOD!"
  else:
    print "BAD :("
