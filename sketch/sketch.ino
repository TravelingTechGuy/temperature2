#include <Arduino_RouterBridge.h>
#include <tuple>
#include "Arduino_LED_Matrix.h"
#include "Arduino_Modulino.h"

Arduino_LED_Matrix matrix;
ModulinoThermo thermo;

String deviceUnits = "F";

struct SensorResult {
  float celsius;
  float fahrenheit;
  float humidity;
};

void setDeviceUnits(String units) {
  deviceUnits = units;
}

SensorResult getSensorData() {
  float celsius = thermo.getTemperature();
  float fahrenheit = (celsius * 9 / 5) + 32;
  float humidity = thermo.getHumidity();
  return {celsius, fahrenheit, humidity};
}

// Package and return the 3 variables safely as a tuple - for RPC MessagePack
std::tuple<float, float, float> getSensorDataForPython() {
  SensorResult data = getSensorData();
  // Return a tuple of the 3 floats
  return std::make_tuple(data.celsius, data.fahrenheit, data.humidity);
}

void writeToMatrix(String str) {
  matrix.beginText(0, 1, 0xFFFFFF); // (x, y, color)
  matrix.textFont(Font_5x7);
  matrix.textScrollSpeed(200); // Speed in milliseconds
  matrix.print(str);
  matrix.endText(SCROLL_LEFT); // Scroll direction
}

void setup() {
  // Uno Q bridge typically uses 115200
  Serial.begin(115200);
  Modulino.begin();
  thermo.begin();
  matrix.begin();
  Bridge.begin();
  Bridge.provide("set_device_units", setDeviceUnits);
  Bridge.provide_safe("get_sensor_data", getSensorDataForPython);  //safe to prevent thread issue
}

void loop() {
  //get sensor results and write them to the matrix, and the log every 2 seconds
  SensorResult data = getSensorData();

  String tempStr = deviceUnits == "C" ? String((int)data.celsius) + "C" : String((int)data.fahrenheit) + "F";
  writeToMatrix(tempStr);

  // Print to the STM32 Microcontroller Log
  Serial.print("Temperature: ");
  Serial.print(tempStr);
  Serial.print("\tHumidity: ");
  Serial.println(String(data.humidity));

  delay(2000);
}
