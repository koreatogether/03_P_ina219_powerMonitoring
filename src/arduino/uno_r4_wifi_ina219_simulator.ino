/*
 * INA219 Power Monitoring System - Arduino UNO R4 WiFi Simulator
 * JSON 포맷 기반 시리얼 통신 + Mock 데이터 생성
 * 
 * 기능:
 * - INA219 센서 시뮬레이션 (실제 하드웨어 없이도 동작)
 * - JSON 포맷 데이터 전송
 * - 시퀀스 번호 기반 데이터 무결성
 * - 명령 수신 및 ACK/NACK 응답
 * - 다양한 시나리오 테스트 지원
 */

#include <ArduinoJson.h>
#include <WiFiS3.h>  // UNO R4 WiFi 전용

// 시뮬레이션 모드 설정
enum SimulationMode {
  NORMAL,      // 정상 동작 시뮬레이션
  LOAD_SPIKE,  // 부하 급증 시뮬레이션
  VOLTAGE_DROP, // 전압 강하 시뮬레이션
  NOISE,       // 노이즈 포함 데이터
  ERROR_TEST   // 에러 상황 테스트
};

// 전역 변수
SimulationMode currentMode = NORMAL;
unsigned long measurementInterval = 1000; // 1초 기본값
unsigned long lastMeasurement = 0;
unsigned long sequenceNumber = 0;
bool sensorStatus = true;

// 시뮬레이션 파라미터
struct SimulationParams {
  float baseVoltage = 5.0;    // 기준 전압 (V)
  float baseCurrent = 0.2;    // 기준 전류 (A)
  float voltageNoise = 0.05;  // 전압 노이즈 범위
  float currentNoise = 0.02;  // 전류 노이즈 범위
  unsigned long cycleTime = 30000; // 시뮬레이션 사이클 시간 (30초)
};

SimulationParams simParams;

void setup() {
  // 시리얼 통신 초기화
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  // 시작 메시지
  sendStatusMessage("INA219 Power Monitoring Simulator - UNO R4 WiFi");
  sendStatusMessage("JSON Protocol v1.0");
  sendStatusMessage("Simulation Mode: NORMAL");
  
  // 랜덤 시드 초기화
  randomSeed(analogRead(0));
  
  sendStatusMessage("Simulator ready - Starting measurements...");
}

void loop() {
  unsigned long currentTime = millis();
  
  // 측정 간격 확인
  if (currentTime - lastMeasurement >= measurementInterval) {
    sendMeasurementData();
    lastMeasurement = currentTime;
  }
  
  // 시리얼 명령 처리
  handleSerialCommands();
  
  // 시뮬레이션 모드 자동 변경 (데모용)
  updateSimulationMode(currentTime);
  
  delay(10);
}

void sendMeasurementData() {
  // JSON 문서 생성 (충분한 크기로 할당)
  StaticJsonDocument<200> doc;
  
  // 시뮬레이션 데이터 생성
  float voltage = generateVoltage();
  float current = generateCurrent();
  float power = voltage * current;
  
  // JSON 데이터 구성
  doc["v"] = round(voltage * 1000) / 1000.0;  // 소수점 3자리
  doc["a"] = round(current * 1000) / 1000.0;  // 소수점 3자리
  doc["w"] = round(power * 1000) / 1000.0;    // 소수점 3자리
  doc["ts"] = millis();
  doc["seq"] = ++sequenceNumber;
  doc["status"] = sensorStatus ? "ok" : "error";
  doc["mode"] = getModeString();
  
  // JSON 문자열로 직렬화
  String jsonString;
  serializeJson(doc, jsonString);
  
  // 시리얼로 전송
  Serial.println(jsonString);
}

float generateVoltage() {
  float voltage = simParams.baseVoltage;
  
  switch (currentMode) {
    case NORMAL:
      voltage += random(-50, 51) / 1000.0; // ±0.05V 변동
      break;
      
    case LOAD_SPIKE:
      // 부하 급증 시 전압 강하 시뮬레이션
      voltage -= 0.3 + random(0, 200) / 1000.0;
      break;
      
    case VOLTAGE_DROP:
      // 전압 강하 시뮬레이션
      voltage = 4.2 + random(-100, 100) / 1000.0;
      break;
      
    case NOISE:
      // 노이즈가 많은 환경
      voltage += random(-200, 201) / 1000.0;
      break;
      
    case ERROR_TEST:
      // 에러 상황 (센서 오류)
      voltage = -1.0; // 비정상 값
      sensorStatus = false;
      break;
  }
  
  return max(0.0, voltage);
}

float generateCurrent() {
  float current = simParams.baseCurrent;
  unsigned long time = millis();
  
  switch (currentMode) {
    case NORMAL:
      // 사인파 패턴 + 노이즈
      current += 0.1 * sin(2 * PI * time / 10000.0);
      current += random(-20, 21) / 1000.0;
      break;
      
    case LOAD_SPIKE:
      // 급격한 전류 증가
      current = 0.8 + random(0, 200) / 1000.0;
      break;
      
    case VOLTAGE_DROP:
      // 전압 강하 시 전류 증가
      current = 0.35 + random(-50, 51) / 1000.0;
      break;
      
    case NOISE:
      // 노이즈가 많은 전류
      current += random(-100, 101) / 1000.0;
      break;
      
    case ERROR_TEST:
      // 에러 상황
      current = -1.0;
      break;
  }
  
  return max(0.0, current);
}

