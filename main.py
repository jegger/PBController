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
import dbus
import sqlite3
import dbus.service
import signal
import socket
from dbus.mainloop.glib import DBusGMainLoop
#initialize thread support in gtk
gtk.threads_init()
#gtk.gdk.threads_init()

"""
PBController
============

The PBController starts all the progs in a seperate process. Also it regulates
the the desktops of Kwin. To use PBCntroller successfully you have to use Kwin.
Else it will just be a little mess. -> Switching between different progs is not
possible. If you want to use this with compiz you have to write the addition 
yourself.

!For kwin you have to install the tool WMIface first!
"""

class Controller():
    '''This is the controller class. It will start, stop progs and receive the
    events when a prog is opened or closed. It is also handling the kwin desktop
    switching when kwin is available. Without kwin only one prog can be open at
    a time.
    '''
    progs={}
    def __init__(self):
        print "PBController has started"
        #init dbus client
        self.bus = dbus.SessionBus()
            
    def open_prog(self, prog_id):
        '''Open a particular prog.
        
        If Kwin is not available it will just launch one prog at a time.
        Also it will not do any desktop switching.
        
        :param prog_id: id of prog which should be opened
        '''
        prog_id=int(prog_id)
        if prog_id not in self.progs:
            #if this is the first run since runtime make a new prog instance
            self.progs[prog_id]=Prog(self, prog_id, self.get_path_from_db(prog_id), 
                                    tuio.create_new_port(), ignore_region=(0.9479166667,
                                                                           0.9074074074,
                                                                           0.9739583333,
                                                                           0.9537037037))
        #check if the prog is already running
        if self.progs[prog_id].open:
            self.switch_to_desktop(self.progs[prog_id].desktop)
            tuio.add_port(self.progs[prog_id].TUIOport)
        else:
            if self.kwin_is_available():
                #is a desktop free?
                c=0
                for prog in self.progs:
                    if self.progs[prog].desktop!=None:
                        c+=1
                if c>= self.get_number_of_desktops()-1:
                    #all desktops are full
                    self.prog_opening_failed(prog_id, "NoFreeDesktop")
                    return False
            
            #if it is not running, try to start it & start tuio for prog
            tuio.add_port(self.progs[prog_id].TUIOport)
            if self.progs[prog_id].start():
                #if kwin is available
                if self.kwin_is_available():
                    self.progs[prog_id].desktop=self.get_current_desktop()
                self.prog_opened(prog_id)
            else:
                #if start fails: add pbase port again
                tuio.add_port(3335)
                
        return False
    
    def prog_opened(self, prog_id):
        '''Call over DBUS to PBase&PBSwitch: prog_opened
        
        :param prog_id: id of prog which just opened
        '''
        print "prog opened", prog_id
        server=self.try_reach_dbus_PBase()
        print "prog opened2", prog_id
        if server:
            print "prog opened2.1", prog_id
            try:
                print "prog opened2.2", prog_id
                server.prog_opened(prog_id, dbus_interface = 'org.PB.PBase')
                print "prog opened2.3", prog_id
            except dbus.exceptions.DBusException, e:
                print "prog opened2.4", prog_id
                print "dbus exception from main from pbcontroller:", e
                print "prog opened2.5", prog_id
        print "prog opened3", prog_id
        try:
            server = self.bus.get_object('org.PB.PBSwitch', '/PBSwitch')
            print "prog opened4", prog_id
            try:
                server.prog_opened(prog_id, dbus_interface = 'org.PB.PBSwitch')
            except dbus.exceptions.DBusException, e:
                print "in controller main", e
            print "prog opened4", prog_id
        except Exception, e:
            print "prog opened5", prog_id
            print e
        
    def stop_prog(self, prog_id):
        '''This function kills/stops a prog.
        
        :param prog_id: prog_id of prog which should be killed/stopped
        '''
        PID=self.progs[prog_id].PID
        print "kill prog:", PID
        try:
            os.killpg(PID, signal.SIGTERM)
        except:
            os.system("kill "+str(PID))
        os.system("kill -9 "+str(PID))
        return False
    
    def stop_all_progs(self):
        for prog in self.progs: self.stop_prog(prog)
        for prog in self.progs: self.progs[prog].threading=False
    
    def prog_closed(self, prog_id):
        '''Call over DBUS to PBase: prog_closed
        Stop TUIO port for this prog
        Start TUIO for PBase
        
        :param prog_id: id of prog which just closed
        '''
        prog_id=int(prog_id)
        #set desktop of prog=None
        self.progs[prog_id].desktop=None
        #start tuio for pbase
        tuio.add_port(3335)
        server=self.try_reach_dbus_PBase()
        if server: 
            try:
                server.prog_closed(prog_id, dbus_interface = 'org.PB.PBase')
            except dbus.exceptions.DBusException, e:
                print "failed to connect to pbase dbus", e
        try:
            server = self.bus.get_object('org.PB.PBSwitch', '/PBSwitch')
            try:
                server.prog_closed(prog_id, dbus_interface = 'org.PB.PBSwitch')
            except dbus.exceptions.DBusException, e:
                print "in controller main", e
        except Exception, e:
            print e
        return False
    
    def prog_opening_failed(self, prog_id, reason):
        server=self.try_reach_dbus_PBase()
        if server:
            try:
                server.prog_opening_failed(prog_id, reason, dbus_interface = 'org.PB.PBase')
            except dbus.exceptions.DBusException, e:
                print e
    
    def load_pbase(self):
        '''Call over DBUS to PBase: load pbase
        '''
        server=self.try_reach_dbus_PBase()
        if server: 
            try:
                server.load(dbus_interface = 'org.PB.PBase')
            except dbus.exceptions.DBusException, e:
                print e
        return False
    
    def unload_pbase(self):
        '''Call over DBUS to PBase: unload
        '''
        server=self.try_reach_dbus_PBase()
        if server: 
            try:
                server.unload(dbus_interface = 'org.PB.PBase')
            except dbus.exceptions.DBusException, e:
                print e
        return False
    
    def show_pbase(self):
        '''This function shows PBase. In case kwin is available it will switch to the 
        next free desktop. If kwin is not available it will close the running prog.
        '''
        if self.kwin_is_available():
            #check if no prog is on the current desktop: this means pbase is already open
            for prog in self.progs:
                if self.progs[prog].desktop==self.get_current_desktop():
                    self.switch_to_desktop(self.get_free_desktop())
                    #activate tuio
                    tuio.add_port(3335)
                    return
        else:
            #if kwin is not available, quit all runing progs
            for prog in self.progs:
                if self.progs[prog].open:
                    print prog
                    self.stop_prog(prog)
        return
    
    def get_open_progs(self):
        '''This function returns all the open progs in a list.
        
        :return progs: list with prog_id's
        '''
        prog_list=[]
        for prog in self.progs:
            if self.progs[prog].open: prog_list.append(prog)
        return prog_list
    
    def get_free_desktop(self):
        '''This function searches for the next free desktop and returns the number
        of it.
        
        :return desktop: int: the number of the free desktop
        '''
        #create a list with the number of desktops in it.
        #example: desktops=[1,2,3,4] (four desktops)
        desktops=[]
        for desktop in range(self.get_number_of_desktops()):
            desktops.append(desktop+1)
        #fill the number in the list with None when a prog is there
        #example: desktops[None,2,3,4] (On desktop 1 is a prog running)
        for prog in self.progs:
            if self.progs[prog].desktop!=None: #ignore progs which aren't active/ prog.desktop=None
                desktops[desktops.index(self.progs[prog].desktop)]=None
        for i in desktops:
            if i != None: return i
    
    def switch_to_desktop(self, desktop):
        '''This function switches to the given desktop.
        
        :param desktop: nuber of the desktop
        '''
        if self.kwin_is_available():
            os.system("wmiface setCurrentDesktop "+str(desktop))
    
    def get_current_desktop(self):
        '''This function returns the number of the current desktop.
        
        :return desktop: int, number of desktop
        '''
        if self.kwin_is_available():
            proc = subprocess.Popen("wmiface currentDesktop", shell=True, stdout=subprocess.PIPE)
            proc.wait()
            for line in proc.stdout: currentDesktop=int(line.rstrip())
            return int(currentDesktop)
    
    def get_number_of_desktops(self):
        '''This function returns the number of the current desktop.
        
        :return desktop: int, number of desktop
        '''
        if self.kwin_is_available():
            proc = subprocess.Popen("wmiface numberOfDesktops", shell=True, stdout=subprocess.PIPE)
            proc.wait()
            for line in proc.stdout: desktops=int(line.rstrip())
            return int(desktops)
        
    def shutdown(self, reboot=False):
        '''This function calls shutdown on start over DBUS
        This function also closes all running progs first.
        
        :param reboot: if rebooting after shutdown or not
        '''
        self.stop_all_progs()
        server = self.bus.get_object('org.PB.start', '/start')
        server.shutdown(reboot, dbus_interface = 'org.PB.start')
        return False
    
    def kwin_is_available(self):
        '''This function checks if kwin is available or not by
        calling the try calling its D-Bus
        
        :return bool: returns True or False
        '''
        try: 
            self.bus.get_object('org.kde.kwin', '/KWin')
            return True
        except: 
            return False
        
    def get_path_from_db(self, prog_id):
        '''This function gets the path to the prog.
        
        :param prog_id: id of the prog
        '''
        DB_connection = sqlite3.connect("../PBase/data/database.sqlite")
        DB_cursor = DB_connection.cursor()
        DB_cursor.execute("SELECT path FROM progs WHERE id = '%i'" %prog_id)
        DB_connection.commit()
        for row in DB_cursor: path=row[0]
        DB_connection.close()
        return path
    
    def try_reach_dbus_PBase(self):
        try:
            server = self.bus.get_object('org.PB.PBase', '/PBase')
        except dbus.exceptions.DBusException:
            print "Can not reach DBUS PBase"
            return False
        return server
    
