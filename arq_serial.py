# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 15:40:14 2014
Project	:Python-Project
Version	:0.0.1
@author	:macrobull (http://github.com/macrobull)

"""

from arq import ARQ_Protocol

import asyncio
import serial
import sys, time

from macrobull.misc import serialChecker


def iterFileWithChunkIndex(f, chunk_size):
	idx = 0
	buf = b''
	while True:
		if len(buf) < chunk_size: buf += f.read(chunk_size)
		p = buf.find(b'\n') +1
		if (0<p<chunk_size):
			r = buf[:p]
			buf = buf[p:]
		elif len(buf):
			r = buf[:chunk_size]
			buf = buf[chunk_size:]
		else:
			break
		idx += 1
		if r: r = str(idx).encode() + b':' + r
		yield r

records = {}
chunks = {}
def handleChunkIndex(idx, s):
	s = s.decode('utf-8', 'ignore')
	cPos = s.index(':')
	chunk_idx, s = int(s[:cPos]), s[cPos+1:]
#	if not((idx in records) and (records[idx] == chunk_idx)):
	if True:
		records[idx] = chunk_idx
		chunks[chunk_idx] = chunks[chunk_idx] + 1 if chunk_idx in chunks else 1
		print('[%4d][%4d]' % (idx, chunk_idx), s)


class Protocol_Serial(ARQ_Protocol):

	def openDevice(self, dev = None):
		kwargs = dict(baudrate = 460800)
		kwargs['timeout'] = 100. / kwargs['baudrate']
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
		#yield from asyncio.sleep(0.0001)
		txStamps.append(time.time())

	@asyncio.coroutine
	def recvByte(self):
		while not(self.dev.inWaiting()):
			yield from asyncio.sleep(20./self.dev.baudrate)
#			time.sleep(0.001)
		rxStamps.append(time.time())
#		return self.dev.read(1)
		c = self.dev.read(1)
		rxStamps.append(time.time())
#		print(str(c)[2:-1], end = '', flush = True)
		return c



if __name__ == '__main__':

	debug = False
	if sys.argv.count('-d'):
		sys.argv.pop(sys.argv.index('-d'))
		debug = True
	fPlot = False
	if sys.argv.count('-p'):
		sys.argv.pop(sys.argv.index('-p'))
		fPlot = True
	if sys.argv.count('--plot'):
		sys.argv.pop(sys.argv.index('--plot'))
		fPlot = True

	if len(sys.argv) < 2:
		print("python3 arq_serial.py : ")
		print("\tsend <device> <filename> [packet size] [group size]\t: Send file")
		print("\trecv [device] \t\t: Receive content")
		print("\t-p; --plot \t\t: plot channel usage")
		print("\t-d \t\t\t: debug")
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
		p = Protocol_Serial(timeout = 1., debug = debug)
		p.openDevice(dev)
		p.sendFrames(iterFileWithChunkIndex(open(fn, 'rb'), ps), mode = gs)
		time.sleep(0.1)
		p.closeDevice()


	if mode == 'recv':
		dev = None
		if len(sys.argv)>2: dev = sys.argv[2]
		p = Protocol_Serial(timeout =2., debug = debug)
		p.openDevice(dev)
		p.recvFrames(process = handleChunkIndex)
		p.closeDevice()

		err = {}
		for c in range(1, max(chunks.keys())):
			if not(c in chunks and chunks[c] == 1):
				err[c] = chunks[c] if c in chunks else 0

		if err:
			print(records)
			print(err)

	if fPlot:
#		SR = 400
		SR = int(len(txStamps) / 20000) + 1
		def genUsage(s):
			ss = 0
			t_st = s[0]
			ts = [0]
			us = [0]
			for i, t in enumerate(s[1:-1]):
				ss += t if (i & 1) else -t
				if i % SR == 0:
					i = int(i / SR)
					ts.append(t - t_st)
					ts.append(t - t_st)
					us.append(i & 1)
					us.append(1 - (i & 1))
			ts.append(s[-1] - t_st)
			us.append(0)
			return ts, us, ss /(s[-1] - s[0])

		from pylab import *

		t, u, r = genUsage(txStamps)
		print("Tx use rate = ", r)
		subplot(211, title='TX usage')
		fill_between(t, 0, u)
		plot(t, u)
		xlabel('Time/s')
		yticks([])

		t, u, r = genUsage(rxStamps)
		print("Rx use rate = ", r)
		subplot(212, title='RX usage')
		fill_between(t, 0, u)
		plot(t, u)
		xlabel('Time/s')
		yticks([])

		show()
