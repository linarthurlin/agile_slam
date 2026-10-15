#!/usr/bin/env python3
"""Capture one mapped Linux X11 client window, including WSLg clients."""
import argparse
import ctypes as C
import re
import subprocess
from PIL import Image

class XImage(C.Structure):
    _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),
              ('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),
              ('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),
              ('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),
              ('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong)]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('title',help='Exact window title from xwininfo')
    parser.add_argument('output')
    args=parser.parse_args()
    tree=subprocess.check_output(['xwininfo','-root','-tree'],text=True)
    matches=re.findall(r'(0x[0-9a-f]+) "'+re.escape(args.title)+r'".*? (\d+)x(\d+)',tree)
    if len(matches)!=1:raise RuntimeError(f'Expected one mapped window; found {len(matches)}')
    identifier,width,height=matches[0]
    lib=C.CDLL('libX11.so.6')
    lib.XOpenDisplay.argtypes=[C.c_char_p];lib.XOpenDisplay.restype=C.c_void_p
    lib.XGetImage.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
    lib.XGetImage.restype=C.POINTER(XImage)
    lib.XDestroyImage.argtypes=[C.POINTER(XImage)]
    lib.XCloseDisplay.argtypes=[C.c_void_p]
    display=lib.XOpenDisplay(None)
    if not display:raise RuntimeError('Cannot open X11 display.')
    image=lib.XGetImage(display,int(identifier,16),0,0,int(width),int(height),C.c_ulong(-1).value,2)
    if not image:raise RuntimeError('X11 could not capture the client window.')
    try:
        info=image.contents
        if info.bits_per_pixel!=32 or info.byte_order!=0 or (info.red_mask,info.green_mask,info.blue_mask)!=(0xff0000,0xff00,0xff):
            raise RuntimeError('Unsupported X11 pixel layout.')
        data=C.string_at(info.data,info.bytes_per_line*info.height)
        Image.frombytes('RGB',(info.width,info.height),data,'raw','BGRX',info.bytes_per_line,1).save(args.output)
    finally:
        lib.XDestroyImage(image)
        lib.XCloseDisplay(display)

if __name__=='__main__':main()
