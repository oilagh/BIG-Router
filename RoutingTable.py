import json
from datetime import datetime

class RoutingTable:
    def __init__(self):
        self.history = []

        self.routes = []

    
    def __handle_handshake(self, msg):
        pass

    def __handle_update(self, msg):
        pass

    def __handle_withdraw(self, msg):
        pass

    def __handle_data(self, msg):
        pass

    
    def add_message(self, srcif, msg):
        jsonDict = json.loads(msg)
        
        self.history.append({
            'timestamp': datetime.now().isoformat(),
            'srcif': srcif,
            'msg': msg
        })
    
    def add_route(self, network, netmask, next_hop, relation, localpref=100, as_path=[], origin='IGP', self_origin=False):
        self.routes.append({
            'network':     network,
            'netmask':     netmask,
            'next_hop':    next_hop,
            'relation':    relation,
            'localpref':   localpref,
            'as_path':     as_path,
            'origin':      origin,
            'self_origin': self_origin
        })
    
    def dump(self):
        return self.routes