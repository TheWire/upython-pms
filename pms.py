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
SLEEP_STATE_CMD = 0xE4
PASSIVE_STATE_CMD = 0xE1
READ_PASSIVE_CMD = 0xE2
SLEEP_STATE = 0x00
WAKEUP_STATE = 0x01
PASSIVE_STATE = 0x00
ACTIVE_STATE = 0x01


   
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
                    frame, new_idx = self.__parse_data_frame(new_idx, raw_data)
                    if frame is not None:
                        data.push(frame)
                    else:
                        found = False
                raw_data = raw_data[new_idx:]
            if len(raw_data) >= 288: raw_data = bytes() #incase somehow no frames found for a long time
            
    def __single_read(self):
        raw_data = bytes()
        raw_data = self.__read2(raw_data)
        print(raw_data)
            
    def __read(self, raw_data):
        while len(raw_data) < 32:
            while self.__pms_uart.any() > 0:
                raw_data += self.__pms_uart.read(1)
        return raw_data
    
    def __read2(self, raw_data):
        i = 0
        while len(raw_data) < 32 and i < 10:
            while self.__pms_uart.any() > 0:
                raw_data += self.__pms_uart.read(1)
            i += 1
        return raw_data
    
    def passive_mode(self, state):
        if state:
            self.__send_command(PASSIVE_STATE_CMD, PASSIVE_STATE)
        else:
            self.__send_command(PASSIVE_STATE_CMD, ACTIVE_STATE)
        sleep(5)
        self.__single_read()
    
    def sleep_mode(self, state):
        if state:
            self.__send_command(SLEEP_STATE_CMD, SLEEP_STATE)
        else:
            self.__send_command(SLEEP_STATE_CMD, WAKEUP_STATE)
        sleep(5)
        self.__single_read()
    
    def __send_command(self, command, data):
        self.__flush_buffer()
        cmd = [START_HIGH, START_LOW, command, data >> 8, data & 0xFF]
        check_sum = sum(cmd)
        cmd.append(check_sum >> 8)
        cmd.append(check_sum & 0xFF)
        print(cmd)
        self.__write(bytes(cmd))

    def __write(self, data):
        self.__pms_uart.write(data)
                          
    def __find_frame(self, raw_data):
        for i in range(len(raw_data) - 1):
            if raw_data[i] == START_HIGH and raw_data[i+1] == START_LOW:
                return True, i
        return False, 0
    
    def __flush_buffer(self):
        self.__pms_uart.read(288)
            
    def __find_frames(self, raw_data):
        frames = list()
        i = 0
        while i < len(raw_data):
            if len(raw_data) - i < MIN_FRAME_SIZE:
                return frames
            if raw_data[i] == START_HIGH and raw_data[i+1] == START_LOW:
                frame, newI = self.__parse_data_frame(raw_data[i:])
                if frame is not None: frames.append(frame)
            i += 1
            
    def __read_2_bytes(self, byte_high, byte_low):
        return (byte_high << 8) + byte_low
        
    def __average_frame(self, frames):
        average_frame = dict()
        for field in DATA_OFFSETS:
            average = 0
            for frame in frames:
                average += frame[field]
            average_frame[field] = average / len(frames)
            
        return average_frame
    
    #return frame_size, position after size bytes and check_sum
    def __parse_frame_start(self, start_idx, raw_data):
        if len(raw_data) < MIN_FRAME_SIZE: return 0, 0, start_idx
        #start bytes
        pos = start_idx
        if raw_data[pos] != START_HIGH or raw_data[pos+1] != START_LOW:
            return 0, 0, pos
    
        sum_of_bytes = raw_data[pos] + raw_data[pos+1]
        pos += 2
        
        #size bytes
        frame_size = self.__read_2_bytes(raw_data[pos], raw_data[pos+1])
        sum_of_bytes += raw_data[pos] + raw_data[pos+1]
        pos += 2
        
        return frame_size, pos, sum_of_bytes
             
    def __parse_data_frame(self, start_idx, raw_data):
        frame_size, pos, sum_of_bytes = self.__parse_frame_start(start_idx, raw_data)
        if frame_size == 0: return None, pos
        if frame_size + 4 > len(raw_data): #4: 2 start bytes + 2 check bytes
            return None, start_idx
        #data bytes
        frame = dict()
        sensor_data_end = pos + frame_size - 4 #4 = minus 2 size bytes, version and error bytes

        j = 0
        for i in range(pos, sensor_data_end, 2):
            frame[DATA[j]] = self.__read_2_bytes(raw_data[i], raw_data[i+1])
            sum_of_bytes += raw_data[i] + raw_data[i+1]
            j += 1

        pos = sensor_data_end
        
        #version + error
        version = raw_data[pos]
        error = raw_data[pos+1]
        sum_of_bytes += version + error

        pos += 2
        
        #checksum
        is_valid, pos = self.__parse_check_sum(pos, sum_of_bytes, raw_data)
        if is_valid: return frame, pos
        None, pos
            
    
    #return if frame is valid and new position
    def __parse_check_sum(self, pos, sum_of_bytes, raw_data):
        #checksum
        check_sum = self.__read_2_bytes(raw_data[pos], raw_data[pos+1])
        pos += 2
        if sum_of_bytes == check_sum:
            return True, pos
        else:
            print("check sum failed")
            return False, pos
    
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
            