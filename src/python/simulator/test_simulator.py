#!/usr/bin/env python3
"""
Arduino Simulator Test Script
시뮬레이터 기능 테스트 및 데모

사용법:
python test_simulator.py [옵션]

옵션:
--mock: Mock 시뮬레이터만 사용
--port COM3: 특정 포트 사용
--duration 30: 테스트 시간 (초)
"""

import argparse
import json
import sys
import time
from typing import Any

try:
    from simulator_interface import create_simulator, list_available_ports
except ImportError:
    import os
    import sys

    sys.path.append(os.path.dirname(__file__))
    from simulator_interface import create_simulator, list_available_ports


class SimulatorTester:
    """시뮬레이터 테스트 클래스"""

    def __init__(self, port: str = "AUTO", duration: int = 30):
        self.port = port
        self.duration = duration
        self.data_count = 0
        self.error_count = 0
        self.last_sequence = -1
        self.start_time = time.time()

        # 통계 데이터
        self.voltage_data = []
        self.current_data = []
        self.power_data = []

    def run_test(self):
        """테스트 실행"""
        print("=== Arduino Simulator Test ===")
        print(f"Port: {self.port}")
        print(f"Duration: {self.duration} seconds")
        print("=" * 40)

        # 시뮬레이터 생성
        sim_manager = create_simulator(self.port, mock_fallback=True)

        # 콜백 설정
        sim_manager.set_data_callback(self._on_data)
        sim_manager.set_status_callback(self._on_status)
        sim_manager.set_connection_callback(self._on_connection)

        # 연결
        if not sim_manager.connect():
            print("❌ Failed to connect to simulator")
            return False

        print(f"✅ Connected using {sim_manager.get_simulator_type()} simulator")

        try:
            # 기본 테스트
            self._run_basic_test(sim_manager)

            # 명령 테스트
            self._run_command_test(sim_manager)

            # 데이터 수집 테스트
            self._run_data_collection_test(sim_manager)

            # 결과 출력
            self._print_results()

        except KeyboardInterrupt:
            print("\n⚠️ Test interrupted by user")
        except Exception as e:
            print(f"❌ Test error: {e}")
        finally:
            sim_manager.disconnect()
            print("🔌 Simulator disconnected")

        return True

    def _run_basic_test(self, sim_manager):
        """기본 연결 테스트"""
        print("\n📡 Basic Connection Test")
        print("-" * 30)

        # 상태 확인
        if sim_manager.is_connected():
            print("✅ Connection status: OK")
        else:
            print("❌ Connection status: Failed")
            return

        # 간단한 데이터 읽기 테스트
        print("📊 Reading initial data...")
        for i in range(3):
            data = sim_manager.read_data(timeout=2.0)
            if data:
                print(f"  Sample {i+1}: {data[:80]}...")
            else:
                print(f"  Sample {i+1}: No data")
            time.sleep(0.5)

    def _run_command_test(self, sim_manager):
        """명령 테스트"""
        print("\n🎮 Command Test")
        print("-" * 30)

        commands = [
            ('{"cmd":"get_status","seq":100}', "Status query"),
            ('{"cmd":"set_interval","value":500,"seq":101}', "Set interval to 500ms"),
            (
                '{"cmd":"set_mode","value":"LOAD_SPIKE","seq":102}',
                "Set LOAD_SPIKE mode",
            ),
            ('{"cmd":"set_mode","value":"NORMAL","seq":103}', "Set NORMAL mode"),
            ("HELP", "Text command: HELP"),
            ("STATUS", "Text command: STATUS"),
        ]

        for cmd, description in commands:
            print(f"  📤 {description}")
            if sim_manager.send_command(cmd):
                print("    ✅ Command sent")

                # 응답 대기
                response = sim_manager.read_data(timeout=1.0)
                if response:
                    try:
                        resp_data = json.loads(response)
                        if "ack" in resp_data:
                            result = resp_data.get("result", "unknown")
                            print(f"    📥 Response: {result}")
                        else:
                            print(f"    📥 Response: {response[:50]}...")
                    except json.JSONDecodeError:
                        print(f"    📥 Text response: {response[:50]}...")
                else:
                    print("    ⚠️ No response")
            else:
                print("    ❌ Command failed")

            time.sleep(0.5)

    def _run_data_collection_test(self, sim_manager):
        """데이터 수집 테스트"""
        print(f"\n📈 Data Collection Test ({self.duration}s)")
        print("-" * 30)

        start_time = time.time()
        last_print = start_time

        while time.time() - start_time < self.duration:
            data = sim_manager.read_data(timeout=0.1)

            if data:
                try:
                    json_data = json.loads(data)

                    # 측정 데이터인지 확인
                    if all(key in json_data for key in ["v", "a", "w", "seq"]):
                        self._process_measurement_data(json_data)

                except json.JSONDecodeError:
                    pass  # 텍스트 메시지는 무시

            # 1초마다 진행 상황 출력
            current_time = time.time()
            if current_time - last_print >= 1.0:
                elapsed = int(current_time - start_time)
                remaining = self.duration - elapsed
                print(
                    f"  ⏱️ {elapsed:2d}s elapsed, {remaining:2d}s remaining | "
                    f"Data: {self.data_count}, Errors: {self.error_count}"
                )
                last_print = current_time

            time.sleep(0.01)

    def _process_measurement_data(self, data: dict[str, Any]):
        """측정 데이터 처리"""
        self.data_count += 1

        # 시퀀스 번호 확인
        seq = data.get("seq", 0)
        if self.last_sequence >= 0 and seq != self.last_sequence + 1:
            self.error_count += 1
            print(f"    ⚠️ Sequence gap: expected {self.last_sequence + 1}, got {seq}")
        self.last_sequence = seq

        # 데이터 유효성 검사
        voltage = data.get("v", 0)
        current = data.get("a", 0)
        power = data.get("w", 0)

        if voltage < 0 or current < 0 or power < 0:
            self.error_count += 1
            print(f"    ❌ Invalid data: V={voltage}, A={current}, W={power}")
        else:
            # 통계용 데이터 저장
            self.voltage_data.append(voltage)
            self.current_data.append(current)
            self.power_data.append(power)

    def _print_results(self):
        """테스트 결과 출력"""
        print("\n📊 Test Results")
        print("=" * 40)

        elapsed = time.time() - self.start_time
        data_rate = self.data_count / elapsed if elapsed > 0 else 0
        error_rate = (
            (self.error_count / self.data_count * 100) if self.data_count > 0 else 0
        )

        print("📈 Data Statistics:")
        print(f"  Total samples: {self.data_count}")
        print(f"  Error count: {self.error_count}")
        print(f"  Data rate: {data_rate:.1f} samples/sec")
        print(f"  Error rate: {error_rate:.1f}%")

        if self.voltage_data:
            print("\n⚡ Measurement Statistics:")
            print(
                f"  Voltage: {min(self.voltage_data):.3f}V - {max(self.voltage_data):.3f}V "
                f"(avg: {sum(self.voltage_data)/len(self.voltage_data):.3f}V)"
            )
            print(
                f"  Current: {min(self.current_data):.3f}A - {max(self.current_data):.3f}A "
                f"(avg: {sum(self.current_data)/len(self.current_data):.3f}A)"
            )
            print(
                f"  Power: {min(self.power_data):.3f}W - {max(self.power_data):.3f}W "
                f"(avg: {sum(self.power_data)/len(self.power_data):.3f}W)"
            )

        # 결과 평가
        if self.data_count > 0 and error_rate < 5:
            print("\n✅ Test PASSED")
        else:
            print("\n❌ Test FAILED")

    def _on_data(self, data: dict[str, Any]):
        """데이터 콜백 (Mock 시뮬레이터용)"""
        pass  # 이미 read_data()에서 처리

    def _on_status(self, message: str):
        """상태 콜백"""
        print(f"  📢 Status: {message}")

    def _on_connection(self, connected: bool, info: str):
        """연결 상태 콜백"""
        status = "Connected" if connected else "Disconnected"
        print(f"  🔌 {status}: {info}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Arduino Simulator Test")
    parser.add_argument("--mock", action="store_true", help="Use mock simulator only")
    parser.add_argument("--port", default="AUTO", help="Serial port to use")
    parser.add_argument(
        "--duration", type=int, default=30, help="Test duration in seconds"
    )
    parser.add_argument(
        "--list-ports", action="store_true", help="List available ports"
    )

    args = parser.parse_args()

    if args.list_ports:
        list_available_ports()
        return

    port = "MOCK" if args.mock else args.port

    tester = SimulatorTester(port, args.duration)
    success = tester.run_test()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
