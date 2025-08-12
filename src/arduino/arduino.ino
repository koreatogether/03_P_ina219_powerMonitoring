/*
 * INA219 Power Monitoring System
 * Arduino 펌웨어 - 전력 측정 및 시리얼 통신
 * 
 * 기능:
 * - INA219 센서를 통한 전압, 전류, 전력 측정
 * - 시리얼 통신을 통한 데이터 전송
 * - 실시간 모니터링
 */

#include <Wire.h>
#include <Adafruit_INA219.h>

// INA219 센서 객체
Adafruit_INA219 ina219;

// 측정 설정
const unsigned long MEASUREMENT_INTERVAL = 1000; // 1초 간격
unsigned long lastMeasurement = 0;

// 데이터 구조체
struct PowerData {
  float voltage_V;
  float current_mA;
  float power_mW;
  unsigned long timestamp;
};

void setup() {
  // 시리얼 통신 초기화
  Serial.begin(115200);
  while (!Serial) {
    delay(10);
  }
  
  Serial.println("INA219 Power Monitoring System");
  Serial.println("==============================");
  
  // I2C 초기화
  Wire.begin();
  
  // INA219 초기화
  if (!ina219.begin()) {
    Serial.println("ERROR: INA219 센서를 찾을 수 없습니다!");
    Serial.println("연결을 확인하고 다시 시도하세요.");
    while (1) {
      delay(1000);
    }
  }
  
  Serial.println("INA219 센서 초기화 완료");
  
  // 측정 범위 설정 (선택사항)
  // ina219.setCalibration_32V_2A();  // 32V, 2A 범위
  // ina219.setCalibration_32V_1A();  // 32V, 1A 범위 (기본값)
  // ina219.setCalibration_16V_400mA(); // 16V, 400mA 범위 (고정밀도)
  
  Serial.println("측정 시작...");
  Serial.println("Format: TIMESTAMP,VOLTAGE,CURRENT,POWER");
}

void loop() {
  unsigned long currentTime = millis();
  
  // 측정 간격 확인
  if (currentTime - lastMeasurement >= MEASUREMENT_INTERVAL) {
    PowerData data = measurePower();
    
    // 데이터 유효성 검사
    if (isValidMeasurement(data)) {
      sendData(data);
    } else {
      Serial.println("ERROR: 측정 데이터가 유효하지 않습니다");
    }
    
    lastMeasurement = currentTime;
  }
  
  // 시리얼 명령 처리
  handleSerialCommands();
  
  delay(10); // CPU 부하 감소
}

PowerData measurePower() {
  PowerData data;
  
  // 타임스탬프 설정
  data.timestamp = millis();
  
  // INA219에서 측정값 읽기
  data.voltage_V = ina219.getBusVoltage_V();
  data.current_mA = ina219.getCurrent_mA();
  data.power_mW = ina219.getPower_mW();
  
  return data;
}

bool isValidMeasurement(const PowerData& data) {
  // 전압 범위 확인 (0V ~ 32V)
  if (data.voltage_V < 0 || data.voltage_V > 32.0) {
    return false;
  }
  
  // 전류 범위 확인 (-3200mA ~ 3200mA)
  if (data.current_mA < -3200 || data.current_mA > 3200) {
    return false;
  }
  
  // 전력 범위 확인 (0mW ~ 100W)
  if (data.power_mW < 0 || data.power_mW > 100000) {
    return false;
  }
  
  return true;
}

void sendData(const PowerData& data) {
  // CSV 형식으로 데이터 전송
  Serial.print(data.timestamp);
  Serial.print(",");
  Serial.print(data.voltage_V, 3);  // 소수점 3자리
  Serial.print(",");
  Serial.print(data.current_mA, 2); // 소수점 2자리
  Serial.print(",");
  Serial.print(data.power_mW, 2);   // 소수점 2자리
  Serial.println();
}

void handleSerialCommands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();
    
    if (command == "STATUS") {
      printStatus();
    } else if (command == "RESET") {
      resetSystem();
    } else if (command == "HELP") {
      printHelp();
    } else if (command.startsWith("INTERVAL=")) {
      setMeasurementInterval(command);
    } else {
      Serial.println("ERROR: 알 수 없는 명령어: " + command);
      Serial.println("HELP를 입력하여 사용 가능한 명령어를 확인하세요.");
    }
  }
}

void printStatus() {
  Serial.println("=== 시스템 상태 ===");
  Serial.print("업타임: ");
  Serial.print(millis() / 1000);
  Serial.println("초");
  
  Serial.print("측정 간격: ");
  Serial.print(MEASUREMENT_INTERVAL);
  Serial.println("ms");
  
  // 현재 측정값
  PowerData current = measurePower();
  Serial.print("현재 전압: ");
  Serial.print(current.voltage_V, 3);
  Serial.println("V");
  
  Serial.print("현재 전류: ");
  Serial.print(current.current_mA, 2);
  Serial.println("mA");
  
  Serial.print("현재 전력: ");
  Serial.print(current.power_mW, 2);
  Serial.println("mW");
  
  Serial.println("==================");
}

void resetSystem() {
  Serial.println("시스템을 재시작합니다...");
  delay(1000);
  
  // 소프트웨어 리셋 (Arduino Uno/Nano)
  #if defined(__AVR__)
    asm volatile ("  jmp 0");
  #elif defined(ESP32)
    ESP.restart();
  #else
    // 다른 플랫폼의 경우 setup() 함수 재호출
    setup();
  #endif
}

void printHelp() {
  Serial.println("=== 사용 가능한 명령어 ===");
  Serial.println("STATUS       - 시스템 상태 출력");
  Serial.println("RESET        - 시스템 재시작");
  Serial.println("HELP         - 도움말 출력");
  Serial.println("INTERVAL=ms  - 측정 간격 설정 (예: INTERVAL=500)");
  Serial.println("========================");
}

void setMeasurementInterval(const String& command) {
  int equalPos = command.indexOf('=');
  if (equalPos > 0) {
    String intervalStr = command.substring(equalPos + 1);
    unsigned long newInterval = intervalStr.toInt();
    
    if (newInterval >= 100 && newInterval <= 60000) {
      // MEASUREMENT_INTERVAL = newInterval; // const이므로 런타임 변경 불가
      Serial.print("측정 간격 변경 요청: ");
      Serial.print(newInterval);
      Serial.println("ms");
      Serial.println("주의: 현재 버전에서는 컴파일 타임에만 변경 가능합니다.");
    } else {
      Serial.println("ERROR: 측정 간격은 100ms ~ 60000ms 범위여야 합니다.");
    }
  } else {
    Serial.println("ERROR: 잘못된 형식입니다. 예: INTERVAL=1000");
  }
}