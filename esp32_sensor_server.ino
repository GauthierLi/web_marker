#include <WiFi.h>
#include <WebSocketsServer.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <pb_encode.h>
#include <pb_decode.h>
#include "sensor_data.pb.h"

// WiFi credentials - Update these with your network details
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Pin definitions
#define DHT_PIN 4
#define DHT_TYPE DHT22

// Server instances
WebServer httpServer(80);           // HTTP server on port 80
WebSocketsServer webSocketServer(81); // WebSocket server on port 81

// Sensor instance
DHT dht(DHT_PIN, DHT_TYPE);

// Global variables
unsigned long lastSensorRead = 0;
const unsigned long sensorInterval = 2000; // Read sensor every 2 seconds
float currentTemperature = 0.0;
float currentHumidity = 0.0;
String deviceId = "ESP32_DHT_001";

// Function prototypes
void setupWiFi();
void setupServers();
void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length);
void handleRoot();
void handleNotFound();
void readSensorData();
void sendSensorDataWebSocket();
bool encodeSensorData(float temp, float hum, uint8_t* buffer, size_t* size);

void setup() {
  Serial.begin(115200);
  Serial.println("\n=== ESP32 Dual Server - Temperature & Humidity Monitor ===");
  
  // Initialize DHT sensor
  dht.begin();
  
  // Setup WiFi connection
  setupWiFi();
  
  // Setup HTTP and WebSocket servers
  setupServers();
  
  Serial.println("Setup complete!");
  Serial.print("HTTP Server: http://");
  Serial.println(WiFi.localIP());
  Serial.print("WebSocket Server: ws://");
  Serial.print(WiFi.localIP());
  Serial.println(":81");
}

void loop() {
  // Handle HTTP requests
  httpServer.handleClient();
  
  // Handle WebSocket events
  webSocketServer.loop();
  
  // Read sensor data periodically
  if (millis() - lastSensorRead >= sensorInterval) {
    readSensorData();
    sendSensorDataWebSocket();
    lastSensorRead = millis();
  }
  
  delay(10); // Small delay to prevent watchdog reset
}

void setupWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println();
  Serial.print("WiFi connected! IP address: ");
  Serial.println(WiFi.localIP());
  
  // Setup mDNS
  if (MDNS.begin("esp32-sensor")) {
    Serial.println("mDNS responder started");
  }
}

void setupServers() {
  // Setup HTTP server routes
  httpServer.on("/", handleRoot);
  httpServer.on("/sensor", HTTP_GET, []() {
    DynamicJsonDocument doc(1024);
    doc["temperature"] = currentTemperature;
    doc["humidity"] = currentHumidity;
    doc["timestamp"] = millis();
    doc["device_id"] = deviceId;
    
    String response;
    serializeJson(doc, response);
    
    httpServer.send(200, "application/json", response);
  });
  
  httpServer.onNotFound(handleNotFound);
  httpServer.begin();
  Serial.println("HTTP server started on port 80");
  
  // Setup WebSocket server
  webSocketServer.begin();
  webSocketServer.onEvent(handleWebSocketEvent);
  Serial.println("WebSocket server started on port 81");
}

void handleWebSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.printf("WebSocket client %u disconnected\n", num);
      break;
      
    case WStype_CONNECTED: {
      IPAddress ip = webSocketServer.remoteIP(num);
      Serial.printf("WebSocket client %u connected from %s\n", num, ip.toString().c_str());
      
      // Send current sensor data to newly connected client
      sendSensorDataWebSocket();
      break;
    }
    
    case WStype_TEXT:
      Serial.printf("WebSocket received text from client %u: %s\n", num, payload);
      // Echo back the message
      webSocketServer.sendTXT(num, "Server received: " + String((char*)payload));
      break;
      
    case WStype_BIN: {
      Serial.printf("WebSocket received binary data from client %u, length: %u\n", num, length);
      // Handle binary data if needed
      break;
    }
    
    default:
      break;
  }
}

