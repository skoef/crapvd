# Custom Router APVertisment Daemon

Send custom, directed IPv6 router advertisements on any network.

## Background
At my current employer, we run a lot of customer virtual machines in shared VLANs.
Each of these customers gets an IPv6 /64, but still have to use a prefixlen of 48 since
the router has a /48 gateway address. We know this is not how it should be implemented,
but resist to the fact of configuring gateways or next-hops for each /64. So this is where
we came up with:

- generate lists of mac address and prefix combinations per customer
- listen for router solicitation from any of these link-local addresses
- reply with a matching router advertisements, forging the given link-local address and MAC
address of the router itself
- send periodic router advertisements anyhow, with or without router solicitation

## Usage
Given the following YAML based config file:
```YAML
customer1:
  macaddr: '01:23:45:67:89:ab'
  prefix:  '2a01:f000:f000:f000::/64'
```

By default, `crapvd` will listen to router advertisements from the actual router and then uses the IPv6 link-local and MAC address found in there to send more specific router advertisements to each client. For information how to override these, and other available settings, refer to the example config file.

## Dependencies
```crapvd``` depends on [scapy](http://www.secdev.org/projects/scapy/ "Scapy") and [pyyaml](http://pyyaml.org/ "PyYAML")
