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
you can also close progs from probazaar.ch remotely.

XLib & touch converting
~~~~~~~~~~~~~~~~~~~~~~
This is kind a ugly solution.
I would be glad if someone could rewrite/re-think this! 

XLib is used for positioning the kivy switch window.
Because the window is not fullscreen and not starting on pos:0,0 we have to
re-write the touch handling and scale the touches up to the real screen size.
Also we have to set the x:0,y:0 point of the touches to the position of the
window.

'''
#kivy
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.support import install_gobject_iteration
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, ListProperty
from kivy.input.motionevent import MotionEvent
from kivy.input.providers.tuio import TuioMotionEventProvider
#global
from functools import partial
import dbus.service
import subprocess
from dbus.mainloop.glib import DBusGMainLoop
import sqlite3
#local
import kivyXwm

#create GLOBAL variables
wind_pos=(760,980) #position of the switch window
wind_size=(400,100) #size of the switch window

#load kv file
Builder.load_file('switcher.kv')

class Switcher(Widget):
    '''This is the "main" class, it handels all the events. Also it displays
    the close button and all the switch uix widgets.
    '''
    switch_open=BooleanProperty(False)
    window_pos_size=ListProperty((0,0,50,50))
    open_prog_list=[]
    prog_buttons={}
    def __init__(self, k_app, **kwargs):
        super(Switcher, self).__init__(**kwargs)
        self.k_app=k_app
        
        #bind functions
        self.bind(switch_open=self._show_hide_switch)
        self.bind(window_pos_size=self.actualize_window)
        
        #remove from kv creation
        self.background.remove_widget(self.background_image)
        self.remove_widget(self.close_switch_button)
        self.remove_widget(self.progs_layout)
        self.remove_widget(self.pbase_button)
        
        #init dbus client
        self.bus = dbus.SessionBus()
        
        #try to fetch open running progs
        server=self.try_reach_dbus_PBController()
        if server:
            try:
                progs=server.get_open_progs(dbus_interface = 'org.PB.PBController')
                for prog_id in progs:
                    self.open_prog_list.append(int(prog_id))
            except dbus.exceptions.DBusException, e:
                print e
            
        #actualize window after creation
        Clock.schedule_once(self.show_switch_button, 0)
    
    def show_switch_button(self, *kwargs):
        '''This button gets called a frame after the creation of the window.
        We have to wait, cause only then we can repositionize the window
        with XLib.
        '''
        self.screen_size=self.k_app.get_screen_size()
        self.window_pos_size[0]=self.screen_size[0]-100
        self.window_pos_size[1]=self.screen_size[1]-100
        
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
            except dbus.exceptions.DBusException, e:
                print e
        self.switch_open=False
        
    def open_prog(self, prog_id, *kwargs):
        '''This function sends a signal over DBUS to the PBController to
        open a prog / switching to a open prog.
        '''
        server=self.try_reach_dbus_PBController()
        if server: 
            try:
                server.open_prog(prog_id, dbus_interface = 'org.PB.PBController')
            except dbus.exceptions.DBusException, e:
                print e
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
            except dbus.exceptions.DBusException, e:
                print e
        self.switch_open=False
        
    def _show_hide_switch(self, wid, open_switch):
        '''This function opens /show and close/hides the switch.
        You shouldn't call this function. Use instead the property switch_open.
        
        :param wid: placeholder for widget passed by bind
        :param open_switch: Bool, True:show-switch
        '''
        if open_switch:
            self.window_pos_size=(0,
                                 self.screen_size[1]-150,
                                 self.screen_size[0],
                                 150)
            self.background.add_widget(self.background_image)
            self.remove_widget(self.open_switch_button)
            self.add_widget(self.close_switch_button)
            self.add_widget(self.progs_layout)
            self.add_widget(self.pbase_button)
            
            prog_icons=[]
            for prog_id in self.open_prog_list:
                name=self.get_prog_info(prog_id)
                path=str("../data/icons/"+str(prog_id)+".png")
                prog_icons.append({"path":path, "name":name, "prog_id":prog_id})
                
            for prog in prog_icons:
                self.prog_buttons[prog_id]=Builder.template('ButtonItem', **prog)
                self.prog_buttons[prog_id].bind(on_press=partial(self.open_prog, prog["prog_id"]))
                self.prog_buttons[prog_id].close_prog_button.bind(on_press=partial(self.close_prog, prog["prog_id"]))
                self.progs_layout.add_widget(self.prog_buttons[prog_id])
        else:
            self.window_pos_size=(self.screen_size[0]-100,
                                 self.screen_size[1]-100,
                                 50,
                                 50)
            self.background.remove_widget(self.background_image)
            self.add_widget(self.open_switch_button)
            self.remove_widget(self.close_switch_button)
            self.progs_layout.clear_widgets()
            self.remove_widget(self.pbase_button)
            self.remove_widget(self.progs_layout)
    
    def actualize_window(self, *kwargs):
        '''This function gets trugh the bind on:
        window_pos_size called. The function resizes the window.
        '''
        self.k_app.actualize_window(x=self.window_pos_size[0], 
                                     y=self.window_pos_size[1],
                                     width=self.window_pos_size[2], 
                                     height=self.window_pos_size[3])
    
    def try_reach_dbus_PBController(self):
        '''Int this function we try to reach the PBController via dbus.
        
        :return server: the server instance from dbus.
        '''
        try:
            server = self.bus.get_object('org.PB.PBController', '/PBController')
        except dbus.exceptions.DBusException:
            print "Can not reach DBUS PBController"
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
        
    def actualize_window(self, x=int, y=int, width=int, height=int):
        '''This function actualizes the window pos and size over XLib
        
        :param x: x pos of window
        :param y: y pos of window
        :param width: width of window
        :param height: height of window
        '''
        #check if arguments are passed, if not do not change
        if x==int: x=wind_pos[0]
        if y==int: y=wind_pos[1]
        if width==int: width=wind_size[0]
        if height==int: height=wind_size[1]
        #repositionize/resize window over XLib
        kivyXwm.repositionize(self.title, x, y, width, height)
        #rewrite globals
        global wind_pos
        global wind_size
        wind_pos=(x, y)
        wind_size=(width, height)
    
    def get_screen_size(self):
        '''This function returns the screen size.
        
        :return size: (height. width) as a tuple
        '''
        proc = subprocess.Popen("xrandr | grep '*'", shell=True, stdout=subprocess.PIPE)
        proc.wait()
        for line in proc.stdout:
            height=int(line.split("x")[1].split(" ")[0])
            width=int(line.split("x")[0].split(" ")[-1])
        return (width, height)

#################### Coordinate transformation / Window handling #############
class Tuio2dCurMotionEvent(MotionEvent):
    def __init__(self, device, id, args):
        super(Tuio2dCurMotionEvent, self).__init__(device, id, args)

    def depack(self, args):
        self.is_touch = True
        if len(args) < 5:
            self.sx, self.sy = map(float, args[0:2])
            self.profile = ('pos', )
        elif len(args) == 5:
            self.sx, self.sy, self.X, self.Y, self.m = map(float, args[0:5])
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc')
        else:
            self.sx, self.sy, self.X, self.Y = map(float, args[0:4])
            self.m, width, height = map(float, args[4:7])
            self.Y = -self.Y
            self.profile = ('pos', 'mov', 'motacc', 'shape')
            if self.shape is None:
                self.shape = ShapeRect()
            self.shape.width = width
            self.shape.height = height
        self.sy = 1 - self.sy
        super(Tuio2dCurMotionEvent, self).depack(args)

    def scale_for_screen(self, w, h, p=None, rotation=0):
        '''Scale position for the screen
        '''
        sx, sy = self.sx, self.sy
        if rotation == 0:
            self.x = sx * float(1920)
            self.y = sy * float(1080)
            self.x = self.x - float(wind_pos[0])
            self.y = self.y - float(wind_pos[1])
        elif rotation == 90:
            sx, sy = sy, 1 - sx
            self.x = sx * float(h)
            self.y = sy * float(w)
        elif rotation == 180:
            sx, sy = 1 - sx, 1 - sy
            self.x = sx * float(w)
            self.y = sy * float(h)
        elif rotation == 270:
            sx, sy = 1 - sy, sx
            self.x = sx * float(h)
            self.y = sy * float(w)

        if p:
            self.z = self.sz * float(p)
        if self.ox is None:
            self.px = self.ox = self.x
            self.py = self.oy = self.y
            self.pz = self.oz = self.z

        self.dx = self.x - self.px
        self.dy = self.y - self.py
        self.dz = self.z - self.pz
TuioMotionEventProvider.register('/tuio/2Dcur', Tuio2dCurMotionEvent)  
    
if __name__ == '__main__':
    SwitchApp().run()