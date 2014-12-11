# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 15:40:14 2014
Project	:Python-Project
Version	:0.0.1
@author	:macrobull (http://github.com/macrobull)

"""

from arq import iterFile, ARQ_Protocol

import asyncio
import serial
import sys, time

from macrobull.misc import serialChecker


class P1(ARQ_Protocol):

	def openDevice(self, dev = None):
		kwargs = dict(baudrate = 9600, timeout = 0.01)
		if not dev: dev = serialChecker()
		print("Device:{}".format(dev))
		self.dev = serial.Serial(dev, **kwargs)

	def closeDevice(self):
		self.dev.close()

	@asyncio.coroutine
	def sendByte(self, b):
		self.dev.write(b)
		yield from asyncio.sleep(0.001)

	@asyncio.coroutine
	def recvByte(self):
		while not(self.dev.inWaiting()):
			yield from asyncio.sleep(0.001)
#			time.sleep(0.001)
		return self.dev.read(1)
#		c = self.dev.read(1)
#		print(str(c)[2:-1], end = '', flush = True)
#		return c



if __name__ == '__main__':

	mode = sys.argv[1]

	if mode == 'send':
		fn = sys.argv[2]
		p = P1(timeout = 2.)
		p.openDevice('/dev/rfcomm5')
		p.sendPackets(iterFile(open(fn, 'rb'), 75), mode = 4)
		time.sleep(0.2)
		p.closeDevice()


	if mode == 'recv':
		p = P1(timeout = 4., debug = True)
		p.openDevice()
		p.recvPackets()
		p.closeDevice()

