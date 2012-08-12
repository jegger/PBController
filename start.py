#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#===============================================================================
# Written by Rentouch 2012 - http://www.rentouch.ch
#===============================================================================

#standard
import subprocess
import os
from threading import Thread
import time
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import gtk

gtk.gdk.threads_init()

'''
Start
=====
In this file all which is done is launching and closing different elements of PB.

What does this script
~~~~~~~~~~~~~~~~~~~~~
This script launches all the PB - elements. In case of a shutdown or reboot it 
will close them also. If any of the PB elements will crash, the script will 
restart them immediately.

Why doesn't do this the controller?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
It is just a matter of stability. 
In case of a controller crash all the progs will crash also.
But the PBase, PBSwitch and PBUpdater are running safely.

Because the controller is a complex structure, the possibility is bigger for a 
crash of the controller than this simple start script.

How can I close or shutdown/reboot?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You have to call the function shutdown(reboot) over DBUS.
You can reach it under: session bus: org.PB.start (/start)

'''

class Start():
    PBUpdater=True
    PBase=True
    PBSwitch=True
    PID_PBUpdater=None
    
    #list with all the scripts
    script_list=[{"path":"../PBUpdater", "filename":"main.py", "PID":None, "run":True, "port":None},
                 {"path":"../PBController", "filename":"main.py", "PID":None, "run":True, "port":None},
                 {"path":"../PBase", "filename":"main.py", "PID":None, "run":True, "port":3335},
                 {"path":"../PBController", "filename":"switch.py", "PID":None, "run":True, "port":3334}]
    
    def _launch(self, path, filename, index):
        '''This is the function that actually launches any of the scripts.
        While launching it stores the PID (for killing the process later)
        int the list. This function is always a thread.
        '''
        while self.script_list[index]["run"]:
            os.chdir(path)
            if self.script_list[index]["port"]!=None:
                if self.script_list[index]["filename"]=="switch.py":
                    #for the PBSwitch
                    pr=subprocess.Popen(("python",filename, "-w","--size=50x50","-p", "test:tuio,0.0.0.0:"+str(self.script_list[index]["port"])))
                else:
                    #for PBase
                    pr=subprocess.Popen(("python",filename, "-k","-p", "test:tuio,0.0.0.0:"+str(self.script_list[index]["port"])))
            else:
                pr=subprocess.Popen(("python",filename))
            self.script_list[index]["PID"]=pr.pid
            print "STARTED:", self.script_list[index]["path"], self.script_list[index]["filename"], self.script_list[index]["PID"]
            
            #try waiting until window opened
            time.sleep(0.5)
            
            #special window operations
            if self.script_list[index]["filename"]=="switch.py":
                #for switch (above)
                self.modify_window(self.script_list[index]["PID"], True, "keepAbove")
            else:
                #for pbase
                self.modify_window(self.script_list[index]["PID"], True, "keepBelow")
            
            pr.wait()
    
    def modify_window(self, pid, everydesktop, args):
        '''This functions modifies the window if wmctrl exists
        
        :param pid: the pid of the window
        :param everydesktop: bool: if window should appear on every desktop
        :param args: the args for adding in wmctrl: above or below
        '''
        if not self.wmiface:
            return
        
        #get window id
        proc = subprocess.Popen('wmiface findNormalWindows "" "" "" "" '+str(pid)+' false', shell=True, stdout=subprocess.PIPE)
        proc.wait()
        window_id=None
        for line in proc.stdout:
            window_id=line.replace("\n", "")
        if window_id==None: 
            print "Can not find window with PID:", pid
            return
        
        #modify window with args
        command='wmiface '+args+' '+window_id+' True'
        pr=subprocess.Popen(command, shell=True)
        pr.wait()
        #modify window with desktop
        if not everydesktop:
            return
        print window_id
        command='wmiface setWindowDesktop '+window_id+' -1'
        pr=subprocess.Popen(command, shell=True)
        pr.wait()
        
    def cmd_exists(self, cmd):
        '''checks if this command exists
        '''
        if len(os.popen(cmd).readlines())==0:
            return False
        else:
            return True
    
    def start(self):
        '''This function makes a loop trough the list and makes a thread for
        every script.
        '''
        #check for wmctrl
        self.wmiface=self.cmd_exists("wmiface numberOfDesktops")
        print self.wmiface
        #loop trough scripts
        for index, script in enumerate(self.script_list):
            t = Thread(target=self._launch, args=(script["path"], script["filename"], index))
            t.start()
            time.sleep(0.1)
            
    def stop(self):
        '''This function kills all the running scripts.
        '''
        for script in self.script_list:
            script["run"]=False
            os.system("kill "+str(script["PID"]))
        raise SystemExit(0)
    
class DBusServer(dbus.service.Object):
    '''DBus server from PBase.
    Reachable under session bus: org.PB.start (/start)
    '''
    def __init__(self, start):
        '''Initialize the session bus under: org.PB.start
        
        :param start: start object
        '''
        self.start=start
        bus_name = dbus.service.BusName('org.PB.start', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/start')

    @dbus.service.method('org.PB.start')
    def shutdown(self, reboot=False):
        '''This function will shutdown the device or
        restart in case the argument reboot is True
        
        :param reboot: Indicates if the device should reboot or shutdown
        '''
        print "SHUTDOWN"
        return self.start.stop()
        
DBusGMainLoop(set_as_default=True)
st=Start()
myservice = DBusServer(st)
st.start()
try:
    gtk.main()
except KeyboardInterrupt:
    raise  