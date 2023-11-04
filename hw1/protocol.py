from typing import List, Set
import threading
import socket
import time
import sys
from collections import OrderedDict

def int_to_bytes(n: int, size = 4) -> bytes:
    return n.to_bytes(size, byteorder='little', signed=False)

def bytes_to_int(b: bytes) -> int:
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
    def __init__(self, data: bytes, id: int, ack: int, split = 0):
        self.data = data
        self.id = id
        self.ack = ack
        self.split = split

    def __eq__(self, other):
        return self.id == other.id

    def __hash__(self):
        return hash(('id', self.id))

    def serialize(self) -> bytes:
        return \
            int_to_bytes(self.id) + \
            int_to_bytes(self.ack) + \
            int_to_bytes(self.split, 1) + \
            self.data
    
    def is_empty(self) -> bool:
        return len(self.data) == 0
    
    @classmethod
    def load(cls, data: bytes):
        id = bytes_to_int(data[:4])
        ack = bytes_to_int(data[4:8])
        split = bytes_to_int(data[8:9])
        return Packet(data[9:], id, ack, split)

class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, name, *args, **kwargs):
        self.buffer_size = 4096
        self.used_ids: Set[int] = set()
        self.sent_packets: List[Packet] = []

        self.send_queue: List[Packet] = []
        self.recv_queue: List[Packet] = []
        
        self.id = 1
        self.ack = 0

        self.last_ack = None

        self.TICK = 0.0000001

        self.time = 0
        self.last_sent_time = 0

        self.name = name

        self.halt = False

        self.verbose = True

        self.thread = threading.Thread(target=self.working_thread)
        self.thread.start()

        super().__init__(*args, **kwargs)

    def __del__(self):
        self.halt = True

    def working_thread(self):
        while not self.halt:
            try:
                data = self.recvfrom(32767 + 9)
                packet = Packet.load(data)
                if packet.id not in self.used_ids:
                    if packet.id - self.ack != 1:
                        self.log("Packet loss detected id=", packet.id,  "ack=", self.ack)
                        self.send_acknowledgement() 
                    else:
                        if packet.is_empty():
                            self.log("empty ack =", packet.ack)
                            self.send_lost_packets(packet.ack)
                        else:
                            self.log("packet in order: p.id=", packet.id, "p.ack=", packet.ack)
                            self.used_ids.add(packet.id)
                            self.recv_queue.append(packet)
                            self.ack = packet.id
                else:
                    self.log("Got duplicate! id=", packet.id, packet.ack)
                self.last_ack = packet.ack
            except Exception:
                pass

            while len(self.send_queue) > 0:
                packet = self.send_queue.pop()
                packet.ack = self.ack
                self.sendto(packet.serialize())
                self.sent_packets.append(packet)
                self.last_sent_time = self.time

            self.time += self.TICK

            if self.time - self.last_sent_time >= 100 * self.TICK and len(self.sent_packets) > 0:
                last = self.sent_packets[-1]
                if (last.id != self.last_ack or self.last_ack is None) and not last.is_empty():
                    self.send_queue.append(last)
                    self.log("adding last id =", last.id)

            if self.time - self.last_sent_time >= 50 * self.TICK:
                if len(self.send_queue) == 0:
                    self.send_acknowledgement()

            time.sleep(self.TICK)

    def send_acknowledgement(self):
        self.log("Sending empty ack=", self.ack, "id=", self.id)
        packet = Packet(b'', self.id, self.ack)
        self.send_queue.append(packet)
        return 9

    def send_lost_packets(self, ack: int):
        id_to_send = sys.maxsize if len(self.send_queue) == 0 else self.send_queue[0].id
        
        # if lost packets were already queued, do not add them again
        lost_packets = list(filter(lambda x: x.id > ack and x.id < id_to_send and not x.is_empty(), self.sent_packets))
        lost_packets = list(OrderedDict.fromkeys(lost_packets))
        
        self.log("Queue before adding lost: ", [p.id for p in self.send_queue])
        for p in lost_packets:
            p.ack = self.ack
        self.send_queue = lost_packets + self.send_queue

        self.log("Queue after: ", [p.id for p in self.send_queue])
    
    def log(self, *values: object):
        if self.verbose:
            print(self.name, *values)

    def send(self, data: bytes):
        # split here
        split_size = 32767 
        size = len(data)
        splits = size // split_size + 1

        for i in range(splits):
            split = 0 if splits == 1 else 2 if (i == splits - 1) else 1
            packet_data = data[i * split_size : (i + 1) * split_size]
            packet = Packet(packet_data, self.id, self.ack, split)
            self.log("Sending packet, id=", self.id, "len=", len(packet_data), "Split=", split)
            self.send_queue.insert(0, packet)
            self.id += 1
            
        return size + 9

    def recv(self, n: int):
        while len(self.recv_queue) == 0 or self.recv_queue[-1].split == 1:
            time.sleep(self.TICK)
        # join split sequence together
        if self.recv_queue[-1].split == 0:
            packet = self.recv_queue.pop()
            # self.log("Recv!", packet.id)
            return packet.data
        data = b''
        while len(self.recv_queue) > 0 and self.recv_queue[-1].split != 0:
            packet = self.recv_queue.pop()
            data = packet.data + data
        # self.log("Sending data: ", len(data))
        return data


