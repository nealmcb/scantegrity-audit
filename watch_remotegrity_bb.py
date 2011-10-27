#!/usr/bin/env python
"""
Watch the bulletin boards used by Remotegrity.

%InsertOptionParserUsage%

Example:
 watch_remotegrity_bb.py https://takoma.remotegrity.org/
"""

import os
import sys
import time
from optparse import OptionParser
from datetime import datetime

import urllib
import logging
import hashlib

__author__ = "Neal McBurnett <http://neal.mcburnett.org/>"
__version__ = "0.1.0"
__date__ = "2011-10-26"
__copyright__ = "Copyright (c) 2011 Neal McBurnett"
__license__ = "GPL v3"

parser = OptionParser(prog="watch_remotegrity_bb.py", version=__version__)
parser.add_option("-u", "--urlbase",
  help="Base URL for the bulletin boards.  E.g. -u https://takoma.remotegrity.org/")

parser.add_option("-i", "--interval", type="int",
  action="store", default=300,
  help="interval in seconds between retrievals")

# incorporate OptionParser usage documentation in our docstring
__doc__ = __doc__.replace("%InsertOptionParserUsage%\n", parser.format_help())

def md5sum(filename):
    "Compute MD5 hash value of the given file" 

    with open(filename, mode='rb') as f:
        d = hashlib.md5()
        while True:
            buf = f.read(4096)
            if not buf:
                break
            d.update(buf)
    return d.hexdigest()

def main(parser):
    """
    Sit in a loop retrieving all both BB.php and BBoffline.php.
    If the data is the same as last time, don't save it.
    The delay interval between retrievals is configurable.
    """

    logging.basicConfig(level=logging.INFO, format='%(message)s', filename= "watch_remotegrity_bb.log", filemode='a' )

    (options, args) = parser.parse_args()

    paths = ["BB.php", "BBoffline.php"]

    last_hashes = [None, None]

    while True:

        for i, url in enumerate(paths):
            # Save the given url in a local file, suffixed with a UTC ISO timestamp
            # down to the second, e.g. BB.php-20111026T221041
            file, response = urllib.urlretrieve(options.urlbase + url,
                                url + datetime.utcnow().strftime('-%Y%m%dT%H%M%S'))
            logging.info("Retrieved %s, %s bytes" % (file, response.dict['content-length']))

            hash = md5sum(file)
            if hash != last_hashes[i]:
                last_hashes[i] = hash
                logging.info("%s is new" % (file))
            else:
                os.remove(file)

        time.sleep(options.interval)

if __name__ == "__main__":
    main(parser)
