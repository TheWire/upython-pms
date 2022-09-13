# Micropython Library for Plantower PMS A003/7003/5003 air quality monitor

Micropython libary for Plantower PMS A003/7003/5003 air quality monitor.
Tested on PMSA003 with Raspberry Pi Pico should work with other sensor microcontroller combinations.

## Example Usage
### Single Read
```
from pms import PMS

#example uart comfig for raspberry Pi Pico
uart = UART(
    0,
    baudrate=9600,
    bits=8,
    parity=None,
    stop=1,
    timeout=2000,
    tx=Pin(16),
    rx=Pin(17)
)

sensor = PMS(uart)
data = sensor.read()
print(data["PM2.5"])
```
### Read Continuously
```
def callback(data):
    print(data)

subscription = sensor.subscribe(callback)

uasyncio.create_task(sensor.start())
```

#### remove from subscription when done
```
sensor.unsubscribe(subscription)
```

### Change Mode
#### Passive Mode
True for single read False for continuous.
```
sensor.passive_mode(True)
```
#### Sleep Mode
Lowers power usage shuts down fan.
```
sensor.sleep_mode(True)
```

### Data
python dict values available:

- PM1.0
- PM2.5
- PM10
- PM1.0_UAE
- PM2.5_UAE
- PM10_UAE
- 0.3um
- 0.5um
- 1.0um
- 2.5um
- 5.0um
- 10um

PM values in g/m3.

PM values calibrated - standard particle calibration fluid 1.

UAE stands for under atmospheric environment (no calibration?).

Other values particle size in um in 0.1L of air.