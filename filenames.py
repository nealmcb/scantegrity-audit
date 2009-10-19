"""
filenames for individual audit files

Ben Adida
ben@adida.net
2009-10-10
"""

import hashlib

# first meeting
MEETING_ONE_IN = "MeetingOneIn.xml"
MEETING_ONE_OUT = "MeetingOneOut.xml"
ELECTION_SPEC = "ElectionSpec.xml"
PARTITIONS = "partitions.xml"

# second meeting
MEETING_TWO_IN = "MeetingTwoIn.xml"
MEETING_TWO_OUT = "MeetingTwoOut.xml"
MEETING_TWO_OUT_COMMITMENTS = "MeetingTwoOutCommitments.xml"

# third meeting
MEETING_THREE_IN = "MeetingThreeIn.xml"
MEETING_THREE_OUT = "MeetingThreeOut.xml"

def file_in_dir(dir, file):
  return dir + "/" + file

def hash_file(path):
  f = open(path, "r")
  contents = f.read()
  f.close()
  
  return hashlib.sha1(contents).hexdigest()