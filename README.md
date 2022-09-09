# Micropython Library for Plantower PMS A003/7003/5003 air quality monitor

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

#remove from subscription when done
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