class Prog():
    '''The Prog class will be instanced for every prog that will be running.

    :param controller: the controller object
    :param prog_id: the ID of the prog
    :param path: the path to the prog
    :pram TUIOport: the port on which which the prog should listen to TUIO.
    Once the prog instance is created, you should not change the port unless 
    you are sure that you know what you are doing. That is because the
    TUIOController will multiplex to this port the next time this prog
    gets opened too.
    :prarm ignore_region: this is the region on which the close button 
    could be placed. This means on this region do not recognize any touches.
    '''
    def __init__(self, controller, prog_id, path, TUIOport, ignore_region):
        self.controller=controller
        self.prog_id=prog_id
        self.path=path
        self.TUIOport=TUIOport
        self.ignore_region=ignore_region #(0.395833, 0.9537, 0.604166, 1.0)
        self.open=False
        self.desktop=None
        self.PID=None #the PID will defined at runtime via the queue.
        self.threading=True
    
    def start(self, *kwargs):
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
        self.process=multiprocessing.Process(target=self.__process, args=(q,))
        self.process.start()
        
        #create the thread
        t = Thread(target=self.__check_activity)
        t.start()
        
        #receive PID from queue
        self.PID=q.get()
        print "Prog opened with PID of:", self.PID
        self.open=True
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
        command=("python","main.py","-k","-p", 
                 "test:tuio,0.0.0.0:"+str(self.TUIOport),"-c",
                 "postproc:ignore:["+str(self.ignore_region)+"]")
        pr=subprocess.Popen(command, cwd="../progs/"+self.path+"/", stdout=subprocess.PIPE, 
                                             preexec_fn=os.setsid)
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
            time.sleep(0.2)
            if not self.process.is_alive():
                self.open=False
                gtk.timeout_add(1, self.controller.prog_closed, self.prog_id)
                break

