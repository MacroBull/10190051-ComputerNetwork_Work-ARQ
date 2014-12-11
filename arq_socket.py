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

	def closeDevice(self):
		self.odev.close()
		self.idev.close()

	@asyncio.coroutine
	def sendByte(self, b):
		self.odev.write(b)
		self.odev.flush()
		yield from asyncio.sleep(0.001)

	@asyncio.coroutine
	def recvByte(self):
		while True:
			r, w, e = sl.select([self.idev], [], [], 0)
#			print(r,w,e)
			if self.idev in r:
				return self.idev.read(1)
#				c = self.idev.read(1)
#				print(c)
#				return c
			yield from asyncio.sleep(0.001)



if __name__ == '__main__':

	mode = sys.argv[1]

	if mode == 'send':
		fn = sys.argv[2]
		p = P2()
		p.openDevice('tx.sock', 'rx.sock', 0)
		p.sendPackets(iterFile(open(fn, 'rb'), 75), mode = 4)
		time.sleep(0.2)
		p.closeDevice()


	if mode == 'recv':
		p = P2(debug = False)
		p.openDevice('rx.sock', 'tx.sock')
		p.recvPackets()
		p.closeDevice()

