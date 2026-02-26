import socket, json

MY_ROUTER_PORT = 53580

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
msg = {
    "src": "1.2.3.2",
    "dst": "1.2.3.1",
    "type": "update",
    "msg": {
        "network": "1.2.3.0",
        "netmask": "255.255.255.0",
        "localpref": 100,
        "ASPath": [4],
        "origin": "IGP",
        "selfOrigin": True,
    },
}
sock.sendto(json.dumps(msg).encode(), ("127.0.0.1", MY_ROUTER_PORT))