void handleRoot() {
  String html = R"====(
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Temperature & Humidity Monitor</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .sensor-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .sensor-card {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            transition: transform 0.3s ease;
        }
        .sensor-card:hover {
            transform: translateY(-5px);
        }
        .sensor-value {
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }
        .sensor-label {
            font-size: 1.1em;
            opacity: 0.9;
        }
        .sensor-unit {
            font-size: 0.8em;
            opacity: 0.7;
        }
        .status {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .connected { background-color: #4CAF50; }
        .disconnected { background-color: #f44336; }
        .chart-container {
            background: rgba(255, 255, 255, 0.2);
            border-radius: 15px;
            padding: 20px;
            margin-top: 20px;
            height: 300px;
        }
        .temperature { color: #ff6b6b; }
        .humidity { color: #4ecdc4; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌡️ ESP32 Sensor Monitor</h1>
            <p>Real-time Temperature & Humidity Data</p>
        </div>
        
        <div class="sensor-grid">
            <div class="sensor-card temperature">
                <div class="sensor-label">Temperature</div>
                <div class="sensor-value" id="temperature">--.-</div>
                <div class="sensor-unit">°C</div>
            </div>
            
            <div class="sensor-card humidity">
                <div class="sensor-label">Humidity</div>
                <div class="sensor-value" id="humidity">--.-</div>
                <div class="sensor-unit">%</div>
            </div>
        </div>
        
        <div class="status">
            <span class="status-indicator" id="status-indicator"></span>
            <span id="status-text">Connecting...</span>
            <div style="margin-top: 10px;">
                <small>Last Update: <span id="last-update">Never</span></small>
            </div>
        </div>
        
        <div class="chart-container">
            <canvas id="chart" width="400" height="200"></canvas>
        </div>
    </div>

    <script>
        // WebSocket connection
        let ws;
        let temperatureData = [];
        let humidityData = [];
        let timeLabels = [];
        const maxDataPoints = 20;
        
        // DOM elements
        const tempElement = document.getElementById('temperature');
        const humidityElement = document.getElementById('humidity');
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        const lastUpdateElement = document.getElementById('last-update');
        const canvas = document.getElementById('chart');
        const ctx = canvas.getContext('2d');
        
        function connectWebSocket() {
            const wsUrl = `ws://${window.location.hostname}:81`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = function() {
                console.log('WebSocket connected');
                statusIndicator.className = 'status-indicator connected';
                statusText.textContent = 'Connected';
            };
            
            ws.onmessage = function(event) {
                try {
                    const data = JSON.parse(event.data);
                    updateSensorDisplay(data);
                } catch (e) {
                    console.log('Received non-JSON message:', event.data);
                }
            };
            
            ws.onclose = function() {
                console.log('WebSocket disconnected');
                statusIndicator.className = 'status-indicator disconnected';
                statusText.textContent = 'Disconnected - Reconnecting...';
                
                // Attempt to reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
            
            ws.onerror = function(error) {
                console.error('WebSocket error:', error);
                statusIndicator.className = 'status-indicator disconnected';
                statusText.textContent = 'Connection Error';
            };
        }
        
        function updateSensorDisplay(data) {
            tempElement.textContent = data.temperature.toFixed(1);
            humidityElement.textContent = data.humidity.toFixed(1);
            lastUpdateElement.textContent = new Date().toLocaleTimeString();
            
            // Add data to charts
            addDataPoint(data.temperature, data.humidity);
            drawChart();
        }
        
        function addDataPoint(temp, humidity) {
            const now = new Date().toLocaleTimeString();
            
            temperatureData.push(temp);
            humidityData.push(humidity);
            timeLabels.push(now);
            
            // Keep only the last maxDataPoints
            if (temperatureData.length > maxDataPoints) {
                temperatureData.shift();
                humidityData.shift();
                timeLabels.shift();
            }
        }
        
        function drawChart() {
            const width = canvas.width;
            const height = canvas.height;
            const padding = 40;
            
            // Clear canvas
            ctx.clearRect(0, 0, width, height);
            
            if (temperatureData.length < 2) return;
            
            // Find min/max values
            const tempMin = Math.min(...temperatureData) - 2;
            const tempMax = Math.max(...temperatureData) + 2;
            const humMin = Math.min(...humidityData) - 5;
            const humMax = Math.max(...humidityData) + 5;
            
            // Draw grid lines
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.2)';
            ctx.lineWidth = 1;
            for (let i = 0; i <= 5; i++) {
                const y = padding + (height - 2 * padding) * i / 5;
                ctx.beginPath();
                ctx.moveTo(padding, y);
                ctx.lineTo(width - padding, y);
                ctx.stroke();
            }
            
            // Draw temperature line
            ctx.strokeStyle = '#ff6b6b';
            ctx.lineWidth = 2;
            ctx.beginPath();
            for (let i = 0; i < temperatureData.length; i++) {
                const x = padding + (width - 2 * padding) * i / (temperatureData.length - 1);
                const y = height - padding - (height - 2 * padding) * (temperatureData[i] - tempMin) / (tempMax - tempMin);
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            
            // Draw humidity line
            ctx.strokeStyle = '#4ecdc4';
            ctx.lineWidth = 2;
            ctx.beginPath();
            for (let i = 0; i < humidityData.length; i++) {
                const x = padding + (width - 2 * padding) * i / (humidityData.length - 1);
                const y = height - padding - (height - 2 * padding) * (humidityData[i] - humMin) / (humMax - humMin);
                
                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            }
            ctx.stroke();
            
            // Draw legend
            ctx.fillStyle = 'white';
            ctx.font = '14px Arial';
            ctx.fillText('Temperature', padding, 20);
            ctx.fillStyle = '#ff6b6b';
            ctx.fillRect(padding - 20, 10, 15, 3);
            
            ctx.fillStyle = 'white';
            ctx.fillText('Humidity', padding + 120, 20);
            ctx.fillStyle = '#4ecdc4';
            ctx.fillRect(padding + 100, 10, 15, 3);
        }
        
        // Start connection
        connectWebSocket();
        
        // Fallback: fetch data via HTTP if WebSocket fails
        function fetchDataHTTP() {
            fetch('/sensor')
                .then(response => response.json())
                .then(data => {
                    if (ws.readyState !== WebSocket.OPEN) {
                        updateSensorDisplay(data);
                    }
                })
                .catch(error => console.error('HTTP fetch error:', error));
        }
        
        // Fallback polling every 5 seconds
        setInterval(fetchDataHTTP, 5000);
    </script>
</body>
</html>
)====";
  
  httpServer.send(200, "text/html", html);
}

void handleNotFound() {
  httpServer.send(404, "text/plain", "404 - Not Found");
}

void readSensorData() {
  float temp = dht.readTemperature();
  float hum = dht.readHumidity();
  
  if (isnan(temp) || isnan(hum)) {
    Serial.println("Failed to read from DHT sensor!");
    return;
  }
  
  currentTemperature = temp;
  currentHumidity = hum;
  
  Serial.printf("Temperature: %.1f°C, Humidity: %.1f%%\n", temp, hum);
}

void sendSensorDataWebSocket() {
  if (webSocketServer.connectedClients() == 0) {
    return; // No clients connected
  }
  
  // Create JSON data for WebSocket transmission
  DynamicJsonDocument doc(1024);
  doc["temperature"] = currentTemperature;
  doc["humidity"] = currentHumidity;
  doc["timestamp"] = millis();
  doc["device_id"] = deviceId;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  // Send to all connected WebSocket clients
  webSocketServer.broadcastTXT(jsonString);
  
  // Also try to send Protocol Buffer encoded data
  uint8_t buffer[256];
  size_t size;
  if (encodeSensorData(currentTemperature, currentHumidity, buffer, &size)) {
    webSocketServer.broadcastBIN(buffer, size);
  }
}

bool encodeSensorData(float temp, float hum, uint8_t* buffer, size_t* size) {
  // Create Protocol Buffer message
  sensor_SensorData sensorData = sensor_SensorData_init_zero;
  
  sensorData.temperature = temp;
  sensorData.humidity = hum;
  sensorData.timestamp = millis();
  strcpy(sensorData.device_id, deviceId.c_str());
  
  // Encode the message
  pb_ostream_t stream = pb_ostream_from_buffer(buffer, 256);
  bool status = pb_encode(&stream, sensor_SensorData_fields, &sensorData);
  
  if (status) {
    *size = stream.bytes_written;
    Serial.printf("Protocol Buffer encoded: %d bytes\n", *size);
  } else {
    Serial.println("Failed to encode Protocol Buffer message");
  }
  
  return status;
}