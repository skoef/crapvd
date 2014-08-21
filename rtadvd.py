#!/usr/bin/env python

from scapy.all import *
import yaml
import time
import logging
import os
import getopt

class CRApvD:
	def __init__(self, config):
		self.config = config
		self.prefixes = {}
		self.timers = {}
		self.prefixesMtime = 0
		self.keepRunning = True

		logging.basicConfig(filename=self.config['logfile'], level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %I:%M:%S')
		logging.info('starting crapvd')

		self.updatePrefixes()

	def run(self):
		logging.info('starting sniffing')
		sniff('icmp6', prn=self.sniffHandler, stop_filter=self.keepSniffing)
		logging.info('stopped sniffing')

	def keepSniffing(self, x):
		return not self.keepRunning

	def sniffHandler(self, packet):
		# router sollicitation
		if ICMPv6ND_RS in packet:
			logging.info('received RS from %s', packet[IPv6].src)
			# drop timeout for address to below timeout
			self.timers[packet[IPv6].src] = time.time() - (self.config['interval'] + 1)
			logging.debug('dropped timeout to %d for %s' % (self.timers[packet[IPv6].src], packet[IPv6].src))

		# update prefixes list
		self.updatePrefixes()

		# asynchronously 'schedule' next round of sending directed RA's
		self.checkToSend()

	def checkToSend(self):
		timeout = (time.time() - self.config['interval'])
		for customer in self.prefixes:
			data = self.prefixes[customer]
			if data['lladdr'] not in self.timers:
				self.timers[data['lladdr']] = time.time()
				logging.debug('%s not found in timers, resetting' % data['lladdr'])
			elif self.timers[data['lladdr']] < timeout:
				logging.debug('timeout for %s: %d < %d, sending' % (data['lladdr'], self.timers[data['lladdr']], timeout))
				self.sendRA(data['lladdr'], data['prefix'])

	def sendRA(self, lladdr, prefix):
		logging.info('sending prefix %s to address %s' % (prefix, lladdr))
		# IPv6 packet
		ip6 = IPv6()
		# forge ip6 source address
		ip6.src = self.config['srcll']
		ip6.dst = lladdr
		# make packet an RA
		ra = ICMPv6ND_RA()
		# forge source mac address
		src = ICMPv6NDOptSrcLLAddr()
		src.lladdr = self.config['srcmac']
		# set right prefix data
		preinf = ICMPv6NDOptPrefixInfo()
		preinf.prefix = prefix.split('/')[0]
		preinf.prefixlen = int(prefix.split('/')[1])
		# glue parts together and send it
		if send(ip6/ra/src/preinf) is None:
			logging.debug('sent successful, resetting timer for %s' % lladdr)
			self.timers[lladdr] = time.time()

	def updatePrefixes(self):
		mtime = os.path.getmtime(self.config['prefixfile'])
		if mtime > self.prefixesMtime:
			if self.prefixesMtime != 0:
				logging.info('prefixes file %s updated, reloading' % self.config['prefixfile'])
			self.prefixesMtime = mtime
			file = open(self.config['prefixfile'], 'r')
			self.prefixes = yaml.load(file)
			logging.info('%d prefixes loaded from %s' % (len(self.prefixes), self.config['prefixfile']))

def usage():
	print """Usage: %s -s srcll -m srcmac [-i interval] [-c prefixesfile] [-l logfile]
	""" % os.path.basename(sys.argv[0])

if __name__ == '__main__':
	# defaults
	config = {
		'interval': 60,
		'logfile': '/var/log/crapvd.log',
		'prefixfile': '/etc/prefixes.yaml',
	}

	# parse options
	try:
		opts, args = getopt.getopt(sys.argv[1:], 's:m:i:c:l:', [])
	except getopt.GetoptError as err:
		print str(err)
		sys.exit(2)

	for o, a in opts:
		if o == '-s':
			config['srcll'] = a
		elif o == '-m':
			config['srcmac'] = a
		elif o == '-i':
			config['interval'] = int(a)
		elif o == '-c':
			config['prefixfile'] = a
		elif o == '-l':
			config['logfile'] = a
		else:
			print "Error: unknown option %s" % o
			usage()
			sys.exit(2)

	if 'srcmac' not in config or 'srcll' not in config:
		print "Error: -s and -m are required"
		usage()
		sys.exit(2)

	c = CRApvD(config)
	c.run()
