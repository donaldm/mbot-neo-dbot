# MBot Neo DBot
AI program for MBot Neo using OpenAI Whisper and Mycroft Adapt-Intent Parser.

## Installation

### makeblock modifications to support Bluetooth programming mode
Currently the makeblock Python package is hard coded to look for a specific device identifier when doing it's auto connect. 

In my local virtualenv I have modified the makeblock module as follows:

boards/base/__init__.py:

```python
    def connect(self,device=None,channel=None):
        if type(device)==int:
            channel = device
        if channel is None:
            channels = mlink.list()
            if len(channels)>0:
                self._dev = mlink.connect(channels[0])
                return self.__setup(self._type,self._dev)
        else:
            self._device = mlink.connect(channel)
            return self.__setup(self._type,self._dev)
        if device is None:
            print([a[2] for a in SerialPort.list()])

            ports = [port[0] for port in SerialPort.list() if port[2] != 'n/a' and port[2].find('CNCA1')>0 ]
            print(ports)
            if len(ports)>0:
                device = SerialPort(ports[0])
                self._dev = device
                return self.__setup(self._type,self._dev)
```

The main change was putting CNCA1 instead of the port[2].find('1A86:7523')>0 that was there before. 

CNCA1 is the identifier of my port from com0com.

In the future I will work to make this change included in the DBot code and not have to modify an open source pacage directly.

## Usage

### Running the software

```
docker-compose up -d
```

### Discovering MBot Neo BLE device information

Using the Python ble-serial package we can run a ble-scan:

```
Started general BLE scan

AC:0B:FB:21:A9:4A (RSSI=-62): Makeblock_LEAC0BFB21A94A

Finished general BLE scan

```

Then once we have the identifier (In this case AC:0B:FB:21:A9:4A) we can run a deep scan.

I use the following command to connect to the MBot Neo using ble-serial:

```
ble-serial -d AC:0B:FB:21:A9:4A  -w 0000ffe3-0000-1000-8000-00805f9b34fb -r 0000ffe2-0000-1000-8000-00805f9b34fb -v
```
