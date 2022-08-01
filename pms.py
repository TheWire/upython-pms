from machine import UART, Pin
from time import sleep
from ucollections import OrderedDict

DATA_OFFSETS = [
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
        
    def readAll(self):
        
        self.__flush_buffer()
        raw_data = bytes()
        while len(raw_data) < 64:
            while self.__pms_uart.any() > 0:
                raw_data += self.__pms_uart.read(1)
        frames = self.__find_frames(raw_data)
        return self.__average_frame(frames)
    
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
            
    def test_find_frames(self):
        data = b'BM\x00\x1c\x00\x02\x00\x03\x00\x04\x00\x02\x00\x03\x00\x04\x02\x5E\x00\xc0\x00\x0f\x00\x02\x00\x00\x00\x00\x97\x00\x02\x85BM\x00\x1c'
        frames = self.__find_frames(data)
        
    def __average_frame(self, frames):
        average_frame = dict()
        for field in DATA_OFFSETS:
            average = 0
            for frame in frames:
                average += frame[field]
            average_frame[field] = average / len(frames)
            
        return average_frame
             
    def __parse_frame(self, raw_data):
        frame_size = self.__read_2_bytes(raw_data[2], raw_data[3])
        if frame_size > len(raw_data):
            print("frame size too small")
            return None, len(raw_data)
        frame = dict()
        sensor_data_end = DATA_OFFSET_START + frame_size - SENSOR_DATA_OFFSET_END # minus 2 for version + error data
        sum_of_bytes = START_HIGH + START_LOW + raw_data[3]
        for i in range(DATA_OFFSET_START, sensor_data_end, 2):
            data_index = (i - DATA_OFFSET_START) // 2
            frame[DATA_OFFSETS[data_index]] = self.__read_2_bytes(raw_data[i], raw_data[i+1])
            sum_of_bytes += raw_data[i] + raw_data[i+1]
        
        position = DATA_OFFSET_START + frame_size
        version = raw_data[position-4]
        error = raw_data[position-3]
        sum_of_bytes += version + error
        check_sum = self.__read_2_bytes(raw_data[position-2], raw_data[position-1])
        if sum_of_bytes == check_sum: return frame, frame_size
        print("check sum failed")
        return None, frame_size
            
            
    def __read_2_bytes(self, byte_high, byte_low):
        return (byte_high << 8) + byte_low
            