from machine import UART, Pin
from time import sleep
from ucollections import deque
import uasyncio

DATA = [
    "PM1.0",
    "PM2.5",
    "PM10",
    "PM1.0_UAE",
    "PM2.5_UAE",
    "PM10_UAE",
    "0.3um",
    "0.5um",
    "1.0um",
    "2.5um",
    "5.0um",
    "10um",
]

MIN_FRAME_SIZE = 6
START_HIGH = 0x42
START_LOW = 0x4D
DATA_OFFSET_START = 4
SENSOR_DATA_OFFSET_END = 4

   
class PMS:
    
    def __init__(self, uart):
        self.__pms_uart = uart
        
        
    async def start(self, buffer_size=10):
        self.__flush_buffer()
        self.__pms_data = PMS_Data(buffer_size)
        await self.__stream_read(self.__pms_data)
    
    def any(self):
        return len(self.__pms_data)
    
    def read(self):
        return self.__pms_data.pop()
        
    async def __stream_read(self, data):
        raw_data = bytes()
        while True:
            await uasyncio.sleep(1.0)
            raw_data = self.__read(raw_data)
            found = True
            while found:
                found, new_idx = self.__find_frame(raw_data)
                if found:
                    frame, new_idx = self.__parse_frame(new_idx, raw_data)
                    if frame is not None:
                        data.push(frame)
                    else:
                        found = False
                raw_data = raw_data[new_idx:]
            if len(raw_data) >= 288: raw_data = bytes() #incase somehow no frames found for a long time
            
    def __read(self, raw_data):
        while len(raw_data) < 32:
            while self.__pms_uart.any() > 0:
                raw_data += self.__pms_uart.read(1)
        return raw_data

    
                          
    def __find_frame(self, raw_data):
        for i in range(len(raw_data) - 1):
            if raw_data[i] == START_HIGH and raw_data[i+1] == START_LOW:
                return True, i
        return False, 0
    
    def __flush_buffer(self):
        while self.__pms_uart.any() > 0:
            self.__pms_uart.read(288)
            
    def __find_frames(self, raw_data):
        frames = list()
        i = 0
        while i < len(raw_data):
            if len(raw_data) - i < MIN_FRAME_SIZE:
                return frames
            if raw_data[i] == START_HIGH and raw_data[i+1] == START_LOW:
                frame, newI = self.__parse_frame(raw_data[i:])
                if frame is not None: frames.append(frame)
            i += 1
        
    def __average_frame(self, frames):
        average_frame = dict()
        for field in DATA_OFFSETS:
            average = 0
            for frame in frames:
                average += frame[field]
            average_frame[field] = average / len(frames)
            
        return average_frame
             
    def __parse_frame(self, start_idx, raw_data):
        if len(raw_data) < MIN_FRAME_SIZE: return None, start_idx
        #start bytes
        pos = start_idx
        sum_of_bytes = raw_data[pos] + raw_data[pos+1]
        pos += 2
        
        #size bytes
        frame_size = self.__read_2_bytes(raw_data[pos], raw_data[pos+1])
        sum_of_bytes += raw_data[pos] + raw_data[pos+1]
        
        if frame_size + 4 > len(raw_data): #4: 2 start bytes + 2 check bytes
            return None, start_idx

        #data bytes
        frame = dict()
        sensor_data_end = pos + frame_size - 2 # minus 2 for version + error data
        pos += 2 # advance pos for size bytes
        j = 0
        for i in range(pos, sensor_data_end, 2):
            frame[DATA[j]] = self.__read_2_bytes(raw_data[i], raw_data[i+1])
            sum_of_bytes += raw_data[i] + raw_data[i+1]
            j += 1

        pos = sensor_data_end
        
        #version error
        version = raw_data[pos]
        error = raw_data[pos+1]
        sum_of_bytes += version + error

        pos += 2
        
        #checksum
        check_sum = self.__read_2_bytes(raw_data[pos], raw_data[pos+1])
        pos += 2
        if sum_of_bytes == check_sum:
            return frame, pos
        else:
            print("check sum failed")
            return None, pos
            
            
    def __read_2_bytes(self, byte_high, byte_low):
        return (byte_high << 8) + byte_low
    
class PMS_Data:
    
    def __init__(self, buffer_size=10):
        self.__data_stream = deque((), buffer_size)
        
    def push(self, data):
        self.__data_stream.append(data)
        
        
    def pop(self):
        data = self.__data_stream.popleft()
        return data
    
    def __len__(self):
        length = len(self.__data_stream)
        return length
            