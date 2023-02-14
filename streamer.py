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
        self.ackNum = 5
        self.seqNum = 5
        self.closed = False
        self.batchAcks = 0
        self.allhere = False

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

    def serial_send(self, data_bytes: bytes) -> None:
        
        lenBytes = len(data_bytes)
        
        bodyLength = 1452 # The length of the packet body

        for i in range(0,lenBytes,bodyLength): # Iterate through the data to be sent

            self.ack = False # Reset Ack flag for this packet

            packetHeader = struct.pack("!i", self.seqNum) # Encode packet sequence number as bytes

            packet = self.add_hash(packetHeader + data_bytes[i:i+bodyLength]) # Concatenate packetHeader and data body, generate and attach checksum

            print(f"Sending packet with contents: {packet}")

            self.socket.sendto(packet, (self.dst_ip, self.dst_port)) # Send complete packet

            start = time.perf_counter() # Start a timer

            while not self.ack: # While we're waiting to receive an Ack packet

                if time.perf_counter()-start>=.5 and not self.ack: # If it's been 0.5 seconds and we haven't recv'd an Ack packet

                    #TODO Add hashing to ack packets
                    
                    self.socket.sendto(packet, (self.dst_ip, self.dst_port)) # Resend the last packet

                    start = time.perf_counter() # Start timing again            

            self.seqNum+=1 # This packet was successfully sent, prep to send next packet

        self.ack = False # Reset Ack flag to false for next iteration



    def serial_listener(self):

        ackHeader = struct.pack("!i",-1) # Encode Ack header as bytes

        lastSeqNum = []
        while not self.closed: # a later hint will explain self.closed
            try:
                packet, addr = self.socket.recvfrom() # Receive packet from socket

                packet = self.hash_matches(packet) # Check received data against received checksum

                if packet is None: # If the checksum doesn't match, drop and let the sender resend
                    print("packet checksum didn't match, ignoring the corrupted packet")
                    continue

                num = struct.unpack('!i',packet[:4])[0]

                if num == -1:
                    self.ack = True

                if num==-2:
                    print("Received FIN packet")

                    # Send a FIN ACK
                    ack = self.add_hash(ackHeader)
                    self.socket.sendto(ack, (self.dst_ip, self.dst_port))


                elif num >= 0:
                    data = packet[4:]

                    if (lastSeqNum and lastSeqNum[-1]!=num-1) and (num not in lastSeqNum):
                        continue

                    lastSeqNum.append(num)
                    self.buffer[num] = data
                    packet = self.add_hash(ackHeader + data)
                    self.socket.sendto(packet, (self.dst_ip, self.dst_port))


      # store the data in the receive buffer
            except Exception as e:
                print("listener died!")
                print(e)








    


    def ssend(self, data_bytes: bytes, sequence) -> None:

        print(f"sending sequence {sequence}")
        
        packetHeader = struct.pack("!i", sequence) # Encode packet sequence number as bytes

        packet = self.add_hash(packetHeader + data_bytes) # Concatenate packetHeader and data body, generate and attach checksum

        self.socket.sendto(packet, (self.dst_ip, self.dst_port)) # Send complete packet


    def send(self, data_bytes: bytes) -> None:

        #start a pool of threads

        len_bytes = len(data_bytes)

        bodyLength = 1452

        # for loop
        for i in range(0, len_bytes, bodyLength * 5):

            self.batchAcks = 0

            threads = []

            for j in range(i, (i + (bodyLength * 5)), bodyLength):
                
                t = threading.Thread(target = self.ssend, args = (data_bytes[j:j+bodyLength], j+5))
                t.start()
                threads.append(t)

            start = time.perf_counter() # Start a timer

            for t in threads:
                t.join()


            # wait for all 5 acks
            #if not recvd, decrement i again
            #send all 5 again
            

            while self.batchAcks != 5: # While we're waiting to receive an Ack packet

                if time.perf_counter()-start>=.5 and self.batchAcks != 5: # If it's been 0.5 seconds and we haven't recv'd an Ack packet

                    i -= (bodyLength * 5)

                    break  




        
         
            

        # have each thread send a chuck of the data

        # check all the acks we got, and loop to the top from the lowest

    def listener(self):

        

        lastSeqNum = []


        while not self.closed: # a later hint will explain self.closed
            try:
                packet, addr = self.socket.recvfrom() # Receive packet from socket

                packet = self.hash_matches(packet) # Check received data against received checksum

                if packet is None: # If the checksum doesn't match, drop and let the sender resend
                    print("packet checksum didn't match, ignoring the corrupted packet")
                    continue

                num = struct.unpack('!i',packet[:4])[0]

                if num == -1:
                    self.ack = True


                if num==-2:
                    print("Received FIN packet")

                    # Send a FIN ACK
                    ack = self.add_hash(struct.pack("!i",-1))
                    self.socket.sendto(ack, (self.dst_ip, self.dst_port))


                elif num >= 0:
                    data = packet[4:]
                    print(f"THIS IS NUM: {num}")

                    if num not in self.buffer:
                        self.buffer[num] = data

                        print(f"THIS IS THE BUFFER: {self.buffer}")
                        

                        #all ack numbers are the sequence number *-1 
                        ackHeader = self.add_hash(struct.pack("!i", -1 * num))
                        self.socket.sendto(ackHeader, (self.dst_ip, self.dst_port))


                        if len(self.buffer) == 5:
                            print("BUFFER FULL")
                            self.ackNum = 5
                            self.allhere = True
                         
                            while len(self.buffer) != 0: pass
                            self.allhere = False
                            self.ackNum = 5

                elif num < 0:
                    self.batchAcks += 1





                    # if (lastSeqNum and lastSeqNum[-1]!=num-1) and (num not in lastSeqNum):
                    #     continue

                    # lastSeqNum.append(num)
                    # self.buffer[num] = data
                    # packet = self.add_hash(ackHeader + data)
                    # self.socket.sendto(packet, (self.dst_ip, self.dst_port))


      # store the data in the receive buffer
            except Exception as e:
                print("listener died!")
                print(e)


    def recv(self) -> bytes:

        ackHeader = struct.pack("!i", -1) # Encode Ack header as bytes
        stack = []
        latest = None 


        while 1:

            if self.allhere and self.buffer and self.ackNum < 7265:

                val = self.buffer[self.ackNum]

                del self.buffer[self.ackNum]
                print(f"LOOP BUFFER: {self.buffer}")

                self.ackNum+=1452

                if not val:
                    continue

                if not latest



                #self.socket.sendto(ackHeader + val, (self.dst_ip, self.dst_port) )
                return val
            


    



    def close(self) -> None:
        """Cleans up. It should block (wait) until the Streamer is done with all
           the necessary ACKs and retransmissions"""
        # your code goes here, especially after you add ACKs and retransmissions.
        # while not self.ack:
        #     time.sleep(0.01)

        print("closing")

        # wait for all acked

        fin = self.add_hash(struct.pack("!i",-2)) # make fin packet

        self.socket.sendto(fin, (self.dst_ip, self.dst_port)) # send fin packet

        start = time.perf_counter() # start timer

        while not self.ack: # while waiting for the fin ack

            if time.perf_counter()-start>=.5 and not self.ack:

                self.socket.sendto(fin, (self.dst_ip, self.dst_port))
                start = time.perf_counter()

        print("fin acked")
        print("waiting two secs") # give the other time to close themselves (and stay open to respond to them)
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

        print(f"Add_hash result digest is {self.hash.digest()} + {p}")

        return_packet = self.hash.digest() + p

        print(f"Meaning return_packet is  {return_packet}")

        if len(return_packet) < 16:
            print("Something is wrong with the packet length, stopping")
            print(return_packet.decode())
            print(len(return_packet))
            sys.exit(-1)
        
        if self.hash.digest_size != 16:
            print("Something is wrong with the hash itself")
            sys.exit(-1)

        return return_packet

    def hash_matches(self, p:bytes):
        #this function should be called on a returned packet.
        #Upon receive, call this function!
        #It will return None if the packet was corrupted, 
        # or it will return the packet, of length 1456
        self.hash = hashlib.md5()

        print(f"Checking match on packet {p}")


        self.hash.update(p[16:])

        print(f"Calculated hash is {self.hash.digest()}")
        print(f"Reference hash is: {p[:16]}")

        if self.hash.digest() != p[:16]:
            print("Hash doesn't match")
            return None
        else:
            print("Hash matches")
            return p[16:]


        #Plan for part 4 implementation
        # In the send portion, alter the packet's data portion to be shorter
        # Then wrap the packet in the above hash_packet function
        
        # In the recv part, as soon as the packet is received and unpacket, call has_matches on it.
        # new_p = hash_matches(recvd_packet), 
        # if new_p == None: corruption occured, ask for resend
        # else : use new_p as the packet going forward
