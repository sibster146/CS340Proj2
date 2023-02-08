# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct
import heapq


class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """Default values listen on all network interfaces, chooses a random source port,
           and does not introduce any simulated packet loss."""
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.buffer = {}
        self.ackNum = 0

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        lenBytes = len(data_bytes)
        # for i in range(0,lenBytes,1472):
        #     self.socket.sendto(data_bytes[i:i+1472], (self.dst_ip, self.dst_port))





        seqNum = 0
        for i in range(0,lenBytes,1468):
            packetHeader = struct.pack("!I",seqNum)
            self.socket.sendto(packetHeader + data_bytes[i:i+1468], (self.dst_ip, self.dst_port))
            #time.sleep(1)
            seqNum+=1

            # packet = struct.pack("!i4s",self.seqNum, data_bytes[i:i+4])
            # self.socket.sendto(packet,(self.dst_ip, self.dst_port))
            # time.sleep(1)
            # self.seqNum+=1
            #self.socket.sendto(data_bytes[i:i+1472], (self.dst_ip, self.dst_port))
        # for now I'm just sending the raw application-level data in one UDP payload


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        # this sample code just calls the recvfrom method on the LossySocket

        # packet,addr = self.socket.recvfrom()
        # print(f"this is the packet: {type(packet)}")
        # return packet



        while 1:
            packet,addr = self.socket.recvfrom()
            num = struct.unpack('!I',packet[:4])[0]
            data = packet[4:]
            print(f"THis is acknum: {self.ackNum}")
            print(f"this is the packet: {num},{data},{type(data)}")
            self.buffer[num] = data
            if self.ackNum in self.buffer:
                val = self.buffer[self.ackNum]
                self.ackNum+=1
                return val



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        pass
