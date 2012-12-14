#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#===============================================================================
# Written by Rentouch 2012 - http://www.rentouch.ch
#===============================================================================

'''
Switch
======

Witch the switch you are able to close progs and switch between them.

Normally the switch can appear just as a close button in the upper right corner.
You can deactivate the switch button in the settings. In this case you can only
show the switch button by making a gesture. When you have a Probazaar account 
you can also close progs from probazaar.ch remotely. (via PBUpdater)
'''
#kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.support import install_gobject_iteration
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty
from kivy.animation import Animation
from kivy.core.window import Window
#global
from functools import partial
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
import sqlite3
import logging
#local

#initialize logger
log = logging.getLogger('Switch')
log.setLevel(logging.INFO)
hdlr = logging.FileHandler('data/logs/log.log')
consoleHandler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [%(levelname)-8s] %(module)s%(lineno)-3s %(message)s")
hdlr.setFormatter(formatter)
consoleHandler.setFormatter(formatter)
log.addHandler(hdlr)
log.addHandler(consoleHandler) 
log.info("*-----------Switch(Controller) started-----------*")

#load kv file
Builder.load_file('switcher.kv')

class Switcher(Widget):
    '''This is the "main" class, it handels all the events. Also it displays
    the close button and all the switch uix widgets.
    '''
    switch_open=BooleanProperty(False)
    open_prog_list=[]
    prog_buttons={}
    def __init__(self, k_app, **kwargs):
        super(Switcher, self).__init__(**kwargs)
        self.k_app=k_app
        
        #bind functions
        self.bind(switch_open=self._show_hide_switch)
        
        #remove from kv creation
        self.background.remove_widget(self.background_image)
        self.remove_widget(self.close_switch_button)
        self.remove_widget(self.progs_layout)
        self.remove_widget(self.pbase_button)
        self.remove_widget(self.shutdown_button)
        self.remove_widget(self.popup)
        
        #init dbus client
        self.bus = dbus.SessionBus()
        
        #preload animations
        self.close_switch_animation=Animation(y=Window.height, duration=0.25, transition="in_circ")
        self.close_switch_animation.bind(on_complete=self.close_animation_step1)
        
        #try to fetch open running progs
        server=self.try_reach_dbus_PBController()
        if server:
            progs=server.get_open_progs(dbus_interface = 'org.PB.PBController')
            for prog_id in progs:
                if not prog_id:
                    return
                self.open_prog_list.append(int(prog_id))
        
    def prog_opened(self, prog_id, *kwargs):
        '''This function gets called whenever a prog opens
        If the switch is already open we add a new button (prog icon)
        to the prog layout. If the switch is not already loaded we just
        add the prog_id to a list. In case the switch get opened, we 
        know which prog is open, cause of the list.
        '''
        if int(prog_id)  in self.open_prog_list:
            return
        if self.switch_open:
            name=self.get_prog_info(prog_id)
            path=str("../data/icons/"+str(prog_id)+".png")
            prog={"path":path, "name":name, "prog_id":prog_id}
            self.prog_buttons[prog_id]=Builder.template('ButtonItem', **prog)
            self.prog_buttons[prog_id].bind(on_press=partial(self.open_prog, prog["prog_id"]))
            self.prog_buttons[prog_id].close_prog_button.bind(on_press=partial(self.close_prog, prog["prog_id"]))
            self.progs_layout.add_widget(self.prog_buttons[prog_id])
        self.open_prog_list.append(int(prog_id))
    
    def prog_closed(self, prog_id, *kwargs):
        '''This function gets called whenver a prog closed.
        We remove the button from the switch when it is open.
        Else we just remove the prog_id from the list.
        '''
        if self.switch_open:
            self.progs_layout.remove_widget(self.prog_buttons[prog_id])
        if int(prog_id) in self.open_prog_list:
            self.open_prog_list.remove(int(prog_id))
    
    def close_prog(self, prog_id, *kwargs):
        '''This function sends s signal to the PBController to close 
        the prog.
        '''
        server=self.try_reach_dbus_PBController()
        if server: 
            try:
                server.close_prog(prog_id, dbus_interface = 'org.PB.PBController')
            except dbus.exceptions.DBusException:
                log.exception('dbus close prog exception')
        self.switch_open=False
        
    def open_prog(self, prog_id, *kwargs):
        '''This function sends a signal over DBUS to the PBController to
        open a prog / switching to a open prog.
        '''
        server=self.try_reach_dbus_PBController()
        if server: 
            try:
                server.open_prog(prog_id, dbus_interface = 'org.PB.PBController')
            except dbus.exceptions.DBusException:
                log.exception('dbus open prog eception')
        self.switch_open=False
    
    def show_pbase(self, *kwargs):
        '''This function gets called whenever the button PBase from the switch
        gets touched. This will close the switch and call the function show_pbase
        over D-Bus on PBController.
        '''
        server=self.try_reach_dbus_PBController()
        if server: 
            try:
                server.show_pbase(dbus_interface = 'org.PB.PBController')
            except dbus.exceptions.DBusException:
                log.exception('dbus show pbase exception')
        self.switch_open=False
    
    def request_shutdown(self, *kwargs):
        '''This function gets called whenever the button Shutdown gets pressed
        in the switch. This will show a popup which ask if you are sure to
        shutdown the machine
        '''
        self.popup.open()
    
    def shutdown(self, reboot):
        '''This function should inform the controller to shutdown the device.
        It calls the function shutdown() on PBController session bus.
        '''
        self.popup.dismiss()
        server=self.try_reach_dbus_PBController()
        if server:
            try:
                server.shutdown(reboot, dbus_interface = 'org.PB.PBController')
            except dbus.exceptions.DBusException, e:
                log.exception('Switch: DBUS Error(PBController.shutdown): '+str(e))
        
    def _show_hide_switch(self, wid, open_switch):
        '''This function opens /show and close/hides the switch.
        You shouldn't call this function. Use instead the property switch_open.
        
        :param wid: placeholder for widget passed by bind
        :param open_switch: Bool, True:show-switch
        '''
        if open_switch:
            #stop close animation, if its running
            self.close_switch_animation.stop(self.background_image)
            
            #add widgets for open switch
            self.background.add_widget(self.background_image)
            self.remove_widget(self.open_switch_button)
            self.add_widget(self.close_switch_button)
            self.add_widget(self.progs_layout)
            
            #fetch open progs icons
            prog_icons=[]
            for prog_id in self.open_prog_list:
                name=self.get_prog_info(prog_id)
                path=str("../data/icons/"+str(prog_id)+".png")
                prog_icons.append({"path":path, "name":name, "prog_id":prog_id})
                
            #add open prog icons to layout
            for prog in prog_icons:
                self.prog_buttons[prog_id]=Builder.template('ButtonItem', **prog)
                self.prog_buttons[prog_id].bind(on_press=partial(self.open_prog, prog["prog_id"]))
                self.prog_buttons[prog_id].close_prog_button.bind(on_press=partial(self.close_prog, prog["prog_id"]))
                self.progs_layout.add_widget(self.prog_buttons[prog_id])
            
            #animate open switch
            self.open_switch_animation=Animation(y=Window.height-150, duration=0.25, transition="out_circ")
            self.open_switch_animation.bind(on_complete=self.open_animation_step1)
            open_switch_animation_progs=Animation(y=Window.height-123, duration=0.25, transition="out_circ")
            self.open_switch_animation.start(self.background_image)
            open_switch_animation_progs.start(self.progs_layout)
            
        else:
            #stop open animation
            self.open_switch_animation.stop(self.background_image)
            
            #animate close switch
            self.close_switch_animation.start(self.background_image)
            self.close_switch_animation.start(self.progs_layout)
            
            #remove widgets which belongs to the open switch
            self.add_widget(self.open_switch_button)
            self.remove_widget(self.close_switch_button)
            self.progs_layout.clear_widgets()
            self.remove_widget(self.pbase_button)
            self.remove_widget(self.shutdown_button)
    
    def open_animation_step1(self, *kwargs):
        '''Internal function. Gets called as soon the open animation finshed
        '''
        self.add_widget(self.pbase_button)
        self.add_widget(self.shutdown_button)
        
    def close_animation_step1(self, *kwargs):
        '''Internal function. Gets called as soon the close animation finshed
        '''
        self.background.remove_widget(self.background_image)
        self.remove_widget(self.progs_layout)
    
    def try_reach_dbus_PBController(self):
        '''Int this function we try to reach the PBController via dbus.
        
        :return server: the server instance from dbus.
        '''
        try:
            server = self.bus.get_object('org.PB.PBController', '/PBController')
        except dbus.exceptions.DBusException:
            log.exception('try reaching dbus failed:')
            return False
        return server
    
    def get_prog_info(self, prog_id):
        '''This function gets all the informations from the DB.
        
        :param prog_id: id of the prog
        :return name: name
        '''
        DB_connection = sqlite3.connect("../PBase/data/database.sqlite")
        DB_cursor = DB_connection.cursor()
        DB_cursor.execute("SELECT name FROM progs WHERE id = '%i'" %prog_id)
        DB_connection.commit()
        for row in DB_cursor: name=row[0]
        DB_connection.close()
        return name

