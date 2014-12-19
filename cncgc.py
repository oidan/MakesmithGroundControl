﻿'''This file is part of the Makesmith Ground Control Software.

The Makesmith Ground Control Software is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Makesmith Ground Control Software is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with the Makesmith Ground Control Software.  If not, see <http://www.gnu.org/licenses/>.

Copyright 2014 Bar Smith'''

from tkinter import *
from tkinter import filedialog
from tkinter import messagebox
root = Tk()
import re
import threading
import queue
import math
#import time
from time import gmtime, strftime
from time import time
import serial
global serialCAN
import serial.tools.list_ports


class Data( ):
	def __init__(self):
		self.version = '0.58'
		#Gcodes contains all of the lines of gcode in the opened file
		self.gcode = []
		#all of the available COM ports
		self.comPorts = []
		#A flag to indicate if logging is enabled
		self.logflag = 0
		#A flag to indicate if the main window should auto scroll
		self.scrollFlag = 1
		#The file where logging will take place if it is turned on
		self.logfile = None
		#This defines which COM port is used
		self.comport = "" 
		#The index of the next unread line of Gcode
		self.gcodeIndex = 0
		#The amount to move from one step
		self.stepsizeval = 1
		#Holds the current value of the feed rate
		self.feedRate = 20
		#holds the address of the g-code file so that the gcode can be refreshed
		self.gcodeFile = ""
		#sets a flag if the gcode is being uploaded currently
		self.uploadFlag = 0
		#flag is 1 if the machine is ready for a command
		self.readyFlag = 0
		#the current position of the cutting head
		self.currentpos = [0.0, 0.0, 0.0]
		self.target = [0.0, 0.0, 0.0]
		#click values for drag window
		self.xclickstart = 0
		self.xclickend = 0
		self.yclickstart = 0
		self.yclickend = 0
		self.offsetX = 0
		self.offsetY = 0 #was -200 
		#Zoom level
		self.zoomLevel = 4.9 #4.9 is real size on my monitor
		self.unitsScale = 1/1.27 #this sets the values for inches and mm 
		#Tool Width and Color Flags
		self.toolWidthFlag = 0
		self.colorFlag = 0
		self.spindleFlag = 1
		self.prependString = " "
		self.absoluteFlag = 1
		self.unitsSetFlag = 0 #used once to set the correct units on the machine
		self.startTime = 0
		self.endTime = 0
		self.xDrag = 0
		self.yDrag = 0
		self.saveFlag = 1 #program saves when flag is 1
		self.appData = ""
		self.contrast = 50
		self.backlight = 65
		self.heartBeat = time()


