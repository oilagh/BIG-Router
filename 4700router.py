#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math

# IP/SUBNET UTILITIES
# Routers operate on binary numbers and not dotted IP strings. Need to implement:
    # Converting IP strings to 32-bit integers
    # Converting integers to IP strings
    # Turning subnet masks into prefix lengths (/24, /16, etc.)
    # Computing network addresses
    # Checking if a destination belongs to a prefix (longest-prefix match)

# Converts dotted IPv4 address into a 32-bit integer so we can perform bitwise routing calculations. Longest-prefix matching is implemented 
# using bit masking, which only works on numeric representations of IP addresses.
def ip_to_int(ip):

    parts = ip.split(".")
    if len(parts) != 4:
        raise ValueError("Invalid IPv4 format")

    value = 0

    for p in parts:
        octet = int(p)
        if octet < 0 or octet > 255:
            raise ValueError("Invalid IPv4 octet")

        # Shift left 8 bits to make room, then insert this octet.
        value = (value << 8) | octet

    return value

# Converts a 32-bit integer back into dotted IPv4 format. Human-readable IP strings are expected when we send routing tables 
# or responses, but internally we store everything as integers.
def int_to_ip(value):
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))

# Converts a subnet mask into its prefix length representation. BGP decisions compare prefix lengths numerically (e.g., /24 is
# more specific than /16).
def netmask_to_prefixlen(mask):

    m = ip_to_int(mask)

    prefix = 0
    seen_zero = False

    # Examine bits from most significant → least significant
    for i in range(31, -1, -1):
        bit = (m >> i) & 1

        if bit == 1:
            # Valid masks must be contiguous ones.
            if seen_zero:
                raise ValueError("Non-contiguous subnet mask")
            prefix += 1
        else:
            seen_zero = True

    return prefix

# Convert a prefix length back into a subnet mask. Some operations (like matching or aggregation) require the mask
# itself rather than just the prefix length.
def prefixlen_to_mask(prefixlen):

    if prefixlen == 0:
        return 0

    # Create mask with prefixlen leading 1s.
    return (0xFFFFFFFF << (32 - prefixlen)) & 0xFFFFFFFF

# computes the base network address for a prefix. BGP stores routes as networks (e.g., 192.168.1.0/24), not individual host IPs. 
def network_address(ip_int, prefixlen):
    mask = prefixlen_to_mask(prefixlen)
    return ip_int & mask

# Determines whether a destination IP belongs to a given network. Implements the core of LONGEST PREFIX MATCH, which is how routers decide where to forward packets.
def prefix_match(ip_int, net_int, prefixlen):
    mask = prefixlen_to_mask(prefixlen)
    return (ip_int & mask) == net_int

class Router:

    relations = {}
    sockets = {}
    ports = {}

    def __init__(self, asn, connections):
        print("Router at AS %s starting up" % asn)
        self.asn = asn
        for relationship in connections:
            port, neighbor, relation = relationship.split("-")

            self.sockets[neighbor] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sockets[neighbor].bind(('localhost', 0))
            self.ports[neighbor] = int(port)
            self.relations[neighbor] = relation
            self.send(neighbor, json.dumps({ "type": "handshake", "src": self.our_addr(neighbor), "dst": neighbor, "msg": {}  }))

    def our_addr(self, dst):
        quads = list(int(qdn) for qdn in dst.split('.'))
        quads[3] = 1
        return "%d.%d.%d.%d" % (quads[0], quads[1], quads[2], quads[3])

    def send(self, network, message):
        self.sockets[network].sendto(message.encode('utf-8'), ('localhost', self.ports[network]))

    def run(self):
        while True:
            socks = select.select(self.sockets.values(), [], [], 0.1)[0]
            for conn in socks:
                k, addr = conn.recvfrom(65535)
                srcif = None
                for sock in self.sockets:
                    if self.sockets[sock] == conn:
                        srcif = sock
                        break
                msg = k.decode('utf-8')

                print("Received message '%s' from %s" % (msg, srcif))
        return

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='route packets')
    parser.add_argument('asn', type=int, help="AS number of this router")
    parser.add_argument('connections', metavar='connections', type=str, nargs='+', help="connections")
    args = parser.parse_args()
    router = Router(args.asn, args.connections)
    router.run()
