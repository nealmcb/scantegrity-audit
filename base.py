"""
The core of every meeting verification

not called directly

data path should NOT have a trailing slash
"""

import sys, hashlib
from xml.etree import ElementTree

if len(sys.argv) > 1:
  DATA_PATH = sys.argv[1]
else:
  DATA_PATH = "testdata"

FINGERPRINTS = []

def add_fingerprint(filename, hash_value):
  FINGERPRINTS.append([filename, hash_value])

def fingerprint_report():
  report = ""
  for filename, fingerprint in FINGERPRINTS:
    report += filename + ": " + fingerprint + "\n"
  return report

##
## loading files and adding fingerprints
##

def file_in_dir(dir, file, filename, xml = True, correct_windows= False):
  path = dir + "/" + file

  try:
    f = open(path, "r")
  except:
    print "could not find file %s" % path
    sys.exit(1)
  contents = f.read()
  f.close()
  
  # must do windows style verification loading of newlines
  if correct_windows and contents.find('\r') == -1:
    print "fixing windows"
    contents = contents.replace('\n','\r\n')    
  
  add_fingerprint(filename, hashlib.sha1(contents).hexdigest())
  if xml:
    return ElementTree.fromstring(contents)
  else:
    return contents
    
##
## Pseudorandom Number Generation
##
# reverse-engineered from
# https://scantegrity.org/svn/data/takoma-nov3-2009/PUBLIC/PUBLIC/pre_election_audit.py

    
def prng(seed,index,modulus):
  """
  Generate a random integer modulo the modulus, given a seed and an index
  """
  
  # concatenate seed and index
  hash_input = "%s%d"%(seed,index)

  # get the SHA1 hash in hex, convert to int
  hash_int= int(hashlib.sha1(hash_input).hexdigest(), 16)
  
  # modulo the modulus
  return hash_int % modulus
  
def generate_random_int_list(seed, modulus, num_ints):
  """
  generate a random list of num_ints integers modulo modulus, with the given seed.
  """
  output_list = []
  counter = 0
  while True:
    new_index = prng(seed, counter, modulus)
    counter += 1
    if new_index in output_list:
      continue
    output_list.append(new_index)
    if len(output_list) == num_ints:
      break
      
  return output_list
