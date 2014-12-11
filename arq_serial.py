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
		txStamps.append(time.time())
		rxStamps.append(time.time())

	def closeDevice(self):
		self.dev.close()
		txStamps.append(time.time())
		rxStamps.append(time.time())

	@asyncio.coroutine
	def sendByte(self, b):
		txStamps.append(time.time())
		self.dev.write(b)
		yield from asyncio.sleep(0.001)
		txStamps.append(time.time())

	@asyncio.coroutine
	def recvByte(self):
		while not(self.dev.inWaiting()):
			yield from asyncio.sleep(0.001)
#			time.sleep(0.001)
		rxStamps.append(time.time())
#		return self.dev.read(1)
		c = self.dev.read(1)
		rxStamps.append(time.time())
#		print(str(c)[2:-1], end = '', flush = True)
		return c



if __name__ == '__main__':

	fPlot = False
	if sys.argv.count('-p'):
		sys.argv.pop(sys.argv.index('-p'))
		fPlot = True
	if sys.argv.count('--plot'):
		sys.argv.pop(sys.argv.index('--plot'))
		fPlot = True

	if len(sys.argv) < 2:
		print("python3 arq_socket.py : ")
		print("\tsend <device> <filename> [packet size] [group size]\t: Send file")
		print("\trecv [device] \t\t: Receive content")
		print("\t-p; --plot \t\t: plot channel usage")
		print("")
		mode = None

	else:
		mode = sys.argv[1]

	txStamps = []
	rxStamps = []

	if mode == 'send':
		dev = sys.argv[2]
		fn = sys.argv[3]
		ps = 35
		gs = 4
		if len(sys.argv)>4: ps = int(sys.argv[4])
		if len(sys.argv)>5: gs = int(sys.argv[5])
		p = P1(timeout = 3.)
		p.openDevice(dev)
		p.sendPackets(iterFile(open(fn, 'rb'), ps), mode = gs)
		time.sleep(0.1)
		p.closeDevice()


	if mode == 'recv':
		dev = None
		if len(sys.argv)>2: dev = int(sys.argv[2])
		p = P1(timeout = 5., debug = False)
		p.openDevice(dev)
		p.recvPackets()
		p.closeDevice()

	if fPlot:
		def genUsage(s):
			ss = 0
			t_st = s[0]
			ts = [0]
			us = [0]
			for i, t in enumerate(s[1:-1]):
				ts.append(t - t_st)
				ts.append(t - t_st)
				us.append(i & 1)
				us.append(1 - (i & 1))
				ss += t if (i & 1) else -t
			ts.append(s[-1] - t_st)
			us.append(0)
			return ts, us, ss /(s[-1] - s[0])

		from pylab import *

		t, u, r = genUsage(txStamps)
		print("Tx use rate = ", r)
		subplot(211, title='tx')
		fill_between(t, 0, u)
		plot(t, u)

		t, u, r = genUsage(rxStamps)
		print("Rx use rate = ", r)
		subplot(212, title='rx')
		fill_between(t, 0, u)
		plot(t, u)

		show()
