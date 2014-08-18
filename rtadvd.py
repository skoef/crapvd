#!/usr/bin/env python

from scapy.all import *
import yaml
import signal
import time
import logging

class rtadvd:
  def __init__(self):
	self.config = {
		'interval': 30,
		'logfile': '/var/log/rtadv.log',
	}
	self.keepRunning = True

	logging.basicConfig(filename=self.config['logfile'], level=logging.DEBUG, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %I:%M:%S')
	logging.info('starting rtadv')

	self.importconf('config.yaml')
	self.importprefixes()
	signal.signal(signal.SIGUSR1, self.sighandler)

  def run(self):
	logging.debug('sending advertisments every %d seconds' % self.config['interval'])
	while self.keepRunning:
		for p in self.config['prefixes']:
			prefix = self.config['prefixes'][p]
			packet = self.craftICMPv6(prefix)
			packet.display()
			send(packet)
			logging.debug('sent RA to %s: %s' % (p, prefix['prefix']))
		time.sleep(self.config['interval'])

  def craftICMPv6(self, prefix):
	# create IP6 packet
	ip6 = IPv6()
	ip6.src = self.config['srcll']
	ip6.dst = prefix['lladdr']
	# fill ip6 packet with icmpv6 info
	ra = ICMPv6ND_RA()
	src = ICMPv6NDOptSrcLLAddr()
	src.lladdr = self.config['srcmac']
	mtu = ICMPv6NDOptMTU()
	preinf = ICMPv6NDOptPrefixInfo()
	preinf.prefix = prefix['prefix'].split('/')[0]
	preinf.prefixlen = int(prefix['prefix'].split('/')[1])
	# glue all parts together
	return (ip6/ra/src/mtu/preinf)

  def importconf(self, configfile):
  	file = open(configfile, 'r')
	self.config = dict(self.config.items() + yaml.load(file).items())
	logging.debug('loaded config from %s' % configfile)

  def importprefixes(self):
  	file = open(self.config['prefixfile'], 'r')
  	self.config['prefixes'] = yaml.load(file)
	logging.info('%d prefixes loaded from %s' % (len(self.config['prefixes']), self.config['prefixfile']))

  def sighandler(self, sig, *args):
  	if sig is 10:
		logging.debug('SIGUSR1 received, reloading prefixes')
		self.importprefixes()

if __name__ == '__main__':
	r = rtadvd()
	r.run()
