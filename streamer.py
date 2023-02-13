# do not import anything else from loss_socket besides LossyUDP
from lossy_socket import LossyUDP
# do not import anything else from socket except INADDR_ANY
from socket import INADDR_ANY
import struct
import heapq
import concurrent.futures
import threading
import time
import hashlib
import sys

"""
-1 = ACK
-2 = FIN
"""

class Streamer:
    def __init__(self, dst_ip, dst_port,
                 src_ip=INADDR_ANY, src_port=0):
        """
        Default values listen on all network interfaces, chooses a random source port,
        and does not introduce any simulated packet loss.
        """
        self.socket = LossyUDP()
        self.socket.bind((src_ip, src_port))
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.buffer = {}
        self.ackNum = 0
        self.seqNum = 0
        self.closed = False

        self.ack = False
        self.future = None
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.start_listener()

    def start_listener(self):
        self.future = self.executor.submit(self.listener)

    def stop_listener(self):
        if self.future is not None:
            self.future.cancel()
            self.executor.shutdown()

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
                if time.perf_counter()-start>=.5 and not self.ack:
                    self.socket.sendto(packetHeader + data_bytes[i:i+1468], (self.dst_ip, self.dst_port))
                    start = time.perf_counter()

            self.seqNum+=1
        self.ack = False




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
                self.buffer[self.ackNum]
                del self.buffer[self.ackNum]
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
        lastSeqNum = []
        while not self.closed: # a later hint will explain self.closed
            try:
                packet, addr = self.socket.recvfrom()
                num = struct.unpack('!i',packet[:4])[0]

                if num == -1:
                    self.ack = True
                if num==-2:
                    print("its getting here")
                    self.ack = True
                    #self.stop_listener()
                    #return

                elif num >= 0:
                    data = packet[4:]

                    if (lastSeqNum and lastSeqNum[-1]!=num-1) and (num not in lastSeqNum):
                        continue

                    lastSeqNum.append(num)
                    self.buffer[num] = data
                    self.socket.sendto(ackHeader + data, (self.dst_ip, self.dst_port))


                  

      # store the data in the receive buffer
            except Exception as e:
                print("listener died!")
                print(e)


    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        finHeader = struct.pack("!i",-2)

        self.socket.sendto( finHeader, (self.dst_ip, self.dst_port))
        start = time.perf_counter()
        while not self.ack:
            if time.perf_counter()-start>=.5 and not self.ack:
                #self.ack = False
                self.socket.sendto(finHeader, (self.dst_ip, self.dst_port))
                start = time.perf_counter()
                #time.sleep(0.01)

        print("waiting two secs")
        time.sleep(2)

        self.closed = True
        self.socket.stoprecv()
        self.stop_listener()
        return



    def add_hash(self, p: bytes) -> bytes: 
        #This function should be called around the packet as it is being sent through the socket
        #Packet should be inputted as a (max length - 16) byte long bytestream.
        #Packet will be returned as a max length packet ready to be sent
        #Total max sending size is 1472:
        #   4 bytes packet header + 1468 packet data
        #Now it will need to be:
        #   16 bytes packet hash + 4 bytes packet header + 1452 bytes packet data


        self.hash = hashlib.md5()
        self.hash.update(p)

        return_packet = self.hash.digest() + p

        if len(return_packet) != 1472:
            print("Something is wrong with the packet length, stopping")
            sys.exit(-1)
        
        if len(self.hash.digest) != 16 or self.hash.digest_size != 16:
            print("Something is wrong with the hash itself")
            sys.exit(-1)

        return return_packet

    def hash_matches(self, p:bytes):
        #this function should be called on a returned packet.
        #Upon recieve, call this function!
        #It will return None if the packet was corrupted, 
        # or it will return the packet, of length 1456
        self.hash = hashlib.md5()
        self.hash.update(p[16:])

        if self.hash.digest() != p[:16]:
            return None
        else:
            return p[16:]


        #Plan for part 4 implementation
        # In the send portion, alter the packet's data portion to be shorter
        # Then wrap the packet in the above hash_packet function
        
        # In the recv part, as soon as the packet is recieved and unpacket, call has_matches on it.
        # new_p = hash_matches(recvd_packet), 
        # if new_p == None: corruption occured, ask for resend
        # else : use new_p as the packet going forward
