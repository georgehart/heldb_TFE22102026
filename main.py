'''
=========================================

  WEBSERVER DHT11 METRIC DATA

  author  : Georges Hart
  Date    : November 2024
  Release : 0.3

  Description : 
  A minimalist code for setting up a web server that publishes data from a DHT11 sensor.
  This data will be scraped by a time-series database such as Prometheus.
  This data will in turn be processed by Grafana, which will display a dashboard.               

=========================================
'''
# ----- IMPORT Libraries -----
import network
import socket
import time
import machine
from machine import Pin
import dht

'''
Wi-Fi credentials see secrets.py or declare here
ssid = 'xxxxx'
password = 'xxxxx'
'''

# ----- Built In LED -----
led = machine.Pin("LED", machine.Pin.OUT)
led.off()

# ----- MAC Adress -----
wlan = network.WLAN(network.STA_IF)  # Or network.WLAN(network.AP_IF)
try:
    mac_address = wlan.config('mac')
    # Format the MAC address (hexadecimal with colons)
    formatted_mac = ':'.join(['{:02x}'.format(x) for x in mac_address])
    print("MAC Address:", formatted_mac)

except OSError as e:
    print(f"Error getting MAC address: {e}")
    print("Make sure the Pico W is properly connected and the wireless interface is active.")
    # You might want to handle this error more gracefully in a real application.
    # For example, you could provide a default MAC address or retry.

try:
    import secrets
    ssid = secrets.ssid
    password = secrets.password
except ImportError:
    print("WiFi credentials are kept in secrets.py, please add them there!")
    raise  # Or handle the error differently

# ----- DHT sensor pin -----
dht_pin = Pin(16, Pin.IN)  # Example: GPIO 16
sensor = dht.DHT11(dht_pin)  # Or dht.DHT22(dht_pin) if using DHT22

# ----- Connect to Wi-Fi ------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)
while not wlan.isconnected():
    time.sleep(1)
print('Wi-Fi connected')
led.on()
ip_address = wlan.ifconfig()[0]
print('IP Address:', ip_address)

# ----- Create socket -----
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
s = socket.socket()
s.bind(addr)
s.listen(1)
print('Listening on', addr)

# ----- Read DHT sensor data with error handling -----
def read_dht_data():
    try:
        sensor.measure()
        temp = (sensor.temperature())-20
        hum = sensor.humidity()
        return temp, hum
    except OSError as e:
        print("DHT sensor error:", e)
        return None, None

# ----- Main loop -----
while True:
    
    if not wlan.isconnected():  # Check Wi-Fi connection at the start of each loop
        print("Wi-Fi disconnected. Reconnecting...")
        led.off()  # Indicate disconnection
        wlan.connect(ssid, password)
        while not wlan.isconnected():
            time.sleep(1)
        print("Wi-Fi reconnected.")
        led.on()  # Indicate connection
        ip_address = wlan.ifconfig()[0]  # Get the IP address after reconnecting
        print('IP Address:', ip_address)
        
    try:
        conn, addr = s.accept()
        print('Client connected from', addr)
        request = conn.recv(1024).decode('utf-8')
        print("Request:", request)

        temp, hum = read_dht_data()
        current_time = int(time.time())  # Unix epoch timestamp

        # ----- Prometheus format output -----
        if temp is None and hum is None:
            prometheus_output = f"""

# HELP temperature Temperature from DHT11 sensor
# TYPE temperature gauge

temperature{{sensor="dht11",location="GH_trial"}} NaN {current_time}


# HELP Humidity Temperature from DHT11 sensor
# TYPE Humidity gauge
humidity{{sensor="dht11",location="GH_trial"}} NaN {current_time}
"""
        else:
            prometheus_output = f"""
# HELP temperature Temperature from DHT11 sensor
# TYPE temperature gauge
temperature{{sensor="dht11",location="GH_trial"}} {temp:.1f} {current_time}

# HELP Humidity Temperature from DHT11 sensor
# TYPE Humidity gauge
humidity{{sensor="dht11",location="GH_trial"}} {hum:.1f} {current_time}

"""
        conn.send('HTTP/1.0 200 OK\r\nContent-type: text/plain\r\n\r\n')
        conn.send(prometheus_output.encode())
        conn.close()
        print('Client disconnected')

    except OSError as e:
        print("Socket error:", e)
        continue
    except Exception as e:
        print("General error:", e)
        continue