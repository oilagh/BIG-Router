def ip_to_int(ip):
    parts = ip.split(".")
    value = 0
    for p in parts:
        value = (value << 8) | int(p)
    return value


def int_to_ip(value):
    return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))


def prefixlen_to_mask(prefixlen):
    if prefixlen == 0:
        return 0
    return (0xFFFFFFFF << (32 - prefixlen)) & 0xFFFFFFFF


class Route:
    def __init__(self, network, netmask, peer, localpref, selfOrigin, ASPath, origin):
        self.network = network
        self.netmask = netmask
        self.peer = peer
        self.localpref = localpref
        self.selfOrigin = selfOrigin
        self.ASPath = ASPath
        self.origin = origin

    def to_dict(self):
        return {
            "network": self.network,
            "netmask": self.netmask,
            "peer": self.peer,
            "localpref": self.localpref,
            "selfOrigin": self.selfOrigin,
            "ASPath": self.ASPath,
            "origin": self.origin,
        }

    def attrs_match(self, other):
        return (
            self.peer == other.peer
            and self.localpref == other.localpref
            and self.selfOrigin == other.selfOrigin
            and self.ASPath == other.ASPath
            and self.origin == other.origin
        )


class RoutingTable:
    def __init__(self):
        self.routes = []
        self._update_cache = []
        self._withdraw_cache = []

    def add_route(self, updateMsg):
        msg = updateMsg["msg"]
        peer = updateMsg["src"]
        route = Route(
            network=msg["network"],
            netmask=msg["netmask"],
            peer=peer,
            localpref=msg["localpref"],
            selfOrigin=msg["selfOrigin"],
            ASPath=list(msg["ASPath"]),
            origin=msg["origin"],
        )
        self._update_cache.append(updateMsg)
        self.routes.append(route)
        self._aggregate()

    def remove_route(self, withdrawMsg):
        self._withdraw_cache.append(withdrawMsg)
        self._rebuild()

    def lookup(self, dst_ip):
        dst_int = ip_to_int(dst_ip)
        best = []
        best_prefix_len = -1

        for route in self.routes:
            net_int = ip_to_int(route.network)
            mask_int = ip_to_int(route.netmask)
            prefix_len = bin(mask_int).count("1")

            if (dst_int & mask_int) == net_int:
                if prefix_len > best_prefix_len:
                    best_prefix_len = prefix_len
                    best = [route]
                elif prefix_len == best_prefix_len:
                    best.append(route)

        if not best:
            return None
        if len(best) == 1:
            return best[0]
        return self._break_tie(best)

    def dump(self):
        return [r.to_dict() for r in self.routes]

    def _rebuild(self):
        withdrawn = set()
        for w in self._withdraw_cache:
            peer = w["src"]
            for entry in w["msg"]:
                withdrawn.add((peer, entry["network"], entry["netmask"]))

        self.routes = []
        for update in self._update_cache:
            peer = update["src"]
            msg = update["msg"]
            key = (peer, msg["network"], msg["netmask"])
            if key not in withdrawn:
                self.routes.append(
                    Route(
                        network=msg["network"],
                        netmask=msg["netmask"],
                        peer=peer,
                        localpref=msg["localpref"],
                        selfOrigin=msg["selfOrigin"],
                        ASPath=list(msg["ASPath"]),
                        origin=msg["origin"],
                    )
                )
        self._aggregate()

    def _aggregate(self):
        changed = True
        while changed:
            changed = False
            new_routes = []
            used = set()

            for i in range(len(self.routes)):
                if i in used:
                    continue
                r1 = self.routes[i]
                merged = False

                for j in range(i + 1, len(self.routes)):
                    if j in used:
                        continue
                    agg = self._try_aggregate(r1, self.routes[j])
                    if agg is not None:
                        new_routes.append(agg)
                        used.add(i)
                        used.add(j)
                        merged = True
                        changed = True
                        break

                if not merged:
                    new_routes.append(r1)

            self.routes = new_routes

    def _try_aggregate(self, r1, r2):
        if not r1.attrs_match(r2):
            return None

        n1 = ip_to_int(r1.network)
        n2 = ip_to_int(r2.network)
        m1 = ip_to_int(r1.netmask)
        m2 = ip_to_int(r2.netmask)

        if m1 != m2:
            return None

        prefix_len = bin(m1).count("1")
        if prefix_len == 0:
            return None

        diff_bit = 1 << (32 - prefix_len)
        if n1 ^ n2 != diff_bit:
            return None

        parent = min(n1, n2)
        new_mask = prefixlen_to_mask(prefix_len - 1)

        return Route(
            network=int_to_ip(parent),
            netmask=int_to_ip(new_mask),
            peer=r1.peer,
            localpref=r1.localpref,
            selfOrigin=r1.selfOrigin,
            ASPath=r1.ASPath,
            origin=r1.origin,
        )

    def _break_tie(self, candidates):
        max_lp = max(r.localpref for r in candidates)
        candidates = [r for r in candidates if r.localpref == max_lp]
        if len(candidates) == 1:
            return candidates[0]

        self_true = [r for r in candidates if r.selfOrigin]
        if self_true:
            candidates = self_true
        if len(candidates) == 1:
            return candidates[0]

        min_len = min(len(r.ASPath) for r in candidates)
        candidates = [r for r in candidates if len(r.ASPath) == min_len]
        if len(candidates) == 1:
            return candidates[0]

        origin_rank = {"IGP": 0, "EGP": 1, "UNK": 2}
        best_orig = min(origin_rank.get(r.origin, 2) for r in candidates)
        candidates = [
            r for r in candidates if origin_rank.get(r.origin, 2) == best_orig
        ]
        if len(candidates) == 1:
            return candidates[0]

        candidates.sort(key=lambda r: ip_to_int(r.peer))
        return candidates[0]
