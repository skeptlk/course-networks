import socket


class UDPBasedProtocol:
    def __init__(self, *, local_addr, remote_addr):
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.remote_addr = remote_addr
        self.udp_socket.bind(local_addr)

    def sendto(self, data):
        return self.udp_socket.sendto(data, self.remote_addr)

    def recvfrom(self, n):
        msg, addr = self.udp_socket.recvfrom(n)
        return msg
    
class Packet:
    def __init__(self, data: bytes, id: int):
        self.data = data
        self.id = id
    
    def serialize(self) -> bytes:
        return self.id.to_bytes(2, byteorder='little', signed=False) + self.data
    
    @classmethod
    def load(cls, data: bytes):
        id = int.from_bytes(data[:2], byteorder='little', signed=False)
        return Packet(data[2:], id)
    

class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, *args, **kwargs):
        self.buffer_size = 4096
        self.used_ids = set()
        self.id = 0
        super().__init__(*args, **kwargs)

    def send(self, data: bytes):
        packet = Packet(data, self.id)
        self.id += 1
        return self.sendto(packet.serialize())

    def recv(self, n: int):
        while True:
            data = self.recvfrom(n + 2)
            packet = Packet.load(data)
            if packet.id not in self.used_ids:
                self.used_ids.add(packet.id)
                return packet.data[:n]


