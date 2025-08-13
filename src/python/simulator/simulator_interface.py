"""
Arduino Simulator Interface
실제 Arduino와 Mock Simulator를 통합하여 사용할 수 있는 인터페이스

기능:
- 실제 Arduino 시리얼 통신
- Mock Simulator 사용
- 자동 감지 및 전환
- 통일된 API 제공
"""

import json
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Optional

import serial
import serial.tools.list_ports

try:
    from .arduino_mock import ArduinoMockSimulator
except ImportError:
    from arduino_mock import ArduinoMockSimulator


@dataclass
class SimulatorConfig:
    """시뮬레이터 설정"""

    port: str = "AUTO"  # AUTO, MOCK, 또는 실제 포트명
    baudrate: int = 115200
    timeout: float = 1.0
    auto_reconnect: bool = True
    mock_fallback: bool = True  # 실제 포트 없을 때 Mock 사용


class BaseSimulator(ABC):
    """시뮬레이터 기본 인터페이스"""

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self):
        pass

    @abstractmethod
    def send_command(self, command: str) -> bool:
        pass

    @abstractmethod
    def read_data(self, timeout: float = 1.0) -> Optional[str]:
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        pass


class SerialSimulator(BaseSimulator):
    """실제 Arduino 시리얼 통신"""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_conn: Optional[serial.Serial] = None
        self._connected = False

    def connect(self) -> bool:
        try:
            self.serial_conn = serial.Serial(
                port=self.port, baudrate=self.baudrate, timeout=self.timeout
            )
            self._connected = True
            print(f"Connected to Arduino on {self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.port}: {e}")
            self._connected = False
            return False

    def disconnect(self):
        if self.serial_conn:
            self.serial_conn.close()
            self.serial_conn = None
        self._connected = False
        print(f"Disconnected from {self.port}")

    def send_command(self, command: str) -> bool:
        if not self._connected or not self.serial_conn:
            return False

        try:
            self.serial_conn.write((command + "\n").encode())
            return True
        except Exception as e:
            print(f"Failed to send command: {e}")
            return False

    def read_data(self, timeout: float = 1.0) -> Optional[str]:
        if not self._connected or not self.serial_conn:
            return None

        try:
            # 타임아웃 임시 변경
            original_timeout = self.serial_conn.timeout
            self.serial_conn.timeout = timeout

            line = self.serial_conn.readline().decode().strip()

            # 타임아웃 복원
            self.serial_conn.timeout = original_timeout

            return line if line else None
        except Exception as e:
            print(f"Failed to read data: {e}")
            return None

    def is_connected(self) -> bool:
        return self._connected and self.serial_conn is not None


class MockSimulatorWrapper(BaseSimulator):
    """Mock Simulator 래퍼"""

    def __init__(self, port_name: str = "MOCK_COM"):
        self.mock_sim = ArduinoMockSimulator(port_name)

    def connect(self) -> bool:
        return self.mock_sim.connect()

    def disconnect(self):
        self.mock_sim.disconnect()

    def send_command(self, command: str) -> bool:
        return self.mock_sim.send_command(command)

    def read_data(self, timeout: float = 1.0) -> Optional[str]:
        return self.mock_sim.read_data(timeout)

    def is_connected(self) -> bool:
        return self.mock_sim.is_connected

    def set_data_callback(self, callback: Callable[[dict[str, Any]], None]):
        self.mock_sim.set_data_callback(callback)

    def set_status_callback(self, callback: Callable[[str], None]):
        self.mock_sim.set_status_callback(callback)


