#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#===============================================================================
# Written by Rentouch 2012 - http://www.rentouch.ch
#===============================================================================

'''
Start
=====
In this file all which is done is launching and closing different elements of PB.

Why doesn't do this the controller?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It is just a matter of stability. 
In case of a controller crash all the progs will crash also.
But the PBase, PBSwitch and PBUpdater are running safely.

Because the controller is a complex structure, the possibility is bigger for a 
crash of the controller than this simple start script.


What does this script
~~~~~~~~~~~~~~~~~~~~~
This script launches all the PB - elements. In case of a shutdown or reboot it 
will close them also. If any of the PB elements will crash, the script will 
restart them immediately.
'''