class DBusServer(dbus.service.Object):
    '''DBus server from switch.
    Reachable under session bus: org.PB.PBSwitch (/PBSwitch)
    '''
    def __init__(self, switch):
        '''Initialize the session bus under:
        org.PB.PBase
        
        :param pbase: PBase object
        '''
        self.switch=switch
        bus_name = dbus.service.BusName('org.PB.PBSwitch', bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/PBSwitch')
 
    @dbus.service.method('org.PB.PBSwitch')
    def prog_opened(self, prog_id):
        '''This function gets called whenever a prog got opened. 
        (normally from PBController)
        
        :param prog_id: id of prog
        '''
        Clock.schedule_once(partial(self.switch.prog_opened, prog_id), 0)
        return
    
    @dbus.service.method('org.PB.PBSwitch')
    def prog_closed(self, prog_id):
        '''This function gets called whenever a prog got closed. 
        (normally from PBController)
        
        :param prog_id: id of prog
        '''
        Clock.schedule_once(partial(self.switch.prog_closed, prog_id), 0)
        return
    
DBusGMainLoop(set_as_default=True)

class SwitchApp(App):
    title="PBSwitch"
    def build(self):
        install_gobject_iteration()
        switch=Switcher(k_app=self)
        DBusServer(switch=switch)          
        return switch
    
if __name__ == '__main__':
    SwitchApp().run()