# Custom Router APVertisment Daemon

Send custom, directed IPv6 router advertisments on any network.

## Background
At my current employer, we run a lot of customer virtual machines in shared VLANs. 
Each of these customers gets a IPv6 /64, but still have to use a prefixlen of 48 since 
the router has a /48 gateway address. We know this is not how it should be implemented, 
but resist to the fact of configuring gateways or next-hops for each /64. So this is where 
we came up with:

- generate lists of link-local address and prefix combinations per customer
- listen for router solicitments from any of these link-local addresses
- reply with a matching router advertisments, forging the given link-local address and MAC
address of the router itself
- send periodic router advertisements anyhow, with or without router solicitments

## Usage
Given the following YAML based config file:
```YAML
customer1:
  lladdr: 'fe80::5054:ff:fe00:f000'
  prefix: '2a01:f000:f000:f000::/64'
```
we can start ```carpvd``` with link-local address and MAC address from the router:
```
$ carpvd -m 00:01:02:03:05:05 -s fe80:f000:1 -c /path/to/prefixes.yaml
```
