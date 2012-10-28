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
import signal
import logging
gtk.gdk.threads_init()

'''
Start
=====
In this file all which is done is launching and closing different elements of PB.

What do I need?
~~~~~~~~~~~~~~~
- Kivy branch core-x11 (transparent windows)
--> clone from: https://github.com/jegger/kivy.git;
---> install: sudo WITH_X11=1 python setup.py install
- wmiface

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

#initialize logger
log = logging.getLogger('Start')
log.setLevel(logging.INFO)
hdlr = logging.FileHandler('data/logs/log.log')
consoleHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] %(module)s%(lineno)-3s %(message)s")
hdlr.setFormatter(formatter)
consoleHandler.setFormatter(formatter)
log.addHandler(hdlr)
log.addHandler(consoleHandler) 
log.info("*-----------Start(Controller) started-----------*")

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
        #create watchdog to watch over the loop. If the loop gets executed more 
        #then three times in a row in less then 5seconds - close PBase suite
        watchdog_start_time=time.time()
        counter=0
        
        #start the python script. In case of a crash start again until script_list<item>.run=False
        while self.script_list[index]["run"]:
            os.chdir(path)
            if self.script_list[index]["port"]!=None:
                if self.script_list[index]["filename"]=="switch.py":
                    #for the PBSwitch
                    os.environ['KIVY_WINDOW'] = 'x11'
                    pr=subprocess.Popen(["python", filename, "-p", "test:tuio,0.0.0.0:"+str(self.script_list[index]["port"])], env=os.environ, stdout=subprocess.PIPE, 
                                             preexec_fn=os.setsid)
                    os.environ.pop('KIVY_WINDOW')
                else:
                    #for PBase
                    pr=subprocess.Popen(("python",filename, "-k","-p", "test:tuio,0.0.0.0:"+str(self.script_list[index]["port"])))
            else:
                pr=subprocess.Popen(("python",filename))
            
            #fetch PID fpr process
            self.script_list[index]["PID"]=pr.pid
            log.info("Started process: "+str(self.script_list[index]["path"])+str(self.script_list[index]["filename"])+str(self.script_list[index]["PID"]))
            
            start_time=time.time()
            #special window operations
            if self.script_list[index]["filename"]=="switch.py":
                #for switch (above)
                while time.time()-start_time<10 and self.script_list[index]["run"]:
                    if self.modify_window(self.script_list[index]["PID"], True, "keepAbove"):
                        break
                    time.sleep(3)
            elif self.script_list[index]["filename"]=="main.py" and self.script_list[index]["path"]=="../PBase":
                #for pbase
                while time.time()-start_time<10 and self.script_list[index]["run"]:
                    if self.modify_window(self.script_list[index]["PID"], True, "keepBelow"):
                        break
                    time.sleep(2)
            #wait (make synchronous) here until the script breaks somehow
            pr.wait()
            
            #set PID to False, because the process isn't running anymore
            self.script_list[index]["PID"]=False
            
            #watchdog count up and check
            counter+=1
            if counter>=3:
                if time.time()-watchdog_start_time<=10:
                    self.stop()
                    break
                else:
                    counter=0
                    watchdog_start_time=time.time()
    
    def modify_window(self, pid, everydesktop, args):
        '''This functions modifies the window if wmctrl exists
        
        :param pid: the pid of the window
        :param everydesktop: bool: if window should appear on every desktop
        :param args: the args for adding in wmctrl: above or below
        '''
        if not self.wmiface:
            return False
        
        #get window id
        proc = subprocess.Popen('wmiface findNormalWindows "" "" "" "" '+str(pid)+' false', shell=True, stdout=subprocess.PIPE)
        proc.wait()
        window_id=None
        for line in proc.stdout:
            window_id=line.replace("\n", "")
        if window_id==None: 
            log.info("Can't find window with PID:"+str(pid))
            return False
        
        #modify window with args
        command='wmiface '+args+' '+window_id+' True'
        pr=subprocess.Popen(command, shell=True)
        pr.wait()
        #modify window with desktop
        if not everydesktop:
            return True
        command='wmiface setWindowDesktop '+window_id+' -1'
        pr=subprocess.Popen(command, shell=True)
        pr.wait()
        return True
        
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
        #loop trough scripts
        for index, script in enumerate(self.script_list):
            t = Thread(target=self._launch, args=(script["path"], script["filename"], index))
            t.start()
            time.sleep(0.1)
            
    def stop(self):
        '''This function kills all the running scripts.
        '''
        log.info("kill all scripts")
        for script in self.script_list:
            script["run"]=False
            log.info("kill script: "+str(script["filename"])+str(script["PID"]))
            if script["PID"]:
                os.system("kill "+str(script["PID"]))
                if script["filename"]=="switch.py":
                    os.killpg(script["PID"], signal.SIGTERM)
        gtk.main_quit()
    
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
        log.info("Shutdown device")
        return self.start.stop()
        
DBusGMainLoop(set_as_default=True)
st=Start()
myservice = DBusServer(st)
st.start()
gtk.main()