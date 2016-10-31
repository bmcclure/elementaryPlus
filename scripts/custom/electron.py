#!/usr/bin/python3

import struct
import json
import sys
import os
from functools import reduce
from imp import load_source
absolute_path = os.path.split(os.path.abspath(__file__))[0] + "/"
svgtopng = load_source('svgtopng', absolute_path + 'svgtopng.py')


def getFromDict(dataDict, mapList):
    return reduce(lambda d, k: d[k], mapList, dataDict)


def setInDict(dataDict, mapList, value):
    getFromDict(dataDict, mapList[:-1])[mapList[-1]] = value


# iterative funtion to account for the new size of the png bytearray
def change_dict_vals(d, sizediff, offset):
    if isinstance(d, dict):
        d2 = {k: change_dict_vals(v, sizediff, offset) for k, v in d.items()}
        if d2.get('offset') and int(d2.get('offset')) > offset:
            d2['offset'] = str(int(d2['offset']) + sizediff)
        return d2
    return d


filename = sys.argv[3]+sys.argv[4]
icon_to_repl = sys.argv[2]
icon_for_repl = sys.argv[1]

# uses google's pickle format, which prefixes each field
# with its total length, the first field is a 32-bit unsigned
# integer, thus 4 bytes, we know that, so we skip it
try:
    asarfile = open(filename, 'rb')
except FileNotFoundError:
    sys.exit()
asarfile.seek(4)

# header size is stored in byte 12:16
len1 = struct.unpack('I', asarfile.read(4))[0]
len2 = struct.unpack('I', asarfile.read(4))[0]
len3 = struct.unpack('I', asarfile.read(4))[0]
header_size = len3
zeros_padding = (len2-4-len3)

header = asarfile.read(header_size).decode('utf-8')

files = json.loads(header)
baseoffset = asarfile.tell()+zeros_padding
asarfile.close()

keys = icon_to_repl.split('/')

try:
    fileinfo = getFromDict(files, keys)
except KeyError:
    sys.exit()

offset0 = int(fileinfo['offset'])
offset = offset0+baseoffset
size = int(fileinfo['size'])

with open(filename, 'rb') as asarfile:
    bytearr = asarfile.read()

filename_svg, file_extension = os.path.splitext(icon_for_repl)
if file_extension == '.svg':
    pngbytes = svgtopng.convert_svg2bin(icon_for_repl)
else:
    with open(icon_for_repl, 'rb') as pngfile:
        pngbytes = pngfile.read()

setInDict(files, keys+['size'], len(pngbytes))

newbytearr = pngbytes.join([bytearr[:offset], bytearr[offset+size:]])

sizediff = len(pngbytes)-size

newfiles = change_dict_vals(files, sizediff, offset0)
newheader = json.dumps(newfiles).encode('utf-8')
newheaderlen = len(newheader)

bytearr2 = b''.join([bytearr[:4], struct.pack('I', newheaderlen+(len1-len3)),
                     struct.pack('I', newheaderlen+(len2-len3)),
                     struct.pack('I', newheaderlen), newheader,
                     b'\x00'*zeros_padding,
                     newbytearr[baseoffset:]])

asarfile = open(filename, 'wb')
asarfile.write(bytearr2)
asarfile.close()
