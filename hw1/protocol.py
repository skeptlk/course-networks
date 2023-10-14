from typing import List, Set
import threading
import socket
import time


def int_to_bytepair(n: int) -> bytes:
    return n.to_bytes(2, byteorder='little', signed=False)

def bytepair_to_int(b: bytes) -> int:
    return int.from_bytes(b, byteorder='little', signed=False)

class UDPBasedProtocol:
    def __init__(self, *, local_addr, remote_addr):
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.udp_socket.setblocking(0)
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

        self.send_queue: List[Packet] = []
        self.recv_queue: List[Packet] = []
        
        self.id = 1
        self.ack = 0

        self.TICK = 0.00001

        self.time = 0
        self.last_sent_time = 0

        self.name = name

        self.halt = False

        self.thread = threading.Thread(target=self.working_thread)
        self.thread.start()

        super().__init__(*args, **kwargs)

    def __del__(self):
        self.halt = True

    def working_thread(self):
        while not self.halt:
            try:
                data = self.recvfrom(self.buffer_size)
                packet = Packet.load(data)
                if packet.id not in self.used_ids:
                    # detect packet loss here: 
                    if self.id - packet.ack != 1:
                        # if lost packets were already queued, no not add them again
                        lost_packets = list(filter(lambda x: x.id > packet.ack, self.sent_packets))
                        for p in lost_packets:
                            p.ack = self.ack
                        self.send_queue = lost_packets + self.send_queue
                    else:
                        self.used_ids.add(packet.id)
                        self.recv_queue.append(packet)
                        self.ack = packet.id
            except:
                pass

            if len(self.send_queue) > 0:
                packet = self.send_queue.pop()
                packet.ack = self.ack
                self.sendto(packet.serialize())
                self.sent_packets.append(packet)
                self.last_sent_time = self.time

            self.time += self.TICK

            if self.time - self.last_sent_time >= 100 * self.TICK:
                self.send_queue.append(self.sent_packets[len(self.sent_packets) - 1])

            time.sleep(self.TICK)

    def send(self, data: bytes):
        packet = Packet(data, self.id, self.ack)
        self.id += 1
        self.send_queue.append(packet)

        print(self.name, "Sending packet, id=", self.id)
        return len(data) + 4

    def recv(self, n: int):
        while len(self.recv_queue) == 0:
            time.sleep(self.TICK)
        packet = self.recv_queue.pop()
        print(self.name, "Recv!", packet.id)
        return packet.data

