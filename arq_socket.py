# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 15:40:14 2014
Project	:Python-Project
Version	:0.0.1
@author	:macrobull (http://github.com/macrobull)

"""

from arq import iterFile, ARQ_Protocol

import asyncio


import select as sl
import sys, time


class P2(ARQ_Protocol):

	def openDevice(self, fTxSock, fRxSock, seq = 1):
		if seq:
			self.odev = open(fTxSock, 'wb')
			self.idev = open(fRxSock, 'rb')
		else:
			self.idev = open(fRxSock, 'rb')
			self.odev = open(fTxSock, 'wb')

		txStamps.append(time.time())
		rxStamps.append(time.time())

	def closeDevice(self):
		self.odev.close()
		self.idev.close()

		txStamps.append(time.time())
		rxStamps.append(time.time())

	@asyncio.coroutine
	def sendByte(self, b):

		txStamps.append(time.time())

		self.odev.write(b)
		self.odev.flush()
		yield from asyncio.sleep(0.001)

		txStamps.append(time.time())

	@asyncio.coroutine
	def recvByte(self):
		while True:
			r, w, e = sl.select([self.idev], [], [], 0)
#			print(r,w,e)
			if self.idev in r:

				rxStamps.append(time.time())

#				return self.idev.read(1)
				c = self.idev.read(1)
#				print(c)

				rxStamps.append(time.time())
				return c
			yield from asyncio.sleep(0.001)



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
		print("\tsend <filename> [packet size] [group size]\t: Send file")
		print("\trecv \t\t\t: Receive content")
		print("\t-p; --plot \t\t: plot channel usage")
		print("")
		mode = None

	else:
		mode = sys.argv[1]

	txStamps = []
	rxStamps = []

	if mode == 'send':
		fn = sys.argv[2]
		ps = 35
		gs = 4
		if len(sys.argv)>3: ps = int(sys.argv[3])
		if len(sys.argv)>4: gs = int(sys.argv[4])
		p = P2()
		p.openDevice('tx.sock', 'rx.sock', 0)
		p.sendPackets(iterFile(open(fn, 'rb'), ps), mode = gs)
		time.sleep(0.1)
		p.closeDevice()


	if mode == 'recv':
		p = P2(debug = False)
		p.openDevice('rx.sock', 'tx.sock')
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