class TUIOMultiplexer(object):
    '''This class is does multiplex the TUIO to different ports.
    
    There is a self.active_ports dict, in which all ports are stored that are active.
    Also there is a self.ports list, in which all ports are stored where used since
    runtime.
    '''
    active_ports={} #active ports
    ports=[] #all ports which are used since runtime
    stop_loop=False
    def __init__(self, *kwagrs):
        '''The init function will start the loop
        Also it will add the first port to the loop (PBSwitch->3334)
        '''
        #always multiplex for PBSwitch 3334!
        self.add_port(3334)
        #start tuio for pbase
        self.add_port(3335)
        
        t = Thread(target=self.__loop)
        t.start()
                
    def __loop(self):
        '''The main loop for multiplexing.
        This function is launched as a thread from the init form this class.
        Do not call this function on you own!
        '''
        hostin = "127.0.0.1"
        portin = 3333
        cont = True
        while cont and not self.stop_loop:
            try:
                sin = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sin.bind((hostin,portin))
                cont = False
            except:
                print "TUIOMultiplexer: Port error. retry..."
                time.sleep(2)
                cont = True
        data = 1
        while data and not self.stop_loop:
            data = sin.recv(1024*1024)
            copy_active_ports=self.active_ports
            for i in copy_active_ports:
                try:
                    self.active_ports[i].send(data)
                except:
                    pass
    
    def create_new_port(self):
        '''Create a new port for a new prog.
        This is needed if a prog is lunched the first time since runtime.
        The function will return you the new port for.
        
        :return port: Returns the port for this prog
        '''
        #get highest used port
        high=max(port for port in self.ports)
        print "new highest port:", high+1
        #add new port that is +1 higher
        self.ports.append(high+1)
        return high+1
    
    def add_port(self, port):
        '''Add a port to the multiplexer
        
        :param port: port to add
        '''
        #check if port is already in list
        if not port in self.ports:
            self.ports.append(port)
            
        #close all ports, without the one that should added
        ports_to_remove=[] #create list to avoid "dict changed size during iteration"
        for porti in self.active_ports:
            if porti!=3334: #if it is not the switch port
                ports_to_remove.append(porti)
        for porti in ports_to_remove: self.remove_port(porti)
        
        #add port
        if port not in self.active_ports:
            print "START TUIO:", port
            self.active_ports[port] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.active_ports[port].connect(("127.0.0.1",port))
    
    def remove_port(self, port):
        '''Remove a port from the multiplexer
    
        :param port: port to remove
        '''
        if port in self.active_ports:
            print "STOP TUIO:", port
            self.active_ports.pop(port)
