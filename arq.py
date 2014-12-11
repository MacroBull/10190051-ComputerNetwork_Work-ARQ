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

def iterFile(f, chunk_size):
	while True:
		r = f.read(chunk_size)
		yield r
		if not r: break # yield '' for EOF

class ARQ_Error(Exception):
	def __init__(self, idx, name, msg):
		self.idx = idx
		self.name = name
		self.msg = msg

class ARQ_Frame():
	def __init__(self, 							# idx, len < 0x80
		fHead = b'\xac', fTail = b'\xa3',			# >= 0x80
		ACK = b'\xaa', NAK = b'\xa5', 			# >= 0x80
		checksum = lambda buf:crc32(buf)&0xff		# simple 1 byte checksum
		):
			self.fHead, self.fTail = fHead, fTail	# frame head and tail
			self.ACK, self.NAK = ACK, NAK
			self.csa = checksum					#checksum algorithm
			self.extraBytes = 5 	# head + idx + len + csum + tail

	def build(self, idx, s): 	# Build data s @idx
		idx_byte = bytes([idx])
		if type(s) is bool: 	# Response frame
			r_byte = self.ACK if s else self.NAK
			return self.fHead + idx_byte + r_byte + self.fTail

		if type(s) is bytes: 	# Data frame
			if len(s) >= 0x80: 	# Check legnth
				raise ARQ_Error(idx, "Data too long",
					"Length is {}.".format(len(s)))
			len_byte = bytes([len(s)])
			csum_byte = bytes([self.csa(s)])
			return self.fHead + idx_byte + len_byte + s + csum_byte + self.fTail

		raise ARQ_Error(idx, "Unexcepted data type",
			"Data type is {}.".format(type(s)))

	def parse(self, s): 	# Parse a frame
		if type(s) is not bytes:
			raise ARQ_Error(None, "Unexcepted data type",
				"Data type is {}.".format(type(s)))

		if not(s.startswith(self.fHead) and s.endswith(self.fTail)):
			raise ARQ_Error(None, "Not an ARQ frame",
				"Frame = [{}..{}].".format(s[0], s[-1]))

		idx, s= s[1], s[2:-1] 	# Remove head, idx and tail
		if len(s) == 1: # Response frame
			if s[:] == self.ACK: return idx, True
			if s[:] == self.NAK: return idx, False
			raise ARQ_Error(idx, "Invalid response",
				"Response {} is {}.".format(idx, s[0]))
		else: # Data frame
			length, s, csum = s[0], s[1:-1], s[-1]
			if length != len(s):
				raise ARQ_Error(idx, "Length mismatch",
					"Frame {} size is {}, {} expected.".format(
					idx, len(s), length))
			ccsum = self.csa(s)
			if csum != ccsum:
				raise ARQ_Error(idx, "CRC mismatch",
					"Frame {} CRC is {}, {} expected.".format(
					idx, ccsum, csum))
			return idx, s

class ARQ_Protocol():
	def __init__(self, timeout = 1., initLen = 35,
		frameFactory = ARQ_Frame(), debug = True):
			self.timeout = timeout
			self.len = initLen
			self.ff = frameFactory
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
	def sendFrame(self, idx, s):
		frame = self.ff.build(idx, s)
		for b in frame: 	# Async sending datae
			yield from self.sendByte(bytes([b])) 	# keep as bytes
		if self.debug: print('<- [{}] {}'.format(idx, s))

	@asyncio.coroutine
	def recvFrame(self):
		while True: 	# Wait for frame head
			b = yield from self.recvByte()
			if b == self.ff.fHead: break
		buf = b
		while True:
			b = yield from self.recvByte()
			buf += b
			if b == self.ff.fTail: 	# Wait for frame tail
				l = buf[2] 	# Expected length or response
				if (l>0x80)or(l + self.ff.extraBytes == len(buf)):
					if self.debug: print('->', buf)#.decode('utf-8', 'ignore'))
					return self.ff.parse(buf)

				if l + self.ff.extraBytes <= len(buf):
					buf = bytes([]) 	# Discard buffer

	def recvFrames(self, process = lambda idx, data : 	# Just print Data
		print('[%d]' % idx, data.decode('utf-8', 'ignore'))
		):

		@asyncio.coroutine
		def routine():
			while True:
				try:
					idx, data = yield from asyncio.wait_for(
						self.recvFrame(), timeout = self.timeout)
				except asyncio.TimeoutError:
					pass
				except ARQ_Error as e:
					print(e)
					if e.idx: 	# Reply NAK
						yield from self.sendFrame(e.idx, False)
				except Exception as e:
					print(e)
				else: 	# Reply ACK
					yield from self.sendFrame(idx, True)
					if len(data) == 0: break	# get EOF, stop
					process(idx, data)

		loop = asyncio.get_event_loop()
		loop.run_until_complete(routine())
		loop.close()

	def sendFrames(self, src, mode = 1):

		@asyncio.coroutine
		def checkLater(idx, value): 	# Check if idx is sucessfully sent
			yield from asyncio.sleep(self.timeout)
			if (pos[idx] == value) and (idx not in busy):
				print("Frame {} response timeout.".format(idx))
				busy.append(idx) 	# Reschedule

		@asyncio.coroutine
		def send():
			for p in src: 	# Iterate data source
				while True:
					while not ready:
						while not (ready or busy): 	# Wait for ongoings
							yield from asyncio.sleep(WAIT_STEP)
						if ready: break
						idx = busy.pop(0)
						yield from self.sendFrame(idx, frames[idx])
						asyncio.async(checkLater(idx, pos[idx]))

					idx = ready.pop(0)
					if idx not in busy: break
				# Queue a new chunk
				busy.append(idx)
				frames[idx] = p
				cnt[0] += 1
				pos[idx] = cnt[0]

			while busy:	# Finish remained works
				idx = busy.pop(0)
				yield from self.sendFrame(idx, frames[idx])
				asyncio.async(checkLater(idx, pos[idx]))

			cnt[2] = 0	# Sender has done

		@asyncio.coroutine
		def recv():
			while (cnt[2])or(cnt[1]<cnt[0]): 	# Still running
				try:
					idx, data = yield from self.recvFrame()
				except ARQ_Error as e:	# Receive error
					print(e)
					idx = e.idx
					if idx and (idx not in busy): busy.append(idx)
				else:
					if data:	# got ACK
						ready.append(idx)
						cnt[1] += 1
					else:	# got NAK
						if idx not in busy: busy.append(idx)

			if self.debug: print('Counter = ', cnt[0], cnt[1])
			loop.stop()

		cnt = [0, 0, 1] # tx_cnt, rx_cnt, state
		ready = list(range(mode))
		busy = []
		pos = [0 for i in range(mode)]
		frames = [None for i in range(mode)]

		loop = asyncio.get_event_loop()
		asyncio.async(send())
		asyncio.async(recv())
		loop.run_forever()	# Concurrent workers
		loop.close()