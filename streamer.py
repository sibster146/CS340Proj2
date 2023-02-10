# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct
import heapq
import concurrent.futures
import time

"""
-1 = ACK
-2 = FIN
"""

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
        self.seqNum = 0
        self.closed = False
        self.ack = False
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        executor.submit(self.listener)

    def send(self, data_bytes: bytes) -> None:
        """Note that data_bytes can be larger than one packet."""
        # Your code goes here!  The code below should be changed!
        
        lenBytes = len(data_bytes)
        
        for i in range(0,lenBytes,1468):
            self.ack = False
            packetHeader = struct.pack("!i",self.seqNum)
            self.socket.sendto(packetHeader + data_bytes[i:i+1468], (self.dst_ip, self.dst_port))
            start = time.perf_counter()
            while not self.ack:
                if time.perf_counter()-start>=0.25 and not self.ack:
                    self.ack = False
                    self.socket.sendto(packetHeader + data_bytes[i:i+1468], (self.dst_ip, self.dst_port))
                    start = time.perf_counter()
                print(time.perf_counter()-start)

                #time.sleep(0.01)
            self.seqNum+=1


    """
    THERE ARE TWO WAYS TO SEND ACKs
    1. SEND THE ACKS in the RECV FUNCTION- tried this it didnt work too well
    2. SEND THE ACKS IN THE LISTENER FUNCTION- trying this one now

    """


    def recv(self) -> bytes:
        """Blocks (waits) if no data is ready to be read from the connection."""
        # your code goes here!  The code below should be changed!
        # this sample code just calls the recvfrom method on the LossySocket

        #print(f"At this call of recv, we have recieved {len(self.buffer)} packets.")
        ackHeader = struct.pack("!i",-1)
        while 1:
            if self.ackNum in self.buffer:
                val = self.buffer[self.ackNum]
                del self.buffer[self.ackNum]
                #self.socket.sendto(ackHeader + val, (self.dst_ip, self.dst_port) )

                self.ackNum+=1
                return val
                """
            else:
                packet,addr = self.socket.recvfrom()
                num = struct.unpack('!i',packet[:4])[0]
                data = packet[4:]
                #print(f"This is acknum: {self.ackNum}")
                #print(f"This is the packet: {num},{data},{type(data)}")
                self.buffer[num] = data
                """
                
    def listener(self):
        ackHeader = struct.pack("!i",-1)
        while not self.closed: # a later hint will explain self.closed
            try:
                packet, addr = self.socket.recvfrom()
                num = struct.unpack('!i',packet[:4])[0]
                data = packet[4:]
                
                if num==-1:

                    self.ack = True
                else:
                    data = packet[4:]
                    print(data)
                    self.socket.sendto(ackHeader + data, (self.dst_ip, self.dst_port))
                    self.buffer[num] = data

      # store the data in the receive buffer
      # ...
            except Exception as e:
                print("listener died!")
                print(e)



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        # while not self.ack:
        #     time.sleep(0.01)

        # finHeader = struct.pack("!i",-2)
        # self.socket.sendto( + data, (self.dst_ip, self.dst_port))


        self.closed = True
        self.socket.stoprecv()
        pass
