import socket

def int_to_bytepair(n: int) -> bytes:
    return n.to_bytes(2, byteorder='little', signed=False)

def bytepair_to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='little', signed=False)

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
    def __init__(self, data: bytes, id: int, ack: int):
        self.data = data
        self.id = id
        self.ack = ack
    
    def serialize(self) -> bytes:
        return int_to_bytepair(self.id) + int_to_bytepair(self.ack) + self.data
    
    @classmethod
    def load(cls, data: bytes):
        id = bytepair_to_int(data[:2])
        ack = bytepair_to_int(data[2:4])
        return Packet(data[4:], id, ack)
    

class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, *args, **kwargs):
        self.buffer_size = 4096
        self.used_ids = set()
        self.sent_packets = []
        self.id = 1
        self.ack = 0
        super().__init__(*args, **kwargs)

    def send(self, data: bytes):
        packet = Packet(data, self.id, self.ack)
        self.sent_packets.append(packet)
        self.id += 1
        return self.sendto(packet.serialize())

    def recv(self, n: int):
        while True:
            data = self.recvfrom(self.buffer_size)
            packet = Packet.load(data)
            if packet.id not in self.used_ids:
                self.used_ids.add(packet.id)
                if self.id - packet.ack != 1:
                    print("!!!! PACKET LOSS DETECTED !!!!", packet.id, self.ack)
                else:
                    self.ack = packet.id

                return packet.data