class MainProgram( Frame ):

	''' ------------------------------------------------------------------------------------
	These are the back-end functions (These are functions which are called by other functions)
	----------------------------------------------------------------------------------------'''
	#This initializes the Tkinter GUI
	def __init__( self, dataBack ):
		Frame.__init__( self )
		
		if sys.platform.startswith('win'):
			self.master.wm_state('zoomed') #This did not work on ubuntu
		elif sys.platform.startswith('linux'):
			self.master.attributes('-zoomed', True)
		
		self.master.title( "Makesmith Ground Control - Software is still beta, please use with caution" )
		
		self.dataBack = dataBack
		self.message_queue = queue.Queue()
		self.gcode_queue = queue.Queue()
		self.quick_queue = queue.Queue()
		
		self.menu = Menu(self)
		self.master.config(menu = self.menu)
		#This code creates the menu system
		self.file = Menu(self.menu)
		self.menu.add_cascade(label = 'File', menu = self.file)
		self.file.add_command(label = 'Quit', command = self.quit)
		self.file.add_command(label = 'Open G-Code', command = self.loadGcode)
		self.file.add_command(label = 'Run G-Code', command = self.beginGcodeRun)
		#self.file.add_command(label = 'Reset Index', command = self.resetcount)
		self.file.add_command(label = 'Begin Logging', command = self.beginLoging)
		self.file.add_command(label = 'End Logging', command = self.endLog)
		self.file.add_command(label = 'Reconnect to CNC', command = self.recievemessage)
		#self.file.add_command(label = 'Save Settings', command = self.savesettings)
		#self.file.add_command(label = 'Load Settings', command = self.loadsettings)
		
		
		self.runmen = Menu(self.menu)
		self.menu.add_cascade(label = 'Run', menu = self.runmen)
		self.runmen.add_command(label = 'Run G-Code', command = self.beginGcodeRun)
		self.runmen.add_command(label = 'Pause', command = self.pause)
		self.runmen.add_command(label = 'Resume', command = self.unpause)
		#self.runmen.add_command(label = 'Force Resume', command = self.forceResume)
		self.runmen.add_command(label = 'Zero Z', command = self.reZeroZ)
		#self.runmen.add_command(label = 'Reset Index', command = self.resetcount)
		self.runmen.add_command(label = 'Diagnostics', command = self.autoDebug)
		self.runmen.add_command(label = 'Switch to Millimetres', command = self.switchmm)
		self.runmen.add_command(label = 'Switch to Inches', command = self.switchinches)
		
		self.view = Menu(self.menu)
		self.menu.add_cascade(label = 'View', menu = self.view)
		self.view.add_command(label = '600% Zoom', command = lambda: self.zoomset(6))
		self.view.add_command(label = '400% Zoom', command = lambda: self.zoomset(4))
		self.view.add_command(label = '200% Zoom', command = lambda: self.zoomset(2))
		self.view.add_command(label = '100% Zoom', command = lambda: self.zoomset(1))
		self.view.add_command(label = '75% Zoom', command = lambda: self.zoomset(.75))
		self.view.add_command(label = '50% Zoom', command = lambda: self.zoomset(.5))
		self.view.add_command(label = '25% Zoom', command = lambda: self.zoomset(.25))
		self.view.add_command(label = 'Reset Origin', command = self.resetOrigin)
		#self.view.add_command(label = 'Display Settings', command = self.updateSettings)
		#self.view.add_command(label = 'Toggle Tool Width', command = self.tool_width_toggle)
		#self.view.add_command(label = 'Toggle Color', command = self.color_toggle)
		self.view.add_command(label =  'Version (' + self.dataBack.version + ')', command = self.versionNumber)
		self.view.add_command(label = 'Update Gcode', command = self.reloadGcode)
		self.view.add_command(label = 'View Gcode', command = self.viewGcode)
		
		self.com = Menu(self.menu)
		self.menu.add_cascade(label = 'Port', menu = self.com)
		self.com.add_command(label = 'Update List', command = self.detectCOMports)
		
		self.help = Menu(self.menu)
		self.menu.add_cascade(label = 'Help', menu = self.help)
		self.help.add_command(label = 'About', command = self.aboutDialog)

		
		self.canvas_frame = Frame(root)
		self.canvas_frame.pack(fill=BOTH, expand = 1, anchor = 'nw', side = LEFT) 
		
		self.canv = Canvas(self.canvas_frame, width=300, height=300, bg = "grey95", yscrollincrement='2', xscrollincrement='2') 
		self.canv.pack(fill=BOTH, expand = 1)
		
		self.canv.bind("<Button 1>",self.grab)
		self.canv.bind("<B1-Motion>",self.drag)
		root.bind("<MouseWheel>", self.mouse_wheel)
		# with Linux OS
		root.bind("<Button-4>", self.mouse_wheel)
		root.bind("<Button-5>", self.mouse_wheel)
		
		self.control_frame = Frame(self.canv, bg = "grey95")
		self.control_frame.pack(expand=NO, anchor = 'ne', pady = 10) 
		
		self.top_frame = Frame(self.control_frame, height=150, bg = "grey95")
		self.top_frame.pack(expand=NO, anchor = 'nw') 
		
		self.middle_frame = Frame(self.control_frame, height=150, bg = "grey95")
		self.middle_frame.pack(expand=NO,  anchor = 'nw') 
		
		self.bottom_frame = Frame(self.control_frame, height=150, bg = "grey95")
		self.bottom_frame.pack(expand=NO,  anchor = 'nw') 
		
		self.set_frame = Frame(self.control_frame, bg = "grey95")
		self.set_frame.pack(expand=NO,  anchor = 'nw')
		
		self.aux_frame = Frame(self.control_frame, bg = "grey95")
		self.aux_frame.pack(expand=NO,  anchor = 'nw')

		self.info_frame = Frame(self.canv, height = 150, width = 150, bg = "grey95")
		self.info_frame.pack(expand=NO, anchor = 'ne', pady = 15)
		
		self.POZ_frame = Frame(self.info_frame, height=150, width = 150, padx = 10, bg = "grey95")
		self.POZ_frame.pack(expand=NO,  anchor = 'nw', side = LEFT, padx = 15) 
		
		self.ETD_frame = Frame(self.info_frame, height = 150, width = 150 , bg = "grey95")
		self.ETD_frame.pack(expand=NO,  anchor = 'nw', side = LEFT, padx = 15)
		
		self.terminal_frame = Frame(self.canv, height=150, width = 550, padx = 25, bg = "grey95")
		self.terminal_frame.pack( anchor = 'ne')
		 
		self.spy_frame = Frame(self.canv, height=75, width = 150, bg = "grey95")
		self.spy_frame.pack(expand = NO,  anchor = 'ne') 
		
		self.buttonwidth = 10
		self.buttonHeight = 3
		self.moveColor = "gray68"
		self.setColor = "gray58"
		
		
		self.ul = Button(self.top_frame , text = "<^", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.ul["command"] = self.ulb
		self.ul.pack(side = LEFT)
		
		self.back = Button(self.top_frame, text = "^ +", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.back["command"] = self.forwardb
		self.back.pack(side = LEFT)
		
		self.ur = Button(self.top_frame, text = "^>", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.ur["command"] = self.urb
		self.ur.pack(side = LEFT)
		
		self.up = Button(self.top_frame, text = "up", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.up["command"] = self.upb
		self.up.pack(side = LEFT)
		
		self.testbtn = Button( self.set_frame, text = "Toggle\nSpindle", bg = self.setColor, width = self.buttonwidth, height = self.buttonHeight)
		self.testbtn["command"] = self.toggleSpindle
		self.testbtn.pack(side = LEFT)
		
		self.left = Button(self.middle_frame, text = "<", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.left["command"] = self.leftb
		self.left.pack(side = LEFT)
		
		self.home = Button(self.middle_frame, text = "HOME", bg = self.setColor, width = self.buttonwidth, height = self.buttonHeight)
		self.home["command"] = self.homebtn
		self.home.pack(side = LEFT)
		
		
		self.right = Button(self.middle_frame, text = ">", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.right["command"] = self.rightb
		self.right.pack(side = LEFT)
		
		self.down = Button( self.middle_frame, text = "down", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.down["command"] = self.downb
		self.down.pack(side = LEFT)
		
		self.testbtn2 = Button(self.set_frame, text = "Re-Zero", bg = self.setColor, width = self.buttonwidth, height = self.buttonHeight)
		self.testbtn2["command"] = self.reZero
		self.testbtn2.pack(side = LEFT)
		
		self.dl = Button( self.bottom_frame, text = "<V", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.dl["command"] = self.dlb
		self.dl.pack(side = LEFT)
		
		self.forward = Button( self.bottom_frame, text = "v -", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.forward["command"] = self.backb
		self.forward.pack(side = LEFT)
		
		self.dr = Button(  self.bottom_frame, text = "V>", bg = self.moveColor, width = self.buttonwidth, height = self.buttonHeight)
		self.dr["command"] = self.drb
		self.dr.pack(side = LEFT)
		
		self.inc = Button( self.bottom_frame, text = "Stop", bg = "orange red", width = self.buttonwidth, height = self.buttonHeight)
		self.inc["command"] = self.stoprun
		self.inc.pack(side = LEFT)
		
		self.scrollbtn = Button(self.set_frame, text = "Scroll\nEnable", bg = self.setColor, width = self.buttonwidth, height = self.buttonHeight)
		self.scrollbtn["command"] = self.scrollactive
		self.scrollbtn.pack(side = LEFT)
		
		self.stepsize = Spinbox(self.aux_frame, from_ = 1, to = 100, width = 16)
		self.stepsize.pack(side = LEFT, padx = 8)
		
		self.speed = Spinbox(self.aux_frame, from_ = 0, to = 125, width = 16)
		self.speed.delete(0,"end")
		self.speed.insert(0,125)
		self.speed.pack(side = LEFT, padx = 8)
		
		#This is the text box which contains the messages too and from the machine
		self.output = Text( self.spy_frame, width = 37, height = 14, background = "grey95", relief = FLAT)
		self.output.pack(fill = Y, expand = YES)
		
		self.IncSend = Button( self.set_frame, text = "Run", bg = self.setColor, width = self.buttonwidth, height = self.buttonHeight)
		self.IncSend["command"] = self.beginGcodeRun
		self.IncSend.pack(side = LEFT)
		
		self.xposdispval = StringVar()
		self.xposdispval.set("0.00")
		self.xpos = Label(self, textvariable = self.xposdispval, font=("Stencil", 18), fg = "black")
		
		
		self.yposdispval = StringVar()
		self.yposdispval.set("0.00")
		self.ypos = Label(self, textvariable = self.yposdispval, font=("Stencil", 18), fg = "black")
		
		self.zposdispval = StringVar()
		self.zposdispval.set("0.00")
		self.zpos = Label(self, textvariable = self.zposdispval, font=("Stencil", 18), fg = "black")
		
		self.xposdispvalin = StringVar()
		self.xposdispvalin.set("0.0 mm")
		self.xposin = Label(self.POZ_frame, textvariable = self.xposdispvalin, font=("Stencil", 18), fg = "black", bg = "grey95")
		self.xposin.pack()
		
		self.yposdispvalin = StringVar()
		self.yposdispvalin.set("0.0 mm")
		self.yposin = Label(self.POZ_frame, textvariable = self.yposdispvalin, font=("Stencil", 18), fg = "black", bg = "grey95")
		self.yposin.pack()
		
		self.zposdispvalin = StringVar()
		self.zposdispvalin.set("0.0 mm")
		self.zposin = Label(self.POZ_frame, textvariable = self.zposdispvalin, font=("Stencil", 18), fg = "black", bg = "grey95")
		self.zposin.pack()
		
		self.timewords = StringVar()
		self.timewords.set("Est Time Remaining:")
		self.timenote = Label(self.ETD_frame, textvariable = self.timewords, font=("Times New Roman", 10), fg = "black", bg = "grey95")
		self.timenote.pack()
		
		self.timeleft = StringVar()
		self.timeleft.set("TBD")
		self.timelft = Label(self.ETD_frame, textvariable = self.timeleft, font=("Times New Roman", 18), fg = "black", bg = "grey95")
		self.timelft.pack()
		
		self.timedisp = StringVar()
		self.timedisp.set(0)
		self.timedsp = Label(self.ETD_frame, textvariable = self.timedisp, font=("Times New Roman", 18), fg = "black", bg = "grey95")
		self.timedsp.pack()
		
		self.terminaltext = StringVar()
		self.terminal = Label(self.terminal_frame, textvariable = self.terminaltext, font=("Times New Roman", 16), fg = "black", bg = "grey95", width = 25, anchor = E, justify = RIGHT)
		self.terminal.pack(fill = BOTH, expand = 1)
		
		
		self.setupSettingsFile()
		self.showCanvas()
		self.loadsettings()
		self.savesettings()
		self.refreshout()
		self.refreshGcode()
		self.detectCOMports()
		self.recievemessage() #This checks if the CNC is hooked up and establishes a connection if it is
		
	
	def aboutDialog(self):
		messagebox.showinfo("About","Makesmith Ground Control\nSoftware Version: "+self.dataBack.version)

	#This sets up the file where the program settings are saved if it does not already exist
	def setupSettingsFile(self):
		APPNAME = "Makesmith"
		import sys
		from os import path, environ
		import os
		if sys.platform == 'darwin':
			from AppKit import NSSearchPathForDirectoriesInDomains
			appdata = path.join(NSSearchPathForDirectoriesInDomains(14, 1, True)[0], APPNAME)
		elif sys.platform == 'win32':
			appdata = path.join(environ['APPDATA'], APPNAME)
		else:
			appdata = path.expanduser(path.join("~", "." + APPNAME))
		self.dataBack.settingsFile = appdata + "\Settings.txt"
		if not os.path.exists(appdata):
			os.makedirs(appdata)
		if not os.path.exists(self.dataBack.settingsFile):
			open(self.dataBack.settingsFile, 'w+')
	
	#Saves the program settings
	def savesettings(self):
		root.after(10000,self.savesettings)
		if self.dataBack.saveFlag == 1:
			settings = open(self.dataBack.settingsFile, 'w') #Opens the provided file name for writing which will replace any existing data
			settings.write(self.dataBack.comport + "\n")
			settings.write(self.dataBack.gcodeFile + "\n")
			settings.write(str(self.dataBack.stepsizeval) + "\n")
			settings.write(str(self.dataBack.feedRate) + "\n")
			settings.write(str(self.dataBack.currentpos[0]) + "\n")
			settings.write(str(self.dataBack.currentpos[1]) + "\n")
			settings.write(str(self.dataBack.currentpos[2]) + "\n")
			settings.write(str(self.dataBack.zoomLevel) + "\n")
			settings.write(str(self.dataBack.unitsScale) + "\n")
			settings.write(str(self.dataBack.toolWidthFlag) + "\n")
			settings.write(str(self.dataBack.colorFlag) + "\n")
			settings.write(str(self.dataBack.absoluteFlag) + "\n")
			settings.write(str(int(self.dataBack.xDrag)) + "\n")
			settings.write(str(int(self.dataBack.yDrag)) + "\n")
			settings.write(str(int(self.dataBack.backlight)) + "\n")
			settings.write(str(int(self.dataBack.contrast)) + "\n")
			settings.close()
			self.dataBack.saveFlag = 0
		
	#This loads the program settings from memory during startup 
	def loadsettings(self):
		try:
			settingsfile = open(self.dataBack.settingsFile, 'r+')
			rawsettings = settingsfile.read()
			settingsparsed = rawsettings.split("\n") #splits the filters into elements to be added to the list
			if len(settingsparsed) >= 5:
				self.dataBack.comport = settingsparsed[0]
				self.dataBack.gcodeFile = settingsparsed[1]
				
				self.dataBack.stepsizeval = float(settingsparsed[2])
				self.dataBack.feedRate = float(settingsparsed[3])
				#self.dataBack.currentpos[0] = float(settingsparsed[4])
				#self.dataBack.currentpos[1] = float(settingsparsed[5])
				#self.dataBack.currentpos[2] = float(settingsparsed[6])
				self.dataBack.zoomLevel = float(settingsparsed[7])
				self.dataBack.xDrag = int(settingsparsed[12])
				self.dataBack.yDrag = int(settingsparsed[13])
				self.dataBack.backlight = int(settingsparsed[14])
				self.dataBack.contrast = int(settingsparsed[15])
			
			settingsfile.close() #closes the filter save file
			self.reloadGcode() 
			self.speed.delete(0,"end")
			self.speed.insert(0,self.dataBack.feedRate)
			self.stepsize.delete(0,"end")
			self.stepsize.insert(0,self.dataBack.stepsizeval)
			root.after(200,self.moveToStart)
		except:
			print("Issue Opening Settings")
	
	def switchmm(self):
		self.gcode_queue.put("G21 ")
		self.dataBack.unitsScale = 1/1.27
		self.dataBack.target[0] = self.dataBack.target[0] * 25.4
		self.dataBack.target[1] = self.dataBack.target[1] * 25.4
		self.dataBack.target[2] = self.dataBack.target[2] * 25.4
	
	def switchinches(self):
		self.gcode_queue.put("G20 ")
		self.dataBack.unitsScale = 20
		self.dataBack.target[0] = self.dataBack.target[0] * 0.039370
		self.dataBack.target[1] = self.dataBack.target[1] * 0.039370
		self.dataBack.target[2] = self.dataBack.target[2] * 0.039370
	
	#Detects all the devices connected to the computer. Returns them as an array.
	def listSerialPorts(self):
		import glob
		if sys.platform.startswith('win'):
			ports = ['COM' + str(i + 1) for i in range(256)]

		elif sys.platform.startswith('linux'):
			# this is to exclude your current terminal "/dev/tty"
			ports = glob.glob('/dev/tty[A-Za-z]*')

		elif sys.platform.startswith('darwin'):
			ports = glob.glob('/dev/tty.*')

		else:
			raise EnvironmentError('Unsupported platform')

		result = []
		for port in ports:
			try:
				s = serial.Serial(port)
				s.close()
				result.append(port)
			except (OSError, serial.SerialException):
				pass
			except (ValueError):
				print("Port find error")
		return result
	
	#Runs every two seconds to detect if any new devices are connected
	def detectCOMports(self):
		if sys.platform.startswith('win'):
			root.after(2000,self.detectCOMports)
		x = []
		
		altPorts = self.listSerialPorts()
		for z in altPorts:
			x.append((z,z))
		
		self.dataBack.comPorts = x
		
		self.com.delete(0,END)
		for y in self.dataBack.comPorts:
			self.com.add_command(label = y[1], command = lambda y=y: self.comset(str(y[0])))
		self.com.add_command(label = 'Specify', command = self.forceCOMconnect)
		self.com.add_command(label = 'Update List', command = self.detectCOMports)
	
	#This allows settings within the machine (like PID gains) from the computer side software
	def pushSettingsToMachine (self):
		try:
			contrast = self.contrastValue.get()
			backlight = self.backlightValue.get()
			self.dataBack.contrast = contrast
			self.dataBack.backlight = backlight
		except:
			#print("update display issue")
			pass;
		
		self.gcode_queue.put("B01 C" + str(self.dataBack.backlight) + " ")
		
		from time import sleep
		sleep(.25)
		
		self.gcode_queue.put("B02 C" + str(self.dataBack.contrast) + " ")
		
	#This sends the next line of gcode and increments the gcode pointer in dataBack
	def sendandinc(self):
		
		timeElap = time() - self.dataBack.startTime
		percentDone = (self.dataBack.gcodeIndex/(len(self.dataBack.gcode)-6))*100
		if(percentDone == 0): #div0 problems
			percentDone = 1
		eTComp = (timeElap*(100 - percentDone))/percentDone
		if (self.dataBack.gcodeIndex >= 18):
			if eTComp < 0:
				self.timeleft.set("0")
			else:
				self.timeleft.set(("%.2f" % (eTComp/60)))
		else:
			self.timeleft.set("Estimating...")
		#timeDispString = "%10.1f Min" % (timeElap/60)
		
		self.sendonegcode()
		
	'''This pulls the value from the scroll box which sets how far the CNC moves when you click 
	an arrow button and commands the machine to move that amount. It is called every time you 
	click an arrow button.'''
	def jmpsize(self):
		self.dataBack.stepsizeval = self.stepsize.get()
		self.dataBack.feedRate = self.speed.get()
		self.dataBack.saveFlag = 1
		
	#This function opens the thread which handles the input from the serial port
	#It only needs to be run once, it is run by connecting to the machine
	def recievemessage(self):
		print("Starting Second Thread")
		#self.message_queue is the queue which handles passing CAN messages between threads
		x = SerialPort( self.message_queue, self.gcode_queue, self, self.dataBack.comport, self.quick_queue)
		self.th=threading.Thread(target=x.getmessage)
		self.th.daemon = True
		self.th.start()
		
	'''angleGet returns the angle from the positive x axis to a point given the center of the circle 
	and the point. It is called when plotting circles in the drawGcode() function.'''
	def angleGet(self, X, Y, centerX, centerY):
		'''print("BEGIN")
		print(X)
		print(Y)
		print(centerX)
		print(centerY)'''
		
		if X == centerX: #this resolves /div0 errors
			#print("special case X")
			if Y >= centerY:
				#print("special case one")
				return(1.5)
			if Y <= centerY:
				#print("special case two")
				return(.5)
		if Y == centerY: #this resolves /div0 errors
			#print("special case Y")
			if X >= centerX:
				#print("special case three")
				return(0)
			if X <= centerX:
				#print("special case four")
				return(1.0)
		if X > centerX and Y > centerY: #quadrant one
			#print("Quadrant 1")
			theta = math.atan((centerY - Y)/(X - centerX))
			theta = 2 + theta/math.pi
		if X < centerX and Y > centerY: #quadrant two
			#print("Quadrant 2")
			theta = math.atan((Y - centerY)/(X - centerX))
			theta = 1 - theta/math.pi
		if X < centerX and Y < centerY: #quadrant three
			#print("Quadrant 3")
			theta = math.atan((Y - centerY)/(X - centerX))
			theta = 1 - theta/math.pi
		if X > centerX and Y < centerY: #quadrant four
			#print("Quadrant 4")
			theta = math.atan((centerY - Y)/(X - centerX))
			theta = theta/math.pi
		#print(theta)
		return(theta)	
	
	#This updates the digital read out on the computer and moves the cross-hairs on the GUI
	def updatePosView(self, poString):
		#print("function ran")
		#print(poString)
		try:
			startpt = poString.find('(')
			startpt = startpt + 1
			
			endpt = poString.find(')')
			
			numz = poString[startpt:endpt]
			#print(numz)
			
			valz = numz.split(",")
			
			#print(valz)
			
			self.xposdispval.set(-1*float(valz[0]))
			self.yposdispval.set(valz[1])
			self.zposdispval.set(valz[2])
			
			xval = float(valz[0])
			yval = float(valz[1])
			zval = float(valz[2])
			
			self.dataBack.currentpos[0] = xval
			self.dataBack.currentpos[1] = yval
			self.dataBack.currentpos[2] = zval
		except:
			print("poz decode issue")
			xval = self.dataBack.currentpos[0]
			yval = self.dataBack.currentpos[1]
			zval = self.dataBack.currentpos[2]
		
		try:
			self.refreshCross()
		except:
			print("r cross issue")
		
		#print(self.dataBack.currentpos)
		
		#this was the old code for inches
		#xposstring = "%10.3f in" % (xval * (1/20))
		#yposstring = "%10.3f in" % (yval * (1/20))
		#zposstring = "%10.3f in" % (zval * (1/20))
		
		xval = -xval
		
		if self.dataBack.unitsScale == 1: #In rotations (no longer used)
			xposstring = "X:%10.1f R" % xval
			yposstring = "Y:%10.1f R" % yval
			zposstring = "Z:%10.1f R" % zval
		
		if self.dataBack.unitsScale == 20: #In inches
			xposstring = "X:%10.1f IN" % (xval * (1/20))
			yposstring = "Y:%10.1f IN" % (yval * (1/20))
			zposstring = "Z:%10.1f IN" % (zval * (1/20))
		
		if self.dataBack.unitsScale <1: #In mm
			if abs(xval) < .1:
				xval = 0.00
			if abs(yval) < .1:
				yval = 0.00
			if abs(zval) < .1:
				zval = 0.00
			xposstring = "X:%10.1f mm" % (xval * (1.27))
			yposstring = "Y:%10.1f mm" % (yval * (1.27))
			zposstring = "Z:%10.1f mm" % (zval * (1.27))
		
		self.xposdispvalin.set(xposstring)
		self.yposdispvalin.set(yposstring)
		self.zposdispvalin.set(zposstring)	
	
	#grab records the point at which you click the left mouse button, used for scrolling.
	def grab(self,event):
		
		self.canv.scan_mark(event.x, event.y)
		self.dataBack.saveFlag = 1
	
	#drag records the point at which you let go of the left mouse button, used for scrolling.
	def drag(self,event):
		
		self.canv.scan_dragto(event.x, event.y, gain=1)
		self.dataBack.xDrag = int(self.canv.canvasx(0))
		self.dataBack.yDrag = int(self.canv.canvasy(0))
		
	#mouse_wheel zooms the canvas when you scroll the mouse wheel.
	def mouse_wheel(self, event):
		# respond to Linux or Windows wheel event
		if event.num == 5 or event.delta == -120:
			self.dataBack.zoomLevel -= 2
			#self.canv.xview_scroll(-110, UNITS) 
			#print(self.canv.winfo_width())
		if event.num == 4 or event.delta == 120:
			self.dataBack.zoomLevel += 2
			#self.canv.xview_scroll(110, UNITS) 
		if self.dataBack.zoomLevel < .1:
			self.dataBack.zoomLevel = .1
		self.refreshGcode()
		self.dataBack.saveFlag = 1
		
		'''xInit = int(self.dataBack.xDrag/conversionFactor)
		yInit = int(self.dataBack.yDrag/conversionFactor)
		self.canv.xview_scroll(-xInit, UNITS) 
		self.canv.yview_scroll(-yInit, UNITS) '''
	
	#This draws the gcode on the canvas.
	def drawgcode(self):
		#one roation is 4 pixels
		xnow = 800.0
		ynow = 800.0
		znow = 0
		cutdi = 1
		fillcolor = "green"
		prependString = "G00 "
		
		
		i = 0
		opstring = ""
		try:
		
			while i < len(self.dataBack.gcode):
				opstring = self.dataBack.gcode[i]
				opstring = opstring + " " #ensures that the is a space at the end of the line
				
				if self.dataBack.toolWidthFlag == 0:
					cutdi = 1
				
				if opstring[0] == 'X' or opstring[0] == 'Y' or opstring[0] == 'Z': #this adds the gcode operator if it is omited by the program
					opstring = prependString + opstring
					#print("prepended: ")
					#print(prependString)
				
				if opstring[0:3] == 'G00' or opstring[0:3] == 'G01' or opstring[0:3] == 'G02' or opstring[0:3] == 'G03':
					prependString = opstring[0:3] + " "
				
				if opstring[0:3] == 'G01' or opstring[0:3] == 'G00' or opstring[0:3] == 'G1 ' or opstring[0:3] == 'G0 ':
					#print("g1 recognized")
					scalor = self.dataBack.zoomLevel * self.dataBack.unitsScale
					startpt = opstring.find('X')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					xdist = 0
					if self.dataBack.absoluteFlag == 1:
						xdist = (800 - xnow)/scalor
					if endpt >= 4:
						xdist = float(opstring[startpt : endpt])
						xdist = -xdist
					#----------------------------------------------------
					startpt = opstring.find('Y')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					ydist = 0
					if self.dataBack.absoluteFlag == 1:
						ydist = (800 - ynow)/scalor
					if endpt >= 4:
						ydist = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('Z')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					zdist = 0
					if self.dataBack.absoluteFlag == 1:
						zdist = znow
					if endpt >= 4:
						zdist = float(opstring[startpt : endpt])
						#self.canv.create_text(self.dataBack.offsetX + xnow + 10,self.dataBack.offsetY + ynow + 10, text = str(zdist) )
					
					xdist = xdist * scalor #this is the scale factor for the canvas
					ydist = ydist * scalor
					'''znow = znow + zdist
					fillNum = int(.05*znow)
					fillcolor =  "#" + str(fillNum)'''
					if self.dataBack.colorFlag == 0:
						fillcolor = "black"
					
					if self.dataBack.absoluteFlag == 0:
						self.canv.create_line(self.dataBack.offsetX + xnow, self.dataBack.offsetY + ynow, self.dataBack.offsetX + xnow - xdist, self.dataBack.offsetY + ynow - ydist, width = cutdi, fill = fillcolor, arrow = LAST, capstyle = "round")
						xnow = xnow - xdist
						ynow = ynow - ydist
						
					if self.dataBack.absoluteFlag == 1:
						#print("poop:")
						#print(xnow)
						#print(ynow)
						#print(xdist)
						#print(ydist)
						linestyle = ()
						if opstring[0:3] == 'G00':
							linestyle = (2,2)
						
						self.canv.create_line(self.dataBack.offsetX + xnow, self.dataBack.offsetY + ynow, self.dataBack.offsetX + 800 - xdist, self.dataBack.offsetY + 800 - ydist, width = cutdi, fill = fillcolor, capstyle = "round", dash = linestyle)
						xnow = 800 - xdist
						ynow = 800 - ydist
				
				
				if opstring[0:3] == 'G02' or opstring[0:3] == 'G2 ':
					scalor = self.dataBack.zoomLevel * self.dataBack.unitsScale
					Xval = 0
					Yval = 0
					Ival = 0
					Jval = 0
					#print("g2 recognized")
					startpt = opstring.find('R')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						radius = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('M')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						cirbgn = float(opstring[startpt : endpt])
						cirbgn = - cirbgn
					#----------------------------------------------------
					startpt = opstring.find('N')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						cirend = float(opstring[startpt : endpt])
						cirend = - cirend
					#----------------------------------------------------
					startpt = opstring.find('X')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Xval = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('Y')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Yval = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('I')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Ival = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('J')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Jval = float(opstring[startpt : endpt])
					
					
					if Xval != 0 or Yval != 0 or Ival != 0 or Jval != 0:
						#print("this ran")
						xposnow = (xnow - 800)#this is the position with 800 stripped off
						yposnow = (ynow - 800)
						
						drawFlag = 1
						if abs(scalor*(Xval - xposnow/scalor)) < 1:
							drawFlag = 0
							#print(abs(scalor*(Xval - xposnow/scalor)))
							#print("tata")
						
						if self.dataBack.absoluteFlag == 1:
							#print("absolute circle")
							Xval = Xval - xposnow/scalor
							Yval = Yval + yposnow/scalor
						
						radius = math.sqrt((Ival)**2 + (Jval)**2) #** is the same as ^ (exponent)
						#print(radius)
						cirbgn = self.angleGet((xnow - 800), (ynow - 800), (xnow - 800) + Ival, (ynow - 800) + Jval)
						cirend = self.angleGet(Xval, Yval, Ival, Jval)
						cirbgn = - cirbgn
						cirend = - cirend
						cirend = 2 - cirend
					
					radius = radius * scalor
					
					#this converts from radians to degrees
					cirbgn = (cirbgn * 360) / 2
					cirend = (cirend * 360) / 2
					
					
					#print(topLeftx),
					#print(topLefty), 
					#print(bottomRightx),
					#print(bottomRighty),
					
					#print(cirend)
					if cirbgn < 0:
						cirbgn = 360 + cirbgn
					if cirend < 0:
						cirend = 360 + cirend
					if cirend > cirbgn:
						cirend = 360 - cirend
					if cirbgn < 0:
						cirbgn = 360 + cirbgn
					#if cirend < 0:
					#	cirend = 360 + cirend
					if cirend > cirbgn:
						cirend = 360 - cirend
						#print("The ran")
					extend = cirend - cirbgn
					if extend < 0:
						extend = 360 + cirend
					if extend > 360:
						extend = 360 - cirend
					
					
					topLeftx = xnow - radius - radius*math.cos((2*math.pi*cirbgn)/360)
					topLefty = ynow - radius + radius*math.sin((2*math.pi*cirbgn)/360)
					bottomRightx = topLeftx + 2*radius
					bottomRighty = topLefty + 2*radius
					pos = topLeftx, topLefty, bottomRightx, bottomRighty
						
					if self.dataBack.colorFlag == 0:
						fillcolor = "black"
					
					if drawFlag == 1:
						self.canv.create_arc(pos, style=ARC, start = cirbgn, extent = (cirend - cirbgn), width = cutdi, outline = fillcolor)
					else:
						self.canv.create_line(xnow, ynow, xnow + Xval*scalor, ynow - Yval*scalor, width = cutdi, fill = fillcolor, capstyle = "round")
					
					#testxnow = xnow - radius*math.cos((2*math.pi*cirbgn)/360) + radius*math.cos((2*math.pi*cirend)/360)
					#testynow = ynow + radius*math.sin((2*math.pi*cirbgn)/360) - radius*math.sin((2*math.pi*cirend)/360)
					
					xnow = xnow + Xval*scalor
					ynow = ynow - Yval*scalor
					
					
				
				if opstring[0:3] == 'G03' or opstring[0:3] == 'G3 ':
					#print("g3 recognized")
					Xval = 0
					Yval = 0
					Ival = 0
					Jval = 0
					scalor = self.dataBack.zoomLevel * self.dataBack.unitsScale
					startpt = opstring.find('R')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						radius = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('M')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						cirbgn = float(opstring[startpt : endpt])
						cirbgn = - cirbgn
					#----------------------------------------------------
					startpt = opstring.find('N')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						cirend = float(opstring[startpt : endpt])
						cirend = - cirend
					#----------------------------------------------------
					startpt = opstring.find('X')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Xval = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('Y')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Yval = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('I')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Ival = float(opstring[startpt : endpt])
					#----------------------------------------------------
					startpt = opstring.find('J')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					if endpt >= 4:
						Jval = float(opstring[startpt : endpt])
					
					if Xval != 0 or Yval != 0 or Ival != 0 or Jval != 0:
						#print("this ran")
						xposnow = (xnow - 800)#this is the version with 800 stripped off
						yposnow = (ynow - 800)
						
						drawFlag = 1
						if (abs(scalor*(Xval - xposnow/scalor))) < 1:
							drawFlag = 0
							#print(abs(scalor*(Xval - xposnow/scalor)))
							#print("tata1")
						
						if self.dataBack.absoluteFlag == 1:
							#print("absolute circle")
							Xval = Xval - xposnow/scalor
							Yval = Yval + yposnow/scalor
							#print(Xval)
							#print(Yval)
							
							
						radius = math.sqrt((Ival)**2 + (Jval)**2) #** is the same as ^ (exponent)
						#print(radius)
						cirbgn = self.angleGet(xposnow, yposnow, xposnow + Ival, yposnow + Jval)
						cirend = self.angleGet(Xval, Yval, Ival, Jval)
						cirbgn = - cirbgn
						cirend = - cirend
						#print("Angle arguments")
						#print(opstring)
						#print(Xval)
						#print(Yval)
						#print(Ival)
						#print(Jval)
						#print(cirbgn)
						#print(cirend)
							
					#print(radius)
					#print(cirend)
					#print(cirbgn)
					#the position at any given time is given by 
					radius = radius * scalor
					
					cirbgn = (cirbgn * 359) / 2
					cirend = (cirend * 359) / 2
					#print(cirbgn)
					#print(cirend)
					
					topLeftx = (self.dataBack.offsetX + xnow) - radius - radius*math.cos((2*math.pi*cirbgn)/360)#will involve cos(0.0 - begin)
					topLefty = (self.dataBack.offsetY + ynow) - radius + radius*math.sin((2*math.pi*cirbgn)/360)#will involve sin(0.0 - begin)
					bottomRightx = topLeftx + 2*radius
					bottomRighty = topLefty + 2*radius
					
					#topLeftx = 10
					#topLefty = 10
					#bottomRightx = 240
					#bottomRighty = 240
					
					pos = topLeftx, topLefty, bottomRightx, bottomRighty
					if cirbgn < 0:
						cirbgn = 360 + cirbgn
					if cirend < 0:
						cirend = 360 + cirend
					extend = cirend - cirbgn
					if extend < 0:
						cirend = 360 + cirend
					
					
					
					if self.dataBack.colorFlag == 0:
						fillcolor = "black"
					
					if drawFlag == 1:
						self.canv.create_arc(pos, style=ARC, start=cirbgn, extent = (cirend - cirbgn), width = cutdi, outline = fillcolor)
					else:
						self.canv.create_line(xnow, ynow, xnow + Xval*scalor, ynow - Yval*scalor, width = cutdi, fill = fillcolor, capstyle = "round")
					
					xnow = xnow + Xval*scalor
					ynow = ynow - Yval*scalor
				
				if opstring[0:3] == 'G20':
					self.switchinches()
					
				if opstring[0:3] == 'G21':
					self.switchmm()
					
				if opstring[0:3] == 'G90':
					self.dataBack.absoluteFlag = 1
					
				if opstring[0:3] == 'G91':
					self.dataBack.absoluteFlag = 0
				
				if opstring[0] == 'D':
					#print("diameter change recognized")
					startpt = opstring.find('D')
					startpt = startpt + 1
					endpt = 0
					j = startpt
					while opstring[j] != ' ':
						j = j + 1
					endpt = j
					tooldi = float(opstring[startpt : endpt])
					cutdi = scalor*20*tooldi
					#print(tooldi)
				
				i = i + 1
		except:
			print("bad gcode")
		
	#This reloads the gcode from the hard drive in case it has been updated.
	def reloadGcode(self):
		try:
			filename = self.dataBack.gcodeFile
			filterfile = open(filename, 'r')
			rawfilters = filterfile.read()
			filtersparsed = re.split(r'\s(?=G)|\n|\s(?=g)|\s(?=M)', rawfilters) #splits the gcode into elements to be added to the list
			filtersparsed = [x + ' ' for x in filtersparsed] #adds a space to the end of each line
			self.dataBack.gcode = filtersparsed
			filterfile.close() #closes the filter save file
		except:
			if filename is not "":
				messagebox.showwarning("Shucks", "Cannot reopen \n %s \n\n It may have been moved or deleted. To locate it or open a different file use File > Open G-code" % filename)
			self.dataBack.gcodeFile = ""
		self.refreshGcode()
		
	#Runs frequently to update the GUI
	def refreshout (self):
		#print("refreshout")
		#print(self.dataBack.readyFlag)
		#print(self.dataBack.uploadFlag)
		root.after(250,self.refreshout)  # reschedule event
		
		if self.dataBack.uploadFlag == 1:
			self.dataBack.endTime = time()
			self.dataBack.target[0] = self.dataBack.currentpos[0]/self.dataBack.unitsScale
			self.dataBack.target[1] = self.dataBack.currentpos[1]/self.dataBack.unitsScale
			self.dataBack.target[2] = self.dataBack.currentpos[2]/self.dataBack.unitsScale
		
		self.timedisp.set(("%.2f" % ((self.dataBack.endTime - self.dataBack.startTime)/60)))
		
			
		if time() - self.dataBack.heartBeat > 1:
			self.terminal.configure(bg = "red")
			self.terminaltext.set("Connection Lost...Reconnect in " + str(6 - int(time() - self.dataBack.heartBeat)))
			if 5 - int(time() - self.dataBack.heartBeat) < 0:
				if self.th.is_alive() : #if the serial thread is open, ask it to close an reopen the serial connection
					self.quick_queue.put("Reconnect")
				else: #if the serial thread is not open, open it
					self.recievemessage()
				self.dataBack.heartBeat = time()
		
		#This pulls the unparsed message and writes it to the output field of the GUI
		while self.message_queue.empty() == False :
			#print(self.message_queue.qsize())
			try:
				messageparsed = self.message_queue.get_nowait()
			except:
				print("message parse issue")

			try:
				if messageparsed == "gready\r\n":
					self.dataBack.readyFlag = 1
					#print("ready flag set")
				elif messageparsed == "ESTOP\r\n":
					self.dataBack.readyFlag = 0
					self.output.insert(END,"ESTOP triggered\r\n")
				elif messageparsed == "ESTOP cleared\r\n":
					self.output.insert(END,"ESTOP cleared\r\n")
					self.dataBack.readyFlag = 1
				elif messageparsed[0] == 'p' and messageparsed[1] == 'z':
					self.updatePosView(messageparsed)
					self.dataBack.heartBeat = time()
					self.terminal.configure(bg = "green")
					self.terminaltext.set("Connected on " + self.dataBack.comport + "    ")
					#print(time())
					#print(("%.2f" % ((time() - self.dataBack.startTime)/60)))
				elif messageparsed == "really stuck\r\n":
					from tkinter import messagebox
					self.dataBack.uploadFlag = 0
					messagebox.showwarning("Shucks", "The machine has become stuck and was unable to free itself.\r\n\r\nThe motors have been turned off to protect them.\r\nPlease verify that the machine is free to move and are properly lubricated, then press OK to continue operation.\r\n\r\nYour machine will not loose its place if you manually rotate the motors")
					self.quick_queue.put("unstuck")
					self.dataBack.uploadFlag = 1
				elif messageparsed[0:18] == "Please insert tool":
					if time() - self.dataBack.startTime > 2:
						print("Insert tool.")
						self.dataBack.uploadFlag = 0
						self.dataBack.readyFlag = 0
						print(self.gcode_queue.qsize())
						from tkinter import messagebox
						messageString = "Please insert tool " + messageparsed[19:] + "Once the tool is in place please select Run >> Resume to resume operation."
						messagebox.showinfo("Tool Change", messageString)
				else:
					try:
						self.output.insert(END, messageparsed)
					except:
						print("jump to end issue")
					
					if(self.dataBack.logflag == 1):
						self.dataBack.logfile.write(messageparsed)
						
				
				if self.dataBack.readyFlag == 1 and self.dataBack.uploadFlag == 1:
					#print("Sending function called")
					self.sendandinc()
					
					self.dataBack.readyFlag = 0
					#print("here: ")
					#print(messageparsed)
					messageparsed = ""
			except:
				print("serial data byte shift")
			
		if self.dataBack.scrollFlag == 1:
			self.output.see(END)
		
		self.jmpsize()
		
		if float(self.output.index(END)) > 600: #checks to see if there are over 600 lines of data being displayed, float() handles the decimal point
			self.output.delete(1.0,300.0) #if there are the oldest 300 are deleted
		
	#Runs frequently to update the cross hairs on the GUI
	def refreshCross(self):
		#indicator for location 
		#(0, 0) is (800, 800)
		
		try:
			self.canv.delete(self.cross1)
			self.canv.delete(self.cross2)
			self.canv.delete(self.posOval)
		except:
			#print("canv delete issue")
			pass;
		
		scalor2 = self.dataBack.zoomLevel
		offsetX =  self.dataBack.offsetX
		offsetY =  self.dataBack.offsetY
		
		
		self.cross1 = self.canv.create_line(offsetX + 790 - self.dataBack.currentpos[0]*scalor2, offsetY + 790 - self.dataBack.currentpos[1]*scalor2, offsetX + 810 - self.dataBack.currentpos[0]*scalor2, offsetY + 810 - self.dataBack.currentpos[1]*scalor2)
		self.cross2 = self.canv.create_line(offsetX + 790 - self.dataBack.currentpos[0]*scalor2, offsetY + 810 - self.dataBack.currentpos[1]*scalor2, offsetX + 810 - self.dataBack.currentpos[0]*scalor2, offsetY + 790 - self.dataBack.currentpos[1]*scalor2)
		self.posOval = self.canv.create_oval(offsetX + 790 - self.dataBack.currentpos[0]*scalor2, offsetY + 790 - self.dataBack.currentpos[1]*scalor2, offsetX + 810 - self.dataBack.currentpos[0]*scalor2, offsetY + 810 - self.dataBack.currentpos[1]*scalor2)
	
	'''--------------------------------------------------------------------------------------
	 These are the front-end functions which the user can activate using the GUI
	 ----------------------------------------------------------------------------------------'''	
	#ForceCOMconnect forces the program to try to connect to a COM port which is not detected
	def forceCOMconnect(self):
		
		self.top = Toplevel()
		self.top.title("Specify Port")

		self.msg = Message(self.top, text="Please Enter Desired Port. This value can be found in Device Manager. An example of a valid choice would be COM9", width = 400)
		self.msg.pack()
		
		self.myEntryBox = Entry(self.top, text = "COM9")
		self.myEntryBox.pack()
		
		self.button = Button(self.top, text="Submit", command=self.submit)
		self.button.pack()
	
	#This is the button on the forceCOMConnect window which updates the COM value
	def submit(self):
		self.comset(self.myEntryBox.get()) 
		self.top.destroy()
	
	#This displays the software version number and requests that the machine print it's firmware version number.
	def versionNumber(self):
		self.gcode_queue.put("B05 ")
		self.gcode_queue.put("Software Version: " + self.dataBack.version)
	
	#resetOrigin moves the window back to the center of the screen if it has been moved to far to one side or another.
	def resetOrigin(self):
		conversionFactor = 2
		xInit = int(self.dataBack.xDrag/conversionFactor)
		yInit = int(self.dataBack.yDrag/conversionFactor)
		self.canv.xview_scroll(-xInit, UNITS) 
		self.canv.yview_scroll(-yInit, UNITS) 
		self.dataBack.xDrag = 0
		self.dataBack.yDrag = 0
		self.dataBack.saveFlag = 1
		if xInit is not 0 or yInit is not 0: #this puts it in a better spot for small screens
			self.canv.xview_scroll(180, UNITS) 
			self.canv.yview_scroll(180, UNITS) 
		
	#moveToStart moves the canvas to a better starting position
	def moveToStart(self):
		conversionFactor = 2
		xInit = int(self.dataBack.xDrag/conversionFactor)
		yInit = int(self.dataBack.yDrag/conversionFactor)
		self.canv.xview_scroll(xInit, UNITS) 
		self.canv.yview_scroll(yInit, UNITS) 
	
	#stoprun stops the machine's movement imediatly when it is moving.
	def stoprun(self):
		stopflag = 0
		if self.dataBack.uploadFlag == 1: 
			stopflag = 1
		self.dataBack.uploadFlag = 0
		self.dataBack.gcodeIndex = 0
		self.quick_queue.put("STOP") 
		with self.gcode_queue.mutex:
			self.gcode_queue.queue.clear()
		print("Gode Stopped")
		
		self.dataBack.target[0] = self.dataBack.currentpos[0]/self.dataBack.unitsScale
		self.dataBack.target[1] = self.dataBack.currentpos[1]/self.dataBack.unitsScale
		self.dataBack.target[2] = self.dataBack.currentpos[2]/self.dataBack.unitsScale
		
		'''if stopflag == 1:
			answer = messagebox.askyesno("Save?", "Would you like to save your place in the current program?")
			if answer is True: pass
			else: self.dataBack.gcodeIndex = 0'''
		
	#pause makes shuts down the machine after it finishes processing the current line of gcode
	def pause(self):
		self.dataBack.uploadFlag = 0
		print("paused")
	
	#unpause causes the machine to begin moving again after being paused.
	def unpause(self):
		self.dataBack.uploadFlag = 1
		print("unpaused")
	
	#This toggles if the lines in the gui are drawn with width. The width is set by the tool diameter.
	def tool_width_toggle(self):
		if self.dataBack.toolWidthFlag == 1:
			self.dataBack.toolWidthFlag = 0
		else:
			self.dataBack.toolWidthFlag = 1
		self.refreshGcode()
		
	#zoomset zooms the canvas.
	def zoomset(self, zoomFract):
		self.dataBack.zoomLevel = 4.9*zoomFract
		self.refreshGcode()
		self.dataBack.saveFlag = 1
	
	#updateSettings lets you change the contrast and brightness on the LCD display
	def updateSettings(self):
		self.settingsView = Toplevel()
		self.settingsView.title("LCD Display Settings")
		
		msg = Message(self.settingsView, text="These settings apply to the optional on machine LCD display\n", width = 400)
		msg.pack()
		
		msg = Message(self.settingsView, text="Contrast", width = 400)
		msg.pack()
		
		self.contrastValue = Scale(self.settingsView, from_=0, to=100, orient=HORIZONTAL, length = 400)
		self.contrastValue.pack()
		self.contrastValue.set(self.dataBack.contrast)
		
		msg2 = Message(self.settingsView, text="Backlight", width = 400)
		msg2.pack()
		
		self.backlightValue = Scale(self.settingsView, from_=0, to=100, orient=HORIZONTAL, length = 400)
		self.backlightValue.pack()
		self.backlightValue.set(self.dataBack.backlight)
		
		msg3 = Message(self.settingsView, text=" ", width = 400)
		msg3.pack()
		
		settingsButton = Button(self.settingsView, text="Update", command=self.pushSettingsToMachine)
		settingsButton.pack()
		self.dataBack.saveFlag = 1
	
	#color_toggle causes the color of the lines on the canvas to be black or color. Currently not working well.
	def color_toggle(self):
		if self.dataBack.colorFlag == 1:
			self.dataBack.colorFlag = 0
		else:
			self.dataBack.colorFlag = 1
		self.refreshGcode()
		self.dataBack.saveFlag = 1
		
	#beginGcodeRun begins exicuting the currently opened gcode file
	def beginGcodeRun(self):
		if self.dataBack.uploadFlag == 0 and self.dataBack.gcodeIndex < 2: #there is not a program being exicuted 
			self.reZero()
			self.dataBack.uploadFlag = 1
			self.dataBack.readyFlag = 1
			self.dataBack.startTime = time()
			self.sendandinc()
		elif self.dataBack.uploadFlag == 0 and self.dataBack.gcodeIndex > 2:
			self.unpause()
		else:
			self.output.insert(END,"A program is already running, press stop to end it")
		
	#scrollactive toggles if the output text can be scrolled or is static
	def scrollactive(self):
		if self.dataBack.scrollFlag == 0:
			self.dataBack.scrollFlag = 1
			return 
		
		if self.dataBack.scrollFlag == 1:
			self.dataBack.scrollFlag = 0
			return
		
	#toggleSpindle turns on and off the dremel if a relay is attached
	def toggleSpindle(self):
		if(self.dataBack.spindleFlag == 1):
			self.gcode_queue.put("S5000 ")
			self.dataBack.spindleFlag = 0
		elif(self.dataBack.spindleFlag == 0):
			self.gcode_queue.put("S0 ")
			self.dataBack.spindleFlag = 1
		
	#reZero defines a new home position for the machine.
	def reZero(self): 
		self.dataBack.currentpos[0] = 0.0
		self.dataBack.currentpos[1] = 0.0
		self.dataBack.currentpos[2] = 0.0
		
		self.dataBack.target[0] = 0.0
		self.dataBack.target[1] = 0.0
		self.dataBack.target[2] = 0.0
		
		self.xposdispval.set("0.00")
		self.yposdispval.set("0.00")
		self.zposdispval.set("0.00")
		
		self.xposdispvalin.set("0.00")
		self.yposdispvalin.set("0.00")
		self.zposdispvalin.set("0.00")
		
		self.gcode_queue.put("G10 X0 Y0 Z0 ")
		
		self.refreshGcode()
	
	#reZeroZ sets a new home position for just the z axis. This is useful for tool changes.
	def reZeroZ(self):
		self.dataBack.currentpos[2] = 0.0
		self.dataBack.target[2] = 0.0
		self.zposdispval.set("0.00")
		self.zposdispvalin.set("0.00")
		
		self.gcode_queue.put("G10 Z0 ")
		self.refreshGcode()
		
	#comset sets the COM port to which the machine is attached
	def comset(self, comstring):
		self.dataBack.comport = comstring
		self.recievemessage()
		print(self.dataBack.comport)
		self.dataBack.saveFlag = 1
	
	#rightb moves the machine to the right by the indicated amount at the indicated speed. rightb is called by the right arrow button.
	def rightb(self):
		self.jmpsize()
		target = -1*self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(target) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] - float(self.dataBack.stepsizeval)
			
	def leftb(self):
		self.jmpsize()
		target = -1*self.dataBack.target[0] - float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(target) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		
	def forwardb(self):
		self.jmpsize()
		target = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Y" + str(target) + " ")
		self.dataBack.target[1] = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
		
	def backb(self):
		self.jmpsize()
		target = self.dataBack.target[1] - float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Y" + str(target) + " ")
		self.dataBack.target[1] = self.dataBack.target[1] - float(self.dataBack.stepsizeval)
		
	def upb(self):
		self.jmpsize()
		target = self.dataBack.target[2] + float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Z" + str(target) + " ")
		self.dataBack.target[2] = self.dataBack.target[2] + float(self.dataBack.stepsizeval)
		
	def downb(self):
		self.jmpsize()
		target = self.dataBack.target[2] - float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Z" + str(target) + " ")
		self.dataBack.target[2] = self.dataBack.target[2] - float(self.dataBack.stepsizeval)
		
	def homebtn(self):
		if self.dataBack.target[2] < 0:
			self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Z0 ")
			self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X0 Y0 Z0 ")
		if self.dataBack.target[2] >= 0:
			self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X0 Y0 ")
			self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " Z0 ")
		self.dataBack.target[0] = 0.0
		self.dataBack.target[1] = 0.0
		self.dataBack.target[2] = 0.0
			
	#up and to the right button
	def urb(self):
		self.jmpsize()
		xtarget = -1*self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		ytarget = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(xtarget) + " Y" + str(ytarget) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] - float(self.dataBack.stepsizeval)
		self.dataBack.target[1] = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
	
	def ulb(self):
		self.jmpsize()
		xtarget = -1*self.dataBack.target[0] - float(self.dataBack.stepsizeval)
		ytarget = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(xtarget) + " Y" + str(ytarget) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		self.dataBack.target[1] = self.dataBack.target[1] + float(self.dataBack.stepsizeval)
	
	def drb(self):
		self.jmpsize()
		xtarget = -1*self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		ytarget = self.dataBack.target[1] - float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(xtarget) + " Y" + str(ytarget) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] - float(self.dataBack.stepsizeval)
		self.dataBack.target[1] = self.dataBack.target[1] - float(self.dataBack.stepsizeval)
	
	def dlb(self):
		self.jmpsize()
		xtarget = -1*self.dataBack.target[0] - float(self.dataBack.stepsizeval)
		ytarget = self.dataBack.target[1] - float(self.dataBack.stepsizeval)
		self.gcode_queue.put("G01 F" + str(float(self.dataBack.feedRate)) + " X" + str(xtarget) + " Y" + str(ytarget) + " ")
		self.dataBack.target[0] = self.dataBack.target[0] + float(self.dataBack.stepsizeval)
		self.dataBack.target[1] = self.dataBack.target[1] - float(self.dataBack.stepsizeval)	
		
	#beginLoging pipes the output of text window to a file. This is usefull for debug reasons
	def beginLoging (self):
		filename = "DataLog.txt"
		try:
			logfile = open(filename, 'w') #Opens the provided file name for writing which will replace any existing data
			logfile.write("Software Version: " + self.dataBack.version) #Log GroundControl version
			self.dataBack.logflag = 1
			self.dataBack.logfile = logfile
		except:
			print("open issue")
			
	#end log closes the log file and sets the log flag to be false. If end log is not called the file will not close properly which is an issue.
	def endLog(self):
		if(self.dataBack.logflag == 1):
			self.dataBack.logflag = 0
			self.dataBack.logfile.close()
		
	#autoDebug tests various functions of the machine
	def autoDebug(self): 
		debugWindow = Toplevel()
		debugWindow.title("Diagnostics")
		msgText = "This will try to help you detect and possibly\n   resolve any issues with the machine\n\n     The output of each test will show \n up on in the terminal on the main screen.\n\n"
		msg = Message(debugWindow, text= msgText, width = 400)
		msg.pack()
		
		encodersFrame = Frame(debugWindow)
		encodersFrame.pack()
		
		MotorsFrame = Frame(debugWindow)
		MotorsFrame.pack()
		
		BothFrame = Frame(debugWindow)
		BothFrame.pack()
		
		centerFrame = Frame(debugWindow)
		centerFrame.pack()
		
		constantFrame = Frame(debugWindow)
		constantFrame.pack()
		
		msg2 = Message(encodersFrame, text= "This tests to see that all of the encoders are producing a valid PWM signal. If the encoder happens to be exactly at the zero position it will not pass the test because the encoder is not producing a signal. Pluging the encoder in backwards will not hurt it.", width = 400)
		msg2.pack(side = LEFT)
		
		encodersButton = Button(encodersFrame, text = "Test Encoders", command = lambda: self.gcode_queue.put("Test Encoders"))
		encodersButton.pack(side = LEFT)
		
		msg3 = Message(MotorsFrame, text= "This test moves each motor in turn. If your motors do not move, check that they are plugged in correctly and that the power supply is working.", width = 400)
		msg3.pack(side = LEFT)
		
		motorsButton = Button(MotorsFrame, text = "Test Motors", command = lambda: self.gcode_queue.put("Test Motors"))
		motorsButton.pack(side = LEFT)
		
		msg4 = Message(BothFrame, text = "This test checks that the motors are plugged into the correct axies. It does this by driving one motor and checking to see that the machine moves in the correct direction.", width = 400)
		msg4.pack(side = LEFT)
		
		bothButton = Button(BothFrame, text="Test Both", command = lambda: self.gcode_queue.put("Test Both"))
		bothButton.pack(side = LEFT)
		
		centermsg = Message(centerFrame, text = "This test allows you to define the center position for each servo. On the back of each servo is a small potentiometer which will let you adjust the resting position of the servo. This test will command all of the motors to not rotat for two seconds. If one motor rotates, adjust the potentiometer on the back of the servo until it stops.", width = 400)
		centermsg.pack(side = LEFT)
		
		centerMotors = Button(centerFrame, text="Center Motors", command = lambda: self.gcode_queue.put("Center Motors"))
		centerMotors.pack(side = LEFT)
		
		constantmsg = Message(constantFrame, text = "\nThis test allows you to manually set the speed of all three motors independently for testing purposes. It can cause strange behavior because it manually overrides the regular control system. If you notice that the motors continue to rotate at speed zero, you can adjust them using the potentiometer on the back of the servo.", width = 500)
		constantmsg.pack(side = LEFT)
		
		constantFramex = Frame(debugWindow)
		constantFramex.pack()
		
		xmsg = Message(constantFramex, text = "X: ")
		xmsg.pack(side = LEFT)
		
		constantMotorsxn9 = Button(constantFramex, text="-9", command = lambda: self.gcode_queue.put("B06 X0"))
		constantMotorsxn8 = Button(constantFramex, text="-8", command = lambda: self.gcode_queue.put("B06 X10"))
		constantMotorsxn7 = Button(constantFramex, text="-7", command = lambda: self.gcode_queue.put("B06 X20"))
		constantMotorsxn6 = Button(constantFramex, text="-6", command = lambda: self.gcode_queue.put("B06 X30"))
		constantMotorsxn5 = Button(constantFramex, text="-5", command = lambda: self.gcode_queue.put("B06 X40"))
		constantMotorsxn4 = Button(constantFramex, text="-4", command = lambda: self.gcode_queue.put("B06 X50"))
		constantMotorsxn3 = Button(constantFramex, text="-3", command = lambda: self.gcode_queue.put("B06 X60"))
		constantMotorsxn2 = Button(constantFramex, text="-2", command = lambda: self.gcode_queue.put("B06 X70"))
		constantMotorsxn1 = Button(constantFramex, text="-1", command = lambda: self.gcode_queue.put("B06 X80"))
		constantMotorsx0 = Button(constantFramex, text="0", command = lambda: self.gcode_queue.put("B06 X90"))
		constantMotorsx1 = Button(constantFramex, text="+1", command = lambda: self.gcode_queue.put("B06 X100"))
		constantMotorsx2 = Button(constantFramex, text="+2", command = lambda: self.gcode_queue.put("B06 X110"))
		constantMotorsx3 = Button(constantFramex, text="+3", command = lambda: self.gcode_queue.put("B06 X120"))
		constantMotorsx4 = Button(constantFramex, text="+4", command = lambda: self.gcode_queue.put("B06 X130"))
		constantMotorsx5 = Button(constantFramex, text="+5", command = lambda: self.gcode_queue.put("B06 X140"))
		constantMotorsx6 = Button(constantFramex, text="+6", command = lambda: self.gcode_queue.put("B06 X150"))
		constantMotorsx7 = Button(constantFramex, text="+7", command = lambda: self.gcode_queue.put("B06 X160"))
		constantMotorsx8 = Button(constantFramex, text="+8", command = lambda: self.gcode_queue.put("B06 X170"))
		constantMotorsx9 = Button(constantFramex, text="+9", command = lambda: self.gcode_queue.put("B06 X180"))
		
		constantMotorsxn9.pack(side = LEFT)
		constantMotorsxn8.pack(side = LEFT)
		constantMotorsxn7.pack(side = LEFT)
		constantMotorsxn6.pack(side = LEFT)
		constantMotorsxn5.pack(side = LEFT)
		constantMotorsxn4.pack(side = LEFT)
		constantMotorsxn3.pack(side = LEFT)
		constantMotorsxn2.pack(side = LEFT)
		constantMotorsxn1.pack(side = LEFT)
		constantMotorsx0.pack(side = LEFT)
		constantMotorsx1.pack(side = LEFT)
		constantMotorsx2.pack(side = LEFT)
		constantMotorsx3.pack(side = LEFT)
		constantMotorsx4.pack(side = LEFT)
		constantMotorsx5.pack(side = LEFT)
		constantMotorsx6.pack(side = LEFT)
		constantMotorsx7.pack(side = LEFT)
		constantMotorsx8.pack(side = LEFT)
		constantMotorsx9.pack(side = LEFT)
		
		constantFramey = Frame(debugWindow)
		constantFramey.pack()
		
		ymsg = Message(constantFramey, text = "Y: ")
		ymsg.pack(side = LEFT)
		
		constantMotorsyn9 = Button(constantFramey, text="-9", command = lambda: self.gcode_queue.put("B06 Y0"))
		constantMotorsyn8 = Button(constantFramey, text="-8", command = lambda: self.gcode_queue.put("B06 Y10"))
		constantMotorsyn7 = Button(constantFramey, text="-7", command = lambda: self.gcode_queue.put("B06 Y20"))
		constantMotorsyn6 = Button(constantFramey, text="-6", command = lambda: self.gcode_queue.put("B06 Y30"))
		constantMotorsyn5 = Button(constantFramey, text="-5", command = lambda: self.gcode_queue.put("B06 Y40"))
		constantMotorsyn4 = Button(constantFramey, text="-4", command = lambda: self.gcode_queue.put("B06 Y50"))
		constantMotorsyn3 = Button(constantFramey, text="-3", command = lambda: self.gcode_queue.put("B06 Y60"))
		constantMotorsyn2 = Button(constantFramey, text="-2", command = lambda: self.gcode_queue.put("B06 Y70"))
		constantMotorsyn1 = Button(constantFramey, text="-1", command = lambda: self.gcode_queue.put("B06 Y80"))
		constantMotorsy0 = Button(constantFramey, text="0", command = lambda: self.gcode_queue.put("B06 Y90"))
		constantMotorsy1 = Button(constantFramey, text="+1", command = lambda: self.gcode_queue.put("B06 Y100"))
		constantMotorsy2 = Button(constantFramey, text="+2", command = lambda: self.gcode_queue.put("B06 Y110"))
		constantMotorsy3 = Button(constantFramey, text="+3", command = lambda: self.gcode_queue.put("B06 Y120"))
		constantMotorsy4 = Button(constantFramey, text="+4", command = lambda: self.gcode_queue.put("B06 Y130"))
		constantMotorsy5 = Button(constantFramey, text="+5", command = lambda: self.gcode_queue.put("B06 Y140"))
		constantMotorsy6 = Button(constantFramey, text="+6", command = lambda: self.gcode_queue.put("B06 Y150"))
		constantMotorsy7 = Button(constantFramey, text="+7", command = lambda: self.gcode_queue.put("B06 Y160"))
		constantMotorsy8 = Button(constantFramey, text="+8", command = lambda: self.gcode_queue.put("B06 Y170"))
		constantMotorsy9 = Button(constantFramey, text="+9", command = lambda: self.gcode_queue.put("B06 Y180"))
		
		constantMotorsyn9.pack(side = LEFT)
		constantMotorsyn8.pack(side = LEFT)
		constantMotorsyn7.pack(side = LEFT)
		constantMotorsyn6.pack(side = LEFT)
		constantMotorsyn5.pack(side = LEFT)
		constantMotorsyn4.pack(side = LEFT)
		constantMotorsyn3.pack(side = LEFT)
		constantMotorsyn2.pack(side = LEFT)
		constantMotorsyn1.pack(side = LEFT)
		constantMotorsy0.pack(side = LEFT)
		constantMotorsy1.pack(side = LEFT)
		constantMotorsy2.pack(side = LEFT)
		constantMotorsy3.pack(side = LEFT)
		constantMotorsy4.pack(side = LEFT)
		constantMotorsy5.pack(side = LEFT)
		constantMotorsy6.pack(side = LEFT)
		constantMotorsy7.pack(side = LEFT)
		constantMotorsy8.pack(side = LEFT)
		constantMotorsy9.pack(side = LEFT)
		
		constantFramez = Frame(debugWindow)
		constantFramez.pack()
		
		zmsg = Message(constantFramez, text = "Z: ")
		zmsg.pack(side = LEFT)
		
		constantMotorszn9 = Button(constantFramez, text="-9", command = lambda: self.gcode_queue.put("B06 Z0"))
		constantMotorszn8 = Button(constantFramez, text="-8", command = lambda: self.gcode_queue.put("B06 Z10"))
		constantMotorszn7 = Button(constantFramez, text="-7", command = lambda: self.gcode_queue.put("B06 Z20"))
		constantMotorszn6 = Button(constantFramez, text="-6", command = lambda: self.gcode_queue.put("B06 Z30"))
		constantMotorszn5 = Button(constantFramez, text="-5", command = lambda: self.gcode_queue.put("B06 Z40"))
		constantMotorszn4 = Button(constantFramez, text="-4", command = lambda: self.gcode_queue.put("B06 Z50"))
		constantMotorszn3 = Button(constantFramez, text="-3", command = lambda: self.gcode_queue.put("B06 Z60"))
		constantMotorszn2 = Button(constantFramez, text="-2", command = lambda: self.gcode_queue.put("B06 Z70"))
		constantMotorszn1 = Button(constantFramez, text="-1", command = lambda: self.gcode_queue.put("B06 Z80"))
		constantMotorsz0 = Button(constantFramez, text="0", command = lambda: self.gcode_queue.put("B06 Z90"))
		constantMotorsz1 = Button(constantFramez, text="+1", command = lambda: self.gcode_queue.put("B06 Z100"))
		constantMotorsz2 = Button(constantFramez, text="+2", command = lambda: self.gcode_queue.put("B06 Z110"))
		constantMotorsz3 = Button(constantFramez, text="+3", command = lambda: self.gcode_queue.put("B06 Z120"))
		constantMotorsz4 = Button(constantFramez, text="+4", command = lambda: self.gcode_queue.put("B06 Z130"))
		constantMotorsz5 = Button(constantFramez, text="+5", command = lambda: self.gcode_queue.put("B06 Z140"))
		constantMotorsz6 = Button(constantFramez, text="+6", command = lambda: self.gcode_queue.put("B06 Z150"))
		constantMotorsz7 = Button(constantFramez, text="+7", command = lambda: self.gcode_queue.put("B06 Z160"))
		constantMotorsz8 = Button(constantFramez, text="+8", command = lambda: self.gcode_queue.put("B06 Z170"))
		constantMotorsz9 = Button(constantFramez, text="+9", command = lambda: self.gcode_queue.put("B06 Z180"))
		
		constantMotorszn9.pack(side = LEFT)
		constantMotorszn8.pack(side = LEFT)
		constantMotorszn7.pack(side = LEFT)
		constantMotorszn6.pack(side = LEFT)
		constantMotorszn5.pack(side = LEFT)
		constantMotorszn4.pack(side = LEFT)
		constantMotorszn3.pack(side = LEFT)
		constantMotorszn2.pack(side = LEFT)
		constantMotorszn1.pack(side = LEFT)
		constantMotorsz0.pack(side = LEFT)
		constantMotorsz1.pack(side = LEFT)
		constantMotorsz2.pack(side = LEFT)
		constantMotorsz3.pack(side = LEFT)
		constantMotorsz4.pack(side = LEFT)
		constantMotorsz5.pack(side = LEFT)
		constantMotorsz6.pack(side = LEFT)
		constantMotorsz7.pack(side = LEFT)
		constantMotorsz8.pack(side = LEFT)
		constantMotorsz9.pack(side = LEFT)
		
		constantFrameExit = Frame(debugWindow)
		constantFrameExit.pack()
		
		constantMotorsExit = Button(constantFrameExit, text="Exit Manual Control", command = lambda: self.gcode_queue.put("Exit Manual Control"))
		constantMotorsExit.pack(side = LEFT)
	
	#loadGcode opens a new gcode file 
	def loadGcode(self):
		filename = filedialog.askopenfilename(initialdir = self.dataBack.gcodeFile)  #This opens the built in TK dialog box to open a file
		if filename is not "":
			self.dataBack.gcodeFile = filename
		self.reloadGcode()
		self.dataBack.saveFlag = 1
		self.refreshGcode()
	
	#viewGcode opens a new window to look at the gcode which is opened
	def viewGcode(self):
		gcodewindow = Toplevel()
		message = "This is the child window"
		gCodeText = Text( gcodewindow, width = 37, height = 14, background = "grey95", relief = FLAT)
		gCodeText.pack(fill = BOTH, expand = YES)
		for x in self.dataBack.gcode:
			gCodeText.insert(END, x + "\r\n")
	
	'''-------------------------------------------------------------------------------------------------------------
	These functions likely do not ever run and can be deleted.
	'''
	#This is called several times, is it useful?
	def refreshGcode(self):
		#print("updated canvas")
		self.canv.delete("all") #clear the canvas
		self.refreshCross()
		
		scalor2 = self.dataBack.zoomLevel
		
		
		#redraw frame shit
		self.canv.create_line( 800, -4000, 800,  4800, dash=(6, 6), fill = 'grey')#the hash lines
		self.canv.create_line( -4000,  800,  4800,  800, dash=(6, 6), fill = 'grey')
		
		#Draw inch marker
		if self.dataBack.unitsScale == 20:
			self.canv.create_line( 900,  850,  900 + 20*scalor2,  850)
			self.canv.create_line( 900,  840,  900,  860)
			self.canv.create_line( 900 + 20*scalor2,  840,  900 + 20*scalor2,  860)
			
			self.canv.create_text( 870, 850, text = "One Inch" )
		else:
			self.canv.create_line( 900,  850,  900 + 8*scalor2,  850)
			self.canv.create_line( 900,  840,  900,  860)
			self.canv.create_line( 900 + 8*scalor2,  840,  900 + 8*scalor2,  860)
			
			self.canv.create_text( 870, 850, text = "10 mm" )
		
		self.drawgcode()
			
	#This is now the way to view the G-code
	#called once during setup
	def showCanvas(self):

		scalor3 = self.dataBack.zoomLevel
		
		
		#canv.create_line(0, 0, 4, 4)
		self.canv.create_line(800, 0, 800, 900, dash=(6, 6), fill = 'grey')#the hash lines
		self.canv.create_line(0, 800, 900, 800, dash=(6, 6), fill = 'grey')
		
		self.canv.create_line(500, 850, 500 + 20*scalor3, 850)
		self.canv.create_line(500, 840, 500, 860)
		self.canv.create_line(500 + 20*scalor3, 840, 500 + 20*scalor3, 860)
		
		self.canv.create_text( 556, 860, text = "One Inch" )
		
		self.drawgcode()
		
		#indicator for location 
		#(0, 0) is (800, 800)
		offsetX =  self.dataBack.offsetX
		offsetY =  self.dataBack.offsetY
		
		self.canv.create_line(offsetX + 790 - self.dataBack.currentpos[0]*scalor3, offsetY + 790 - self.dataBack.currentpos[1]*scalor3, offsetX + 810 - self.dataBack.currentpos[0]*scalor3, offsetY + 810 - self.dataBack.currentpos[1]*scalor3)
		self.canv.create_line(offsetX + 790 - self.dataBack.currentpos[0]*scalor3, offsetY + 810 - self.dataBack.currentpos[1]*scalor3, offsetX + 810 - self.dataBack.currentpos[0]*scalor3, offsetY + 790 - self.dataBack.currentpos[1]*scalor3)
		self.canv.create_oval(offsetX + 790 - self.dataBack.currentpos[0]*scalor3, offsetY + 790 - self.dataBack.currentpos[1]*scalor3, offsetX + 810 - self.dataBack.currentpos[0]*scalor3, offsetY + 810 - self.dataBack.currentpos[1]*scalor3)
		
		#Z axis indicator
		self.canv.create_line(850, 550, 850, 150)
		self.canv.create_line(845, 550, 855, 550)
		self.canv.create_line(845, 150, 855, 150)
		self.canv.create_line(837, 350 - self.dataBack.currentpos[2]*scalor3, 863, 350 - self.dataBack.currentpos[2]*scalor3)
		#tick marks
		self.canv.create_line(850, 350 + 20*scalor3 , 857, 350 + 20*scalor3 )
		self.canv.create_line(850, 350 - 20*scalor3 , 857, 350 - 20*scalor3 )
		
		m = 1
		while(m <= 50):
			self.canv.create_line(846, 350 + m*.03937*20*scalor3 , 850, 350 + m*.03937*20*scalor3 )
			self.canv.create_line(846, 350 - m*.03937*20*scalor3 , 850, 350 - m*.03937*20*scalor3 )
			m = m +1
		
		m = 1
		while(m <= 5):
			self.canv.create_line(842, 350 + m*.3937*20*scalor3 , 850, 350 + m*.3937*20*scalor3 )
			self.canv.create_line(842, 350 - m*.3937*20*scalor3 , 850, 350 - m*.3937*20*scalor3 )
			m = m +1
			
		self.refreshGcode()
	
	#depreciated
	def forceResume(self):
		self.dataBack.uploadFlag = 1
		self.dataBack.readyFlag = 1
		#self.sendandinc()
		print("forced resume")
		print("uploadFlag: ")
		print(self.dataBack.uploadFlag)
		print("gcodeIndex")
		print(self.dataBack.gcodeIndex)
		print("readyFlag")
		print(self.dataBack.readyFlag)
	
	#not called?
	def sendonegcode(self):
		#print("start")
		#print(self.dataBack.gcodeIndex)
		try:
			self.gcode_queue.put(self.dataBack.gcode[self.dataBack.gcodeIndex])
			#print(self.dataBack.gcode[self.dataBack.gcodeIndex])
			self.dataBack.gcodeIndex = self.dataBack.gcodeIndex + 1
		except:
			self.dataBack.uploadFlag = 0
			#self.dataBack.readyFlag = 0
			self.dataBack.gcodeIndex = 0
			print("Gcode run complete")

	'''def incmt(self):
		#self.dataBack.gcodeIndex = self.dataBack.gcodeIndex + 1
		print("incmt ran")'''
	
	'''def resetcount(self):
		self.dataBack.gcodeIndex = 0'''
	
#SerialPort is the thread which handles direct communication with the CAN device. CanPort initializes the connection and then receives
#and parses standard CAN messages. These messages are then passed to the Grid thread via the message_queue queue where they are
#added to the GUI
class SerialPort():
	def __init__( self, message_queue, gcode_queue, mainwindow, comport, quick_queue):
		self.message_queue = message_queue
		self.gcode_queue = gcode_queue
		self.quick_queue = quick_queue
		self.mainwindow = mainwindow
		self.comport = comport
		
	def getmessage (self):
		#print("Waiting for new message")
		#print(self.comport)
		#opens a serial connection called serialCAN
		from time import sleep
		
		'''ser = serial.Serial('/dev/ttyUSB0', 19200, timeout = .25)
		while True:
			# To simulate asynchronous I/O, we create a random number at
			# random intervals. Replace the following 2 lines with the real
			# thing.
			#time.sleep(rand.random() * 0.3)
			msg = ser.readline() #rand.random()
			#self.queue.put(msg)
			print(msg)'''
		
		try:
			print("connecting")
			serialCAN = serial.Serial(self.comport, 19200, timeout = .25) #self.comport is the com port which is opened
		except:
			#print(self.comport + "is unavailable or in use")
			self.message_queue.put("\n" + self.comport + " is unavailable or in use")
		else:
			self.message_queue.put("\r\nConnected on port " + self.comport + "\r\n")
			gcode = ""
			msg = ""
			subReadyFlag = True
			
			serialCAN.parity = serial.PARITY_ODD #This is something you have to do to get the connection to open properly. I have no idea why.
			serialCAN.close()
			serialCAN.open()
			serialCAN.close()
			serialCAN.parity = serial.PARITY_NONE
			serialCAN.open()
			
			while True:
				# To simulate asynchronous I/O, we create a random number at
				# random intervals. Replace the following 2 lines with the real
				# thing.
				#time.sleep(rand.random() * 0.3)
				##self.message_queue.put("\n" + str(self.gcode_queue.qsize()))
				try:
					msg = serialCAN.readline() #rand.random()
				except:
					pass
					#print("no read")
				try:
					msg = msg.decode('utf-8')
				except:
					pass
					#print("decode issue")
					
				if len(msg) > 0:
					
					if msg == "gready\r\n":
						#print("ready set")
						subReadyFlag = True
						if self.gcode_queue.qsize() >= 1:
							msg = ""
					
					self.message_queue.put(msg)
					
					if msg == "Clear Buffer\r\n":
						print("buffer cleared")
						while self.gcode_queue.empty() != True:
							gcode = self.gcode_queue.get_nowait()
						gcode = ""
				msg = ""
				
				if self.gcode_queue.empty() != True and len(gcode) is 0:
						gcode = self.gcode_queue.get_nowait()
				if self.quick_queue.empty() != True:
						qcode = self.quick_queue.get_nowait()
						qcode = qcode.encode()
						#print(len(gcode))
						if qcode == b'Reconnect': #this tells the machine serial thread to close the serial connection
							qcode = ""
							print("Attempting to Re-establish connection")
							serialCAN.close() #closes the serial port
							from time import sleep
							sleep(.25)
							try:
								serialCAN.open()
							except:
								return -1
						else:
							try:
								serialCAN.write(qcode)
							except:
								print("write issue 2")
				if len(gcode) > 0 and subReadyFlag is True:
					#print("gcode seen")
					gcode = gcode.encode()
					#print(len(gcode))
					#print("Sending: ")
					#print(gcode)
					try:
						serialCAN.write(gcode)
						gcode = ""  
					except:
						print("write issue")
					#print("end")
					subReadyFlag = False


def main():
	backend = Data()
	GD = MainProgram(backend)
	
	#GD.bind('<<rout>>', GD.refreshout)
	GD.mainloop()

if __name__ == "__main__":
	 main()
