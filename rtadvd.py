#!/usr/bin/env python

from scapy.all import *
import yaml
import signal
import time
import logging
import sys

class rtadvd:
	def __init__(self):
		self.config = {
			'interval': 30,
			'logfile': '/var/log/rtadv.log',
		}
		self.router = {}
		self.prefixes = {}
		self.timers = {}
		self.keepRunning = True
		self.routerFound = False

		logging.basicConfig(filename=self.config['logfile'], level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %I:%M:%S')
		logging.info('starting rtadv')

		self.importconf('config.yaml')
		self.importprefixes()
		# NOTE: sighandler broken when in select-loop
		signal.signal(signal.SIGUSR1, self.sighandler)

	def run(self):
		logging.info('starting sniffing')
		sniff('icmp6', prn=self.sniffHandler, stop_filter=self.keepSniffing)
		logging.info('stopped sniffing')

	def keepSniffing(self, x):
		return not self.keepRunning

	def sniffHandler(self, packet):
		# router sollicitation
		if ICMPv6ND_RS in packet:
			# do not reply to RS when we haven't found the router
			if self.routerFound is False:
				logging.debug('ignoring RS from %s since we have no route ourselves' % packet[IPv6].src)
			else:
				logging.info('received RS from %s', packet[IPv6].src)
				# drop timeout for address to below timeout
				self.timers[packet[IPv6].src] = time.time() - (self.config['interval'] + 1)
				logging.debug('dropped timeout to %d for %s' % (self.timers[packet[IPv6].src], packet[IPv6].src))

		# router advertisment
		if ICMPv6ND_RA in packet:
			# do not listen to RA when we found the router
			if self.routerFound is True:
				#logging.debug('ignoring RA from %s since we already know the route' % packet[IPv6].src)
				pass
			else:
				self.router['srcll'] = packet[IPv6].src
				self.router['srcmac'] = packet[IPv6][ICMPv6ND_RA].lladdr
				self.routerFound = True
				logging.info('found RA from %s for %s, proceeding' % (self.router['srcll'], self.router['srcmac']))

		# asynchronously 'schedule' next round of sending directed RA's
		if self.routerFound is True:
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
			##else:
			##	logging.debug('no timeout for %s: %d >= %d , delaying' % (data['lladdr'], self.timers[data['lladdr']], timeout))

	def sendRA(self, lladdr, prefix):
		logging.info('sending prefix %s to address %s' % (prefix, lladdr))
		# IPv6 packet
		ip6 = IPv6()
		# forge ip6 source address
		ip6.src = self.router['srcll']
		ip6.dst = lladdr
		# make packet an RA
		ra = ICMPv6ND_RA()
		# forge source mac address
		src = ICMPv6NDOptSrcLLAddr()
		src.lladdr = self.router['srcmac']
		# set right prefix data
		preinf = ICMPv6NDOptPrefixInfo()
		preinf.prefix = prefix.split('/')[0]
		preinf.prefixlen = int(prefix.split('/')[1])
		# glue parts together and send it
		if send(ip6/ra/src/preinf) is None:
			logging.debug('sent successful, resetting timer for %s' % lladdr)
			self.timers[lladdr] = time.time()

	def importconf(self, configfile):
		file = open(configfile, 'r')
		self.config = dict(self.config.items() + yaml.load(file).items())
		logging.debug('loaded config from %s' % configfile)

	def importprefixes(self):
		file = open(self.config['prefixfile'], 'r')
		self.prefixes = yaml.load(file)
		logging.info('%d prefixes loaded from %s' % (len(self.prefixes), self.config['prefixfile']))

	def sighandler(self, sig, *args):
		if sig is 10:
			logging.debug('SIGUSR1 received, reloading prefixes')
			self.importprefixes()

if __name__ == '__main__':
	r = rtadvd()
	r.run()
