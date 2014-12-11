# -*- coding: utf-8 -*-
"""
Created on Wed Dec 10 00:06:48 2014
Project	: A simple implementation of ARQ (http://www.wikiwand.com/en/Automatic_repeat_reqxuest)
Version	:0.0.1
@author	:macrobull (http://github.com/macrobull)

"""

import asyncio
from binascii import crc32

WAIT_STEP = 0.001

def iterFile(f, l):
	while True:
		r = f.read(l)
		yield r
		if not r: break

class ARQ_Error(Exception):
	def __init__(self, idx, name, msg):
		self.idx = idx
		self.name = name
		self.msg = msg

class ARQ_Packet():
	def __init__(self, #idx, len < 0x80
		fHead = b'\xac', fTail = b'\xa3',
		ACK = b'\xaa', NAK = b'\xa5', # >= 0x80
		checksum = lambda buf:crc32(buf)&0xff):
			self.fHead, self.fTail = fHead, fTail # fram head and tail
			self.ACK, self.NAK = ACK, NAK
			self.csa = checksum #checksum algorithm
			self.extraBytes = 5 # head + idx + len + csum + tail

	def packet(self, idx, s):
		idx_byte = bytes([idx])
		if type(s) is bool:
			if s:
				return self.fHead + idx_byte + self.ACK + self.fTail
			else:
				return self.fHead + idx_byte + self.NAK + self.fTail

		if type(s) is bytes:
			if len(s) >= 0x80:
				raise ARQ_Error(idx, "Data too long",
					"Length is {}.".format(len(s)))
			len_byte = bytes([len(s)])
			csum_byte = bytes([self.csa(s)])
			return self.fHead + idx_byte + len_byte + s + csum_byte + self.fTail

		raise ARQ_Error(idx, "Unexcepted data type",
			"Data type is {}.".format(type(s)))

	def unpacket(self, s):
		if type(s) is not bytes:
			raise ARQ_Error(None, "Unexcepted data type",
				"Data type is {}.".format(type(s)))

		if not(s.startswith(self.fHead) and s.endswith(self.fTail)):
			raise ARQ_Error(None, "Not a ARQ packet",
				"Packet = [{}..{}].".format(s[0], s[-1]))

		idx, s= s[1], s[2:-1]
		if len(s) == 1: # Response
			if s[:] == self.ACK:
				return idx, True
			if s[:] == self.NAK:
				return idx, False
			raise ARQ_Error(idx, "Invalid response",
				"Response {} is {}.".format(idx, s[0]))
		else: # Packet
			length, s, csum = s[0], s[1:-1], s[-1]
			if length != len(s):
				raise ARQ_Error(idx, "Length mismatch",
					"Packet {} size is {}, {} expected.".format(
					idx, len(s), length))
			ccsum = self.csa(s)
			if csum != ccsum:
				raise ARQ_Error(idx, "CRC mismatch",
					"Packet {} CRC is {}, {} expected.".format(
					idx, ccsum, csum))
			return idx, s

class ARQ_Protocol():
	def __init__(self, timeout = 1., initLen = 35,
		packetFactory = ARQ_Packet(), debug = True):
			self.timeout = timeout
			self.len = initLen
			self.pf = packetFactory
			self.debug = debug

	def openDevice(self):
		raise NameError("Undefined Method")

	def closeDevice(self):
		raise NameError("Undefined Method")

	@asyncio.coroutine
	def sendByte(self, b):
		raise NameError("Undefined Method")

	@asyncio.coroutine
	def recvByte(self):
		raise NameError("Undefined Method")

	@asyncio.coroutine
	def sendPacket(self, idx, s):
		packet = self.pf.packet(idx, s)
		for b in packet:
			yield from self.sendByte(bytes([b]))
		if self.debug: print('-> [{}] {}'.format(idx, s))

	@asyncio.coroutine
	def recvPacket(self):
		while True:
			b = yield from self.recvByte()
			if b == self.pf.fHead: break
		buf = b
		while True:
			b = yield from self.recvByte()
			buf += b
			if (len(buf)>=4) and (b == self.pf.fTail):
				l = buf[2]
				if (l>0x80)or(l + self.pf.extraBytes == len(buf)):
					if self.debug: print('<-', buf)#.decode('utf-8', 'ignore'))
					return self.pf.unpacket(buf)
				elif l + self.pf.extraBytes < len(buf):
					buf = bytes([])

	def recvPackets(self, process = lambda idx, data :
		print('[%d]' % idx, data.decode('utf-8', 'ignore')) ):

		@asyncio.coroutine
		def routine():
			while True:
				try:
					idx, data = yield from asyncio.wait_for(
						self.recvPacket(), timeout = self.timeout)
				except asyncio.TimeoutError:
					pass
				except ARQ_Error as e:
					print(e)
					if e.idx:
						yield from self.sendPacket(e.idx, False)
				else:
					yield from self.sendPacket(idx, True)
					if len(data) == 0:
						break
					process(idx, data)

		loop = asyncio.get_event_loop()
		loop.run_until_complete(routine())
		loop.close()

	def sendPackets(self, src, mode = 1):

		@asyncio.coroutine
		def checkLater(idx, value):
			yield from asyncio.sleep(self.timeout)
			if (current[idx] == value) and (idx not in busy):
				print("Packet {} response timeout.".format(idx))
				busy.append(idx)

		@asyncio.coroutine
		def send():
			for p in src:

				while True:
					while not ready:
						while not (ready or busy):
							yield from asyncio.sleep(WAIT_STEP)
						if ready: break
						idx = busy.pop(0)
						yield from self.sendPacket(idx, packets[idx])
						asyncio.async(checkLater(idx, current[idx]))

					idx = ready.pop(0)
					if idx not in busy: break

				busy.append(idx)
				packets[idx] = p
				cnt[0] += 1
				current[idx] = cnt[0]

			while busy:
				idx = busy.pop(0)
				yield from self.sendPacket(idx, packets[idx])
				asyncio.async(checkLater(idx, current[idx]))

			cnt[2] = 0

		@asyncio.coroutine
		def recv():
			while (cnt[2])or(cnt[1]<cnt[0]):
				try:
					idx, data = yield from self.recvPacket()
				except ARQ_Error as e:
					print(e)
					idx = e.idx
					if idx and (idx not in busy): busy.append(idx)
				else:
					if data:
						ready.append(idx)
						cnt[1] += 1
					else:
						if idx not in busy: busy.append(idx)

			print('Statistics: cnt = {}'.format(cnt))
			loop.stop()

		cnt = [0, 0, 1] # tx_cnt, rx_cnt, state
		ready = list(range(mode))
		busy = []
		current = [0 for i in range(mode)]
		packets = [None for i in range(mode)]

		loop = asyncio.get_event_loop()
		asyncio.async(send())
		asyncio.async(recv())
		loop.run_forever()
		loop.close()



