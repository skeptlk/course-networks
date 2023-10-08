import socket
from threading import Timer
from typing import List, Set


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
    def __init__(self, name, *args, **kwargs):
        self.buffer_size = 4096
        self.used_ids: Set[int] = set()
        self.sent_packets: List[Packet] = []
        self.id = 1
        self.ack = 0

        self.timer = Timer(0.4, self.send_ack)
        self.timer.start()

        self.name = name

        super().__init__(*args, **kwargs)

    def __del__(self):
        self.timer.cancel()

    def send_ack(self):
        self.send(b'')
        print(self.name, "timer!", self.id, self.ack)
        self.timer = Timer(0.4, self.send_ack)
        self.timer.start()

    def send(self, data: bytes):
        packet = Packet(data, self.id, self.ack)
        self.sent_packets.append(packet)
        print(self.name, "Sending packet, id=", self.id)
        self.id += 1
        return self.sendto(packet.serialize())
    
    def send_lost(self, start_id):
        packets_to_send = filter(lambda x: x.id >= start_id, self.sent_packets)

        for packet in packets_to_send:        
            print(self.name, "Sending lost, id=", packet.id)
            self.sendto(packet.serialize())

    def recv(self, n: int):
        while True:
            data = self.recvfrom(self.buffer_size)
            packet = Packet.load(data)
            if packet.id not in self.used_ids:
                self.used_ids.add(packet.id)
                if self.id - packet.ack != 1:
                    print(self.name, "PACKET LOSS DETECTED! id=", packet.id, " ack=", self.ack)
                    self.send_lost(packet.ack + 1)
                else:
                    if len(packet.data) == 0:
                        print(self.name, "received empty ack! ")
                        self.send_lost(packet.ack + 1)
                    else:
                        print(self.name, "received in-order packet: id=", packet.id, " ack=", self.ack)
                        self.ack = packet.id

                if len(packet.data) == 0:
                    continue

                return packet.data