void handleSerialCommands() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    // JSON 명령 파싱 시도
    StaticJsonDocument<200> doc;
    DeserializationError error = deserializeJson(doc, input);
    
    if (error) {
      // JSON이 아닌 경우 텍스트 명령으로 처리
      handleTextCommand(input);
      return;
    }
    
    // JSON 명령 처리
    handleJsonCommand(doc);
  }
}

void handleJsonCommand(const StaticJsonDocument<200>& doc) {
  String cmd = doc["cmd"];
  unsigned long seq = doc["seq"];
  
  StaticJsonDocument<100> response;
  response["ack"] = seq;
  
  if (cmd == "set_interval") {
    unsigned long newInterval = doc["value"];
    if (newInterval >= 100 && newInterval <= 10000) {
      measurementInterval = newInterval;
      response["result"] = "ok";
      response["message"] = "Interval updated";
    } else {
      response["result"] = "error";
      response["message"] = "Invalid interval range (100-10000ms)";
    }
  }
  else if (cmd == "set_mode") {
    String mode = doc["value"];
    if (setSimulationMode(mode)) {
      response["result"] = "ok";
      response["message"] = "Mode changed to " + mode;
    } else {
      response["result"] = "error";
      response["message"] = "Invalid mode";
    }
  }
  else if (cmd == "get_status") {
    response["result"] = "ok";
    response["uptime"] = millis();
    response["interval"] = measurementInterval;
    response["mode"] = getModeString();
    response["sequence"] = sequenceNumber;
  }
  else if (cmd == "reset") {
    response["result"] = "ok";
    response["message"] = "Resetting...";
    String responseStr;
    serializeJson(response, responseStr);
    Serial.println(responseStr);
    delay(1000);
    setup(); // 소프트 리셋
    return;
  }
  else {
    response["result"] = "error";
    response["message"] = "Unknown command";
  }
  
  String responseStr;
  serializeJson(response, responseStr);
  Serial.println(responseStr);
}

void handleTextCommand(const String& command) {
  String cmd = command;
  cmd.toUpperCase();
  
  if (cmd == "HELP") {
    sendStatusMessage("=== Available Commands ===");
    sendStatusMessage("JSON Commands:");
    sendStatusMessage("  {\"cmd\":\"set_interval\",\"value\":1000,\"seq\":1}");
    sendStatusMessage("  {\"cmd\":\"set_mode\",\"value\":\"NORMAL\",\"seq\":2}");
    sendStatusMessage("  {\"cmd\":\"get_status\",\"seq\":3}");
    sendStatusMessage("  {\"cmd\":\"reset\",\"seq\":4}");
    sendStatusMessage("Text Commands: HELP, STATUS, MODES");
    sendStatusMessage("========================");
  }
  else if (cmd == "STATUS") {
    sendStatusMessage("=== Simulator Status ===");
    sendStatusMessage("Uptime: " + String(millis()/1000) + "s");
    sendStatusMessage("Mode: " + getModeString());
    sendStatusMessage("Interval: " + String(measurementInterval) + "ms");
    sendStatusMessage("Sequence: " + String(sequenceNumber));
    sendStatusMessage("Sensor: " + String(sensorStatus ? "OK" : "ERROR"));
    sendStatusMessage("=======================");
  }
  else if (cmd == "MODES") {
    sendStatusMessage("=== Simulation Modes ===");
    sendStatusMessage("NORMAL - Normal operation");
    sendStatusMessage("LOAD_SPIKE - Load spike simulation");
    sendStatusMessage("VOLTAGE_DROP - Voltage drop simulation");
    sendStatusMessage("NOISE - Noisy environment");
    sendStatusMessage("ERROR_TEST - Error condition test");
    sendStatusMessage("=======================");
  }
  else {
    sendStatusMessage("Unknown command. Type HELP for available commands.");
  }
}

bool setSimulationMode(const String& mode) {
  if (mode == "NORMAL") {
    currentMode = NORMAL;
    sensorStatus = true;
  } else if (mode == "LOAD_SPIKE") {
    currentMode = LOAD_SPIKE;
    sensorStatus = true;
  } else if (mode == "VOLTAGE_DROP") {
    currentMode = VOLTAGE_DROP;
    sensorStatus = true;
  } else if (mode == "NOISE") {
    currentMode = NOISE;
    sensorStatus = true;
  } else if (mode == "ERROR_TEST") {
    currentMode = ERROR_TEST;
    sensorStatus = false;
  } else {
    return false;
  }
  return true;
}

String getModeString() {
  switch (currentMode) {
    case NORMAL: return "NORMAL";
    case LOAD_SPIKE: return "LOAD_SPIKE";
    case VOLTAGE_DROP: return "VOLTAGE_DROP";
    case NOISE: return "NOISE";
    case ERROR_TEST: return "ERROR_TEST";
    default: return "UNKNOWN";
  }
}

void updateSimulationMode(unsigned long currentTime) {
  // 30초마다 모드 자동 변경 (데모용)
  static unsigned long lastModeChange = 0;
  static int modeIndex = 0;
  
  if (currentTime - lastModeChange > 30000) { // 30초
    SimulationMode modes[] = {NORMAL, LOAD_SPIKE, VOLTAGE_DROP, NOISE};
    currentMode = modes[modeIndex % 4];
    modeIndex++;
    lastModeChange = currentTime;
    sensorStatus = true; // ERROR_TEST 제외하고는 정상 상태
    
    sendStatusMessage("Auto mode change: " + getModeString());
  }
}

void sendStatusMessage(const String& message) {
  StaticJsonDocument<150> doc;
  doc["type"] = "status";
  doc["message"] = message;
  doc["ts"] = millis();
  
  String jsonString;
  serializeJson(doc, jsonString);
  Serial.println(jsonString);
}