tuio=TUIOMultiplexer()
        
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
        print "main controller: open prog"
        gtk.timeout_add(1, self.controller.open_prog, prog_id)
        print "main controller: open prog after"
        return
    
    @dbus.service.method('org.PB.PBController')
    def close_prog(self, prog_id):
        '''This function closes a prog. After closing the PBase 
        will be showed.
        
        :param prog_id: id of the prog which should be closed
        '''
        gtk.timeout_add(1,self.controller.stop_prog,prog_id)
        return
    
    @dbus.service.method('org.PB.PBController')
    def get_open_progs(self):
        '''This function returns a list with prog_id's from progs
        which are open.
        
        :return prog_list: list with prog id's
        '''
        return self.controller.get_open_progs()
    
    @dbus.service.method('org.PB.PBController')
    def load_pbase(self):
        '''This function will load the PBase.
        '''
        gtk.timeout_add(1,self.controller.load_pbase)
        return
    
    @dbus.service.method('org.PB.PBController')
    def unload_pbase(self):
        '''This function will unload the PBase.
        '''
        gtk.timeout_add(1, self.controller.unload_pbase)
        return
    
    @dbus.service.method('org.PB.PBController')
    def show_pbase(self):
        '''This function will unload the PBase.
        '''
        gtk.timeout_add(1, self.controller.show_pbase)
        return
    
    @dbus.service.method('org.PB.PBController')
    def shutdown(self, reboot=False):
        '''This function will shutdown the device or
        restart in case the argument reboot is True
        
        :param reboot: Indicates if the device should reboot or shutdown
        '''
        gtk.timeout_add(1, self.controller.shutdown, reboot)
        return
     
DBusGMainLoop(set_as_default=True)
controller=Controller()
myservice = DBusServer(controller)
try:
    gtk.main()
except KeyboardInterrupt:
    #stop everything safely
    tuio.stop_loop=True
    controller.stop_all_progs()
    raise
except Exception, e:
    print e