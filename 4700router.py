#!/usr/bin/env -S python3 -u

import argparse, socket, time, json, select, struct, sys, math

# IP/Subnetting Stuff

# convert dotted IPv4 String into 32-bit integer
def ip_to_int(ip):
    parts = ip.split(".") 
    if len(parts) != 4:
        raise ValueError("Invalid IPv4 format")

    value = 0; #initializing

    for p in parts:
        octet = int(p)
        if octet < 0 or octet > 255:
            raise ValueError("Invalid IPv4 octet")

        # shifting bits left 8 to accomodate new octet using bitwise OR to insert it
        value = (value << 8) | octet

    return value



# convert 32-bit string back into IPv4 address
return ".".join(str((value >> shift) &225) for shift in (24, 16, 8, 0) # value >> shift moves octet to the very right and &255 isolates just that octet

# convert subnet mask string into prefix length
def netmask_to_prefixlen(mask):
    m = ip_to_int(mask) # convert mask to int
    prefix = 0 # represents amount of leading 1-bits
    seen_zero = False

    # bits from most to least significant
    for i in range (31, -1, -1):
        bit = (m >> 1) & 1

        if bit == 1:
            

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