class SimulatorManager:
    """시뮬레이터 관리자 - 실제/Mock 시뮬레이터 통합 관리"""

    def __init__(self, config: SimulatorConfig):
        self.config = config
        self.simulator: Optional[BaseSimulator] = None
        self.is_mock = False

        # 콜백 함수들
        self.data_callback: Optional[Callable[[dict[str, Any]], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None
        self.connection_callback: Optional[Callable[[bool, str], None]] = None

        # 자동 재연결 스레드
        self.reconnect_thread: Optional[threading.Thread] = None
        self.should_reconnect = False

    def connect(self) -> bool:
        """시뮬레이터 연결"""
        if self.config.port == "MOCK":
            return self._connect_mock()
        elif self.config.port == "AUTO":
            return self._connect_auto()
        else:
            return self._connect_serial(self.config.port)

    def disconnect(self):
        """시뮬레이터 연결 해제"""
        self.should_reconnect = False

        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=1.0)

        if self.simulator:
            self.simulator.disconnect()
            self.simulator = None

        print("Simulator disconnected")

    def send_command(self, command: str) -> bool:
        """명령 전송"""
        if not self.simulator:
            return False
        return self.simulator.send_command(command)

    def read_data(self, timeout: float = 1.0) -> Optional[str]:
        """데이터 읽기"""
        if not self.simulator:
            return None
        return self.simulator.read_data(timeout)

    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self.simulator is not None and self.simulator.is_connected()

    def get_simulator_type(self) -> str:
        """시뮬레이터 타입 반환"""
        return "Mock" if self.is_mock else "Serial"

    def set_data_callback(self, callback: Callable[[dict[str, Any]], None]):
        """데이터 콜백 설정"""
        self.data_callback = callback
        if isinstance(self.simulator, MockSimulatorWrapper):
            self.simulator.set_data_callback(callback)

    def set_status_callback(self, callback: Callable[[str], None]):
        """상태 콜백 설정"""
        self.status_callback = callback
        if isinstance(self.simulator, MockSimulatorWrapper):
            self.simulator.set_status_callback(callback)

    def set_connection_callback(self, callback: Callable[[bool, str], None]):
        """연결 상태 콜백 설정"""
        self.connection_callback = callback

    def _connect_auto(self) -> bool:
        """자동 연결 - Arduino 포트 검색 후 Mock 폴백"""
        # Arduino 포트 검색
        arduino_port = self._find_arduino_port()

        if arduino_port:
            print(f"Found Arduino on {arduino_port}")
            if self._connect_serial(arduino_port):
                return True

        # Arduino를 찾지 못했거나 연결 실패 시 Mock 사용
        if self.config.mock_fallback:
            print("Arduino not found, using Mock Simulator")
            return self._connect_mock()

        return False

    def _connect_serial(self, port: str) -> bool:
        """시리얼 포트 연결"""
        try:
            self.simulator = SerialSimulator(
                port, self.config.baudrate, self.config.timeout
            )
            if self.simulator.connect():
                self.is_mock = False
                self._start_auto_reconnect()
                self._notify_connection(True, f"Serial:{port}")
                return True
        except Exception as e:
            print(f"Serial connection failed: {e}")

        return False

    def _connect_mock(self) -> bool:
        """Mock 시뮬레이터 연결"""
        try:
            self.simulator = MockSimulatorWrapper("MOCK_ARDUINO")
            if self.simulator.connect():
                self.is_mock = True

                # Mock 시뮬레이터 콜백 설정
                if self.data_callback:
                    self.simulator.set_data_callback(self.data_callback)
                if self.status_callback:
                    self.simulator.set_status_callback(self.status_callback)

                self._notify_connection(True, "Mock")
                return True
        except Exception as e:
            print(f"Mock connection failed: {e}")

        return False

    def _find_arduino_port(self) -> Optional[str]:
        """Arduino 포트 자동 검색"""
        ports = serial.tools.list_ports.comports()

        # Arduino 관련 키워드
        arduino_keywords = [
            "arduino",
            "uno",
            "nano",
            "mega",
            "leonardo",
            "ch340",
            "cp210",
            "ftdi",
            "usb serial",
        ]

        for port in ports:
            port_info = f"{port.description} {port.manufacturer}".lower()

            for keyword in arduino_keywords:
                if keyword in port_info:
                    return port.device

        # 키워드 매칭 실패 시 첫 번째 시리얼 포트 시도
        if ports:
            return ports[0].device

        return None

    def _start_auto_reconnect(self):
        """자동 재연결 스레드 시작"""
        if not self.config.auto_reconnect or self.is_mock:
            return

        self.should_reconnect = True
        self.reconnect_thread = threading.Thread(
            target=self._reconnect_loop, daemon=True
        )
        self.reconnect_thread.start()

    def _reconnect_loop(self):
        """자동 재연결 루프"""
        while self.should_reconnect:
            time.sleep(5)  # 5초마다 확인

            if not self.is_connected():
                print("Connection lost, attempting to reconnect...")
                self._notify_connection(False, "Disconnected")

                # 재연결 시도
                if self._connect_auto():
                    print("Reconnected successfully")
                else:
                    print("Reconnection failed")

    def _notify_connection(self, connected: bool, info: str):
        """연결 상태 알림"""
        if self.connection_callback:
            self.connection_callback(connected, info)


# 편의 함수들
def create_simulator(
    port: str = "AUTO", mock_fallback: bool = True
) -> SimulatorManager:
    """시뮬레이터 생성 편의 함수"""
    config = SimulatorConfig(port=port, mock_fallback=mock_fallback)
    return SimulatorManager(config)


def list_available_ports():
    """사용 가능한 시리얼 포트 목록"""
    ports = serial.tools.list_ports.comports()

    print("Available Serial Ports:")
    print("=" * 40)

    if not ports:
        print("No serial ports found")
        return

    for i, port in enumerate(ports, 1):
        print(f"{i}. {port.device}")
        print(f"   Description: {port.description}")
        print(f"   Manufacturer: {port.manufacturer}")
        print()


# 테스트 및 데모
def demo_simulator_manager():
    """시뮬레이터 매니저 데모"""
    print("=== Simulator Manager Demo ===")

    # 사용 가능한 포트 목록
    list_available_ports()

    # 시뮬레이터 생성 및 연결
    sim_manager = create_simulator("AUTO", mock_fallback=True)

    # 콜백 설정
    def on_data(data):
        print(
            f"[{sim_manager.get_simulator_type()}] Data: V={data['v']}V, A={data['a']}A, W={data['w']}W"
        )

    def on_status(message):
        print(f"[{sim_manager.get_simulator_type()}] Status: {message}")

    def on_connection(connected, info):
        status = "Connected" if connected else "Disconnected"
        print(f"[Connection] {status}: {info}")

    sim_manager.set_data_callback(on_data)
    sim_manager.set_status_callback(on_status)
    sim_manager.set_connection_callback(on_connection)

    # 연결 시도
    if sim_manager.connect():
        print(f"Connected using {sim_manager.get_simulator_type()} simulator")

        # 데이터 수집 테스트
        print("\nCollecting data for 10 seconds...")
        start_time = time.time()

        while time.time() - start_time < 10:
            data = sim_manager.read_data(timeout=0.1)
            if data:
                try:
                    json_data = json.loads(data)
                    if json_data.get("type") != "status":  # 상태 메시지 제외
                        print(f"Raw data: {data}")
                except json.JSONDecodeError:
                    print(f"Non-JSON data: {data}")

            time.sleep(0.1)

        # 명령 테스트
        print("\nTesting commands...")
        sim_manager.send_command('{"cmd":"get_status","seq":1}')
        time.sleep(1)

        sim_manager.send_command('{"cmd":"set_mode","value":"LOAD_SPIKE","seq":2}')
        time.sleep(2)

        sim_manager.disconnect()
    else:
        print("Failed to connect to any simulator")


if __name__ == "__main__":
    demo_simulator_manager()
