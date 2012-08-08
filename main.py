#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#===============================================================================
# Written by Rentouch 2012 - http://www.rentouch.ch
#===============================================================================

#global
import os
import time
import multiprocessing
import subprocess
from threading import Thread
import gtk
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
#initialize thread support in gtk
#gtk.threads_init()
gtk.gdk.threads_init()

"""
PBController
============

The PBController starts all the progs in a seperate process. Also it regulates
the the desktops of Kwin. To use PBCntroller successfully you have to use Kwin.
Else it will just be a little mess. -> Switching between different progs is not
possible. If you want to use this with compiz you have to write the addition 
yourself.
"""

class Controller():
    def __init__(self):
        pass
    
    def start_prog(self, prog_id):
        pass
    
    def prog_started(self, prog_id):
        pass
    
    def stop_prog(self, prog_id):
        pass
    
    def prog_stopped(self, prog_id):
        pass
    
    def load_pbase(self):
        pass
    
    def unload_pbase(self):
        pass
    
    def shutdown(self):
        pass
    
class Prog():
    '''The Prog class will be instanced for every prog that will be running.

    :param controller: the controller object
    :param prog_id: the ID of the prog
    :param path: the path to the prog
    :pram TUIOport: the port on which which the prog should listen to TUIO.
    Once the prog instance is created, you should not change the port unless 
    you are sure that you know what you are doing. That is because the
    TUIOController will multiplex the to this port the next time this prog
    gets opened also.
    :prarm ignore_region: this ist the region on whiche the close button 
    could be placed. This means on this region do not recognize any touches.
    '''
    def __init__(self, controller, prog_id, path, TUIOport, ignore_region):
        self.controller=controller
        self.prog_id=prog_id
        self.path=path
        self.TUIOport=TUIOport
        self.ignore_region=ignore_region #(0.395833, 0.9537, 0.604166, 1.0)
        self.PID=None #the PID will defined at runtime via the queue.
    
    def start(self):
        '''Starting the prog
        
        1. Create a queue for passing arguments between processes
        2. Create and start a process out of the __process() function
        3. Create and start a thread which is checking the activity of the process
        4. Wait until we received the PID of the subprocess
        
        :return: True if the prog is launched successfully.
        '''
        #check if the process is already running
        if hasattr(self, "process"):
            if self.process.is_alive():
                return False
            
        #make queue for passing arguments between process & this class
        q = multiprocessing.Queue()
        
        #create and start the process
        self.process=multiprocessing.Process(target=self.start, args=(q,))
        self.process.start()
        
        #create the thread
        t = Thread(target=self.__check_activity)
        t.start()
        
        #receive PID from queue
        self.PID=q.get()
        return True
    
    def stop(self):
        '''Stopping the prog / quit
        
        This is done simply by calling "kill <PID>"
        '''
        os.system("kill "+str(self.PID))
    
    def __process(self, q):
        '''The function which will get transformed to the process.
        This is a internal function. Don't EVER call this function on your own! 
        call it only via start()
        '''
        command=("python",self.path,"-k","-p", "test:tuio,0.0.0.0:"+str(self.port),"-c","postproc:ignore:["+self.ignore_region+"]")
        pr=subprocess.Popen(command)
        q.put(pr.pid) #put the PID thrugh the queue
        pr.wait() #wait until the subprocess is finished
    
    def __check_activity(self):
        '''This function get transformed into the thread. It checks
        every 0.1second if the process is still alive. When the prog get
        closed or had a crash it isn't alive anymore. Is this the case,
        then we can inform the controller object about that. Don't EVER 
        call this function on your own! call it only via start()
        
        This thread will be stopped as soon: self.threading=False
        '''
        while self.threading:
            time.sleep(0.1)
            if not self.process.is_alive():
                self.controller.prog_stopped(self.app_id)
        
class DBusServer(dbus.service.Object):
    '''DBus server from PBController.
    Reachable under session bus: org.PB.PBController (/PBController)
    '''
    def __init__(self, controller):
        '''Initialize the session bus under:
        org.PB.PBController
        
        :param controller: controller object
        '''
        self.controller=controller
        bus_name = dbus.service.BusName('org.PB.PBController', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/PBController')
 
    @dbus.service.method('org.PB.PBController')
    def open_prog(self, prog_id):
        '''This function opens or switch to a prog.
        
        :param prog_id: id of the prog which should be opened
        '''
        self.controller.start_prog(prog_id)
    
    @dbus.service.method('org.PB.PBController')
    def close_prog(self, prog_id):
        '''This function closes a prog. After closing the PBase 
        will be showed.
        
        :param prog_id: id of the prog which should be closed
        '''
        self.controller.stop_prog(prog_id)
    
    @dbus.service.method('org.PB.PBController')
    def load_pbase(self):
        '''This function will load the PBase.
        '''
        self.controller.load_pbase()
    
    @dbus.service.method('org.PB.PBController')
    def unload_pbase(self):
        '''This function will unload the PBase.
        '''
        self.controller.unload_pbase()
    
    @dbus.service.method('org.PB.PBController')
    def shutdown(self, reboot=False):
        '''This function will shutdown the device or
        restart in case the argument reboot is True
        
        :param reboot: Indicates if the device should reboot or shutdown
        '''
        self.controller.shutdown(reboot)
     
DBusGMainLoop(set_as_default=True)
controller=Controller()
myservice = DBusServer(controller)

try:
    gtk.main()
except KeyboardInterrupt:
    #stop everything safely
    raise