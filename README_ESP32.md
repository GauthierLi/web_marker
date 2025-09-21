# ESP32 Temperature & Humidity Sensor with Dual Server Support

This ESP32 project implements both WebSocket and HTTP servers to provide real-time temperature and humidity data from a DHT22 sensor.

## Features

- **Dual Server Architecture**: HTTP server (port 80) and WebSocket server (port 81) running concurrently
- **Real-time Data**: WebSocket provides live sensor updates every 2 seconds
- **Protocol Buffer Support**: Data transmitted via Protocol Buffers over WebSocket
- **Web Interface**: Beautiful HTML page with real-time charts and data visualization
- **JSON API**: RESTful HTTP endpoint for sensor data
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Hardware Requirements

- ESP32 development board
- DHT22 (AM2302) temperature and humidity sensor
- 10kΩ pull-up resistor
- Breadboard and jumper wires

## Wiring

```
DHT22    ESP32
------   -----
VCC   -> 3.3V
GND   -> GND
DATA  -> GPIO 4 (with 10kΩ pull-up resistor to 3.3V)
```

## Arduino IDE Setup

### Required Libraries

Install these libraries through the Arduino IDE Library Manager:

1. **WiFi** (built-in with ESP32)
2. **WebSockets** by Markus Sattler
   - Install via: Sketch > Include Library > Manage Libraries > Search "WebSockets"
3. **DHT sensor library** by Adafruit
   - Install via: Sketch > Include Library > Manage Libraries > Search "DHT sensor"
4. **ArduinoJson** by Benoit Blanchon
   - Install via: Sketch > Include Library > Manage Libraries > Search "ArduinoJson"
5. **Nanopb** for Protocol Buffers
   - Download from: https://github.com/nanopb/nanopb/releases
   - Extract and copy the 'nanopb' folder to your Arduino libraries directory

### ESP32 Board Setup

1. Install ESP32 board support:
   - File > Preferences
   - Add this URL to "Additional Board Manager URLs": 
     `https://dl.espressif.com/dl/package_esp32_index.json`
   - Tools > Board > Board Manager > Search "ESP32" > Install

2. Select your ESP32 board:
   - Tools > Board > ESP32 Arduino > Select your specific ESP32 board

## Configuration

1. Open `esp32_sensor_server.ino` in Arduino IDE
2. Update WiFi credentials:
   ```cpp
   const char* ssid = "YOUR_WIFI_SSID";
   const char* password = "YOUR_WIFI_PASSWORD";
   ```
3. Verify pin configuration (default: DHT22 on GPIO 4):
   ```cpp
   #define DHT_PIN 4
   ```

## Usage

1. Upload the code to your ESP32
2. Open Serial Monitor (115200 baud) to see connection status
3. Note the IP address displayed in Serial Monitor
4. Open a web browser and navigate to: `http://[ESP32_IP_ADDRESS]`
5. View real-time temperature and humidity data

## API Endpoints

### HTTP Server (Port 80)

- **GET /** - Main dashboard page with real-time data visualization
- **GET /sensor** - JSON API endpoint returning current sensor data

Example response:
```json
{
  "temperature": 23.5,
  "humidity": 65.2,
  "timestamp": 123456789,
  "device_id": "ESP32_DHT_001"
}
```

### WebSocket Server (Port 81)

- **ws://[ESP32_IP]:81** - Real-time data stream
- Sends sensor data every 2 seconds in both JSON and Protocol Buffer formats
- Automatically reconnects on connection loss

## Protocol Buffer Schema

The sensor data is encoded using Protocol Buffers for efficient transmission:

```protobuf
message SensorData {
  double temperature = 1;    // Temperature in Celsius
  double humidity = 2;       // Humidity percentage (0-100)
  uint64 timestamp = 3;      // Unix timestamp in milliseconds
  string device_id = 4;      // Device identifier
}
```

## Web Interface Features

- **Real-time Charts**: Live temperature and humidity graphs
- **Connection Status**: Visual indicator of WebSocket connection
- **Responsive Design**: Works on all devices
- **Auto-reconnect**: Automatically reconnects if connection is lost
- **Fallback**: HTTP polling as backup if WebSocket fails

## Troubleshooting

### Common Issues

1. **WiFi Connection Failed**:
   - Verify SSID and password
   - Check signal strength
   - Ensure 2.4GHz network (ESP32 doesn't support 5GHz)

2. **Sensor Reading NaN**:
   - Check wiring connections
   - Verify pull-up resistor (10kΩ)
   - Try different GPIO pin

3. **WebSocket Connection Issues**:
   - Check firewall settings
   - Verify ESP32 IP address
   - Try accessing HTTP endpoint first

4. **Library Compilation Errors**:
   - Ensure all required libraries are installed
   - Check library versions for compatibility
   - Update ESP32 board package

### Serial Monitor Output

Normal operation should show:
```
=== ESP32 Dual Server - Temperature & Humidity Monitor ===
Connecting to WiFi.....
WiFi connected! IP address: 192.168.1.100
mDNS responder started
HTTP server started on port 80
WebSocket server started on port 81
Setup complete!
HTTP Server: http://192.168.1.100
WebSocket Server: ws://192.168.1.100:81
Temperature: 23.5°C, Humidity: 65.2%
```

## Performance

- **Update Rate**: 2 seconds (configurable)
- **Concurrent Connections**: Supports multiple WebSocket clients
- **Memory Usage**: ~200KB RAM (typical)
- **CPU Usage**: Very low (< 5%)

## Customization

### Change Update Interval

Modify the `sensorInterval` variable:
```cpp
const unsigned long sensorInterval = 1000; // 1 second updates
```

### Different Sensor

Replace DHT22 with other sensors by modifying the `readSensorData()` function.

### Custom Device ID

Change the device identifier:
```cpp
String deviceId = "YOUR_CUSTOM_ID";
```

## File Structure

```
esp32_sensor_server/
├── esp32_sensor_server.ino    # Main Arduino sketch
├── sensor_data.proto          # Protocol Buffer definition
├── sensor_data.pb.h           # Generated Protocol Buffer header
├── sensor_data.pb.c           # Generated Protocol Buffer source
└── README_ESP32.md            # This documentation
```