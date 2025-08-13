"""
Arduino UNO R4 WiFi + INA219 Mock Simulator
실제 하드웨어 없이도 개발 가능한 시뮬레이터

기능:
- 실제 Arduino 시뮬레이터와 동일한 JSON 프로토콜
- 다양한 시나리오 테스트 지원
- 시리얼 포트 에뮬레이션
- 실시간 데이터 생성
"""

import json
import math
import queue
import random
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class SimulationMode(Enum):
    NORMAL = "NORMAL"
    LOAD_SPIKE = "LOAD_SPIKE"
    VOLTAGE_DROP = "VOLTAGE_DROP"
    NOISE = "NOISE"
    ERROR_TEST = "ERROR_TEST"


@dataclass
class SimulationParams:
    base_voltage: float = 5.0
    base_current: float = 0.2
    voltage_noise: float = 0.05
    current_noise: float = 0.02
    cycle_time: int = 30000  # ms


class ArduinoMockSimulator:
    """Arduino UNO R4 WiFi + INA219 Mock Simulator"""

    def __init__(self, port_name: str = "MOCK_COM1"):
        self.port_name = port_name
        self.is_running = False
        self.is_connected = False

        # 시뮬레이션 상태
        self.current_mode = SimulationMode.NORMAL
        self.measurement_interval = 1000  # ms
        self.sequence_number = 0
        self.sensor_status = True
        self.start_time = time.time()

        # 시뮬레이션 파라미터
        self.sim_params = SimulationParams()

        # 통신 큐
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()

        # 콜백 함수들
        self.data_callback: Optional[Callable[[dict[str, Any]], None]] = None
        self.status_callback: Optional[Callable[[str], None]] = None

        # 스레드
        self.simulation_thread: Optional[threading.Thread] = None
        self.command_thread: Optional[threading.Thread] = None

        print(f"Arduino Mock Simulator initialized on {port_name}")

    def connect(self) -> bool:
        """시뮬레이터 연결"""
        if self.is_connected:
            return True

        try:
            self.is_connected = True
            self.is_running = True

            # 시뮬레이션 스레드 시작
            self.simulation_thread = threading.Thread(
                target=self._simulation_loop, daemon=True
            )
            self.simulation_thread.start()

            # 명령 처리 스레드 시작
            self.command_thread = threading.Thread(
                target=self._command_loop, daemon=True
            )
            self.command_thread.start()

            # 시작 메시지 전송
            self._send_status_message("INA219 Power Monitoring Simulator - UNO R4 WiFi")
            self._send_status_message("JSON Protocol v1.0")
            self._send_status_message(f"Simulation Mode: {self.current_mode.value}")
            self._send_status_message("Simulator ready - Starting measurements...")

            return True

        except Exception as e:
            print(f"Connection error: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        """시뮬레이터 연결 해제"""
        self.is_running = False
        self.is_connected = False

        if self.simulation_thread and self.simulation_thread.is_alive():
            self.simulation_thread.join(timeout=1.0)

        if self.command_thread and self.command_thread.is_alive():
            self.command_thread.join(timeout=1.0)

        print("Arduino Mock Simulator disconnected")

    def send_command(self, command: str) -> bool:
        """명령 전송"""
        if not self.is_connected:
            return False

        try:
            self.input_queue.put(command, timeout=1.0)
            return True
        except queue.Full:
            return False

    def read_data(self, timeout: float = 1.0) -> Optional[str]:
        """데이터 읽기"""
        if not self.is_connected:
            return None

        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def set_data_callback(self, callback: Callable[[dict[str, Any]], None]):
        """데이터 수신 콜백 설정"""
        self.data_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]):
        """상태 메시지 콜백 설정"""
        self.status_callback = callback

    def _simulation_loop(self):
        """시뮬레이션 메인 루프"""
        last_measurement = time.time()
        last_mode_change = time.time()
        mode_index = 0

        while self.is_running:
            current_time = time.time()

            # 측정 간격 확인
            if (current_time - last_measurement) * 1000 >= self.measurement_interval:
                self._send_measurement_data()
                last_measurement = current_time

            # 자동 모드 변경 (30초마다)
            if current_time - last_mode_change > 30:
                modes = [
                    SimulationMode.NORMAL,
                    SimulationMode.LOAD_SPIKE,
                    SimulationMode.VOLTAGE_DROP,
                    SimulationMode.NOISE,
                ]
                self.current_mode = modes[mode_index % len(modes)]
                mode_index += 1
                last_mode_change = current_time
                self.sensor_status = True

                self._send_status_message(
                    f"Auto mode change: {self.current_mode.value}"
                )

            time.sleep(0.01)  # 10ms 대기

    def _command_loop(self):
        """명령 처리 루프"""
        while self.is_running:
            try:
                command = self.input_queue.get(timeout=0.1)
                self._handle_command(command)
            except queue.Empty:
                continue

    def _send_measurement_data(self):
        """측정 데이터 전송"""
        voltage = self._generate_voltage()
        current = self._generate_current()
        power = voltage * current

        data = {
            "v": round(voltage, 3),
            "a": round(current, 3),
            "w": round(power, 3),
            "ts": int(time.time() * 1000),
            "seq": self.sequence_number,
            "status": "ok" if self.sensor_status else "error",
            "mode": self.current_mode.value,
        }

        self.sequence_number += 1

        json_str = json.dumps(data)
        self.output_queue.put(json_str)

        # 콜백 호출
        if self.data_callback:
            self.data_callback(data)

    def _generate_voltage(self) -> float:
        """전압 시뮬레이션"""
        voltage = self.sim_params.base_voltage

        if self.current_mode == SimulationMode.NORMAL:
            voltage += random.uniform(-0.05, 0.05)
        elif self.current_mode == SimulationMode.LOAD_SPIKE:
            voltage -= 0.3 + random.uniform(0, 0.2)
        elif self.current_mode == SimulationMode.VOLTAGE_DROP:
            voltage = 4.2 + random.uniform(-0.1, 0.1)
        elif self.current_mode == SimulationMode.NOISE:
            voltage += random.uniform(-0.2, 0.2)
        elif self.current_mode == SimulationMode.ERROR_TEST:
            voltage = -1.0
            self.sensor_status = False

        return max(0.0, voltage)

    def _generate_current(self) -> float:
        """전류 시뮬레이션"""
        current = self.sim_params.base_current
        current_time = time.time() - self.start_time

        if self.current_mode == SimulationMode.NORMAL:
            # 사인파 패턴 + 노이즈
            current += 0.1 * math.sin(2 * math.pi * current_time / 10)
            current += random.uniform(-0.02, 0.02)
        elif self.current_mode == SimulationMode.LOAD_SPIKE:
            current = 0.8 + random.uniform(0, 0.2)
        elif self.current_mode == SimulationMode.VOLTAGE_DROP:
            current = 0.35 + random.uniform(-0.05, 0.05)
        elif self.current_mode == SimulationMode.NOISE:
            current += random.uniform(-0.1, 0.1)
        elif self.current_mode == SimulationMode.ERROR_TEST:
            current = -1.0

        return max(0.0, current)

    def _handle_command(self, command: str):
        """명령 처리"""
        command = command.strip()

        # JSON 명령 파싱 시도
        try:
            cmd_data = json.loads(command)
            self._handle_json_command(cmd_data)
            return
        except json.JSONDecodeError:
            pass

        # 텍스트 명령 처리
        self._handle_text_command(command)

    def _handle_json_command(self, cmd_data: dict[str, Any]):
        """JSON 명령 처리"""
        cmd = cmd_data.get("cmd", "")
        seq = cmd_data.get("seq", 0)

        response = {"ack": seq}

        if cmd == "set_interval":
            new_interval = cmd_data.get("value", 1000)
            if 100 <= new_interval <= 10000:
                self.measurement_interval = new_interval
                response["result"] = "ok"
                response["message"] = "Interval updated"
            else:
                response["result"] = "error"
                response["message"] = "Invalid interval range (100-10000ms)"

        elif cmd == "set_mode":
            mode_str = cmd_data.get("value", "")
            if self._set_simulation_mode(mode_str):
                response["result"] = "ok"
                response["message"] = f"Mode changed to {mode_str}"
            else:
                response["result"] = "error"
                response["message"] = "Invalid mode"

        elif cmd == "get_status":
            response["result"] = "ok"
            response["uptime"] = int((time.time() - self.start_time) * 1000)
            response["interval"] = self.measurement_interval
            response["mode"] = self.current_mode.value
            response["sequence"] = self.sequence_number

        elif cmd == "reset":
            response["result"] = "ok"
            response["message"] = "Resetting..."
            self._send_json_response(response)
            self._reset_simulator()
            return

        else:
            response["result"] = "error"
            response["message"] = "Unknown command"

        self._send_json_response(response)

    def _handle_text_command(self, command: str):
        """텍스트 명령 처리"""
        cmd = command.upper()

        if cmd == "HELP":
            self._send_status_message("=== Available Commands ===")
            self._send_status_message("JSON Commands:")
            self._send_status_message('  {"cmd":"set_interval","value":1000,"seq":1}')
            self._send_status_message('  {"cmd":"set_mode","value":"NORMAL","seq":2}')
            self._send_status_message('  {"cmd":"get_status","seq":3}')
            self._send_status_message('  {"cmd":"reset","seq":4}')
            self._send_status_message("Text Commands: HELP, STATUS, MODES")
            self._send_status_message("========================")

        elif cmd == "STATUS":
            uptime = int(time.time() - self.start_time)
            self._send_status_message("=== Simulator Status ===")
            self._send_status_message(f"Uptime: {uptime}s")
            self._send_status_message(f"Mode: {self.current_mode.value}")
            self._send_status_message(f"Interval: {self.measurement_interval}ms")
            self._send_status_message(f"Sequence: {self.sequence_number}")
            self._send_status_message(
                f"Sensor: {'OK' if self.sensor_status else 'ERROR'}"
            )
            self._send_status_message("=======================")

        elif cmd == "MODES":
            self._send_status_message("=== Simulation Modes ===")
            self._send_status_message("NORMAL - Normal operation")
            self._send_status_message("LOAD_SPIKE - Load spike simulation")
            self._send_status_message("VOLTAGE_DROP - Voltage drop simulation")
            self._send_status_message("NOISE - Noisy environment")
            self._send_status_message("ERROR_TEST - Error condition test")
            self._send_status_message("=======================")

        else:
            self._send_status_message(
                "Unknown command. Type HELP for available commands."
            )

    def _set_simulation_mode(self, mode_str: str) -> bool:
        """시뮬레이션 모드 설정"""
        try:
            self.current_mode = SimulationMode(mode_str)
            self.sensor_status = self.current_mode != SimulationMode.ERROR_TEST
            return True
        except ValueError:
            return False

    def _send_json_response(self, response: dict[str, Any]):
        """JSON 응답 전송"""
        json_str = json.dumps(response)
        self.output_queue.put(json_str)

    def _send_status_message(self, message: str):
        """상태 메시지 전송"""
        status_data = {
            "type": "status",
            "message": message,
            "ts": int(time.time() * 1000),
        }

        json_str = json.dumps(status_data)
        self.output_queue.put(json_str)

        # 콜백 호출
        if self.status_callback:
            self.status_callback(message)

    def _reset_simulator(self):
        """시뮬레이터 리셋"""
        self.sequence_number = 0
        self.current_mode = SimulationMode.NORMAL
        self.measurement_interval = 1000
        self.sensor_status = True
        self.start_time = time.time()

        time.sleep(1)
        self._send_status_message("Simulator reset complete")


# 테스트 및 데모용 함수들
def demo_basic_usage():
    """기본 사용법 데모"""
    print("=== Arduino Mock Simulator Demo ===")

    simulator = ArduinoMockSimulator("DEMO_PORT")

    # 콜백 함수 설정
    def on_data(data):
        print(f"Data: V={data['v']}V, A={data['a']}A, W={data['w']}W")

    def on_status(message):
        print(f"Status: {message}")

    simulator.set_data_callback(on_data)
    simulator.set_status_callback(on_status)

    # 연결 및 테스트
    if simulator.connect():
        print("Simulator connected successfully")

        # 몇 초간 데이터 수집
        time.sleep(5)

        # 명령 테스트
        print("\nTesting commands...")
        simulator.send_command('{"cmd":"set_interval","value":500,"seq":1}')
        time.sleep(1)

        simulator.send_command('{"cmd":"set_mode","value":"LOAD_SPIKE","seq":2}')
        time.sleep(3)

        simulator.send_command('{"cmd":"get_status","seq":3}')
        time.sleep(1)

        simulator.disconnect()
    else:
        print("Failed to connect simulator")


if __name__ == "__main__":
    demo_basic_usage()
