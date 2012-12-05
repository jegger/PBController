#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#===============================================================================
# Written by Rentouch 2012 - http://www.rentouch.ch
#===============================================================================

import os
import shutil

def install():
    #search pbase folder
    home=os.path.expanduser("~")
    git=os.getcwd()
    if not os.path.isdir(os.path.join(home, "PBase")):
        print "can not locate ~/PBase folder"
        return
    
    #create PBase/PBController folder if it doesn't exist
    if not os.path.isdir(os.path.join(home, "PBase/PBController")):
        os.mkdir(os.path.join(home, "PBase/PBController"))
    
    #change to the PBase/PBController directory
    os.chdir(os.path.join(home, "PBase/PBController"))
    
    #check for dev-version file
    #if it exists, don't install!- it means that it is a developement version
    if os.path.isfile('dev-version'):
        print "Don't install! - dev-version file found"
        return
    
    #check if data directory already exist, if not create it with initial 
    if not os.path.isdir("data"):
        shutil.copytree(os.path.join(git, "data"), "data")
    
    #overwrite all files except
    for filename in os.listdir(git):
        if os.path.isfile(os.path.join(git, filename)) and filename[0]!=".":
            if os.path.isfile(filename):
                os.remove(filename)
            shutil.copy(os.path.join(git, filename), filename)
    
    #overwrite all folders except data
    for foldername in os.listdir(git):
        if os.path.isdir(os.path.join(git, foldername)) and foldername[0]!=".":
            if foldername!="data":
                if os.path.isdir(foldername):
                    shutil.rmtree(foldername)
                shutil.copytree(os.path.join(git, foldername), foldername)
                
install()