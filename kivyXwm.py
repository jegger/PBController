#!/usr/bin/env python

#Thanks for the inputs from Benjamin.
#
#http://kivy-lab.blogspot.ch/2011/05/kivy-window-management-on-x11.html
#

from Xlib.display import Display
from Xlib import X
            
def repositionize(title=str, x=int, y=int, width=int, height=int):
    HEIGHT = height
    WIDTH = width
    y=1080-y-height
    display = Display()
    root = display.screen().root
    windowIDs = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'),X.AnyPropertyType).value
    for windowID in windowIDs:
        window = display.create_resource_object('window', windowID)
        titles = window.get_wm_name()
        pid = window.get_full_property(display.intern_atom('_NET_WM_PID'), X.AnyPropertyType)
        if title in titles:
            window.configure(x = x, y = y, width=WIDTH, height=HEIGHT)
            display.sync()