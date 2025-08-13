"""
Arduino INA219 Simulator Package
Arduino UNO R4 WiFi + INA219 시뮬레이터 패키지

이 패키지는 실제 Arduino 하드웨어 없이도 INA219 전력 모니터링 시스템을
개발하고 테스트할 수 있는 시뮬레이터를 제공합니다.

주요 구성요소:
- ArduinoMockSimulator: Python 기반 Mock 시뮬레이터
- SimulatorManager: 실제/Mock 시뮬레이터 통합 관리
- 테스트 도구 및 데모 스크립트

사용 예시:
    from simulator import create_simulator

    # 자동 감지 (실제 Arduino 우선, Mock 폴백)
    sim = create_simulator("AUTO")

    if sim.connect():
        # 데이터 읽기
        data = sim.read_data()
        print(data)

        # 명령 전송
        sim.send_command('{"cmd":"get_status","seq":1}')

        sim.disconnect()
"""

from .arduino_mock import ArduinoMockSimulator, SimulationMode
from .simulator_interface import (
    SimulatorConfig,
    SimulatorManager,
    create_simulator,
    list_available_ports,
)

__version__ = "1.0.0"
__author__ = "INA219 Monitoring System"

# 패키지 레벨에서 사용할 수 있는 주요 클래스/함수들
__all__ = [
    # 시뮬레이터 클래스들
    "ArduinoMockSimulator",
    "SimulatorManager",
    "SimulatorConfig",
    "SimulationMode",
    # 편의 함수들
    "create_simulator",
    "list_available_ports",
    # 상수들
    "__version__",
]


# 패키지 초기화 메시지
def get_package_info():
    """패키지 정보 반환"""
    return {
        "name": "Arduino INA219 Simulator",
        "version": __version__,
        "description": "Arduino UNO R4 WiFi + INA219 Power Monitoring Simulator",
        "features": [
            "Mock Arduino simulation",
            "Real serial communication",
            "JSON protocol support",
            "Multiple simulation modes",
            "Auto-detection and fallback",
            "Data integrity checking",
        ],
    }


def print_package_info():
    """패키지 정보 출력"""
    info = get_package_info()
    print(f"=== {info['name']} v{info['version']} ===")
    print(info["description"])
    print("\nFeatures:")
    for feature in info["features"]:
        print(f"  • {feature}")
    print()


# 개발자 편의를 위한 빠른 시작 함수
def quick_start(port="AUTO", duration=10):
    """빠른 시작 데모"""
    print("🚀 Quick Start Demo")
    print("-" * 30)

    sim = create_simulator(port)

    if sim.connect():
        print(f"✅ Connected using {sim.get_simulator_type()} simulator")

        import json
        import time

        start_time = time.time()
        data_count = 0

        print(f"📊 Collecting data for {duration} seconds...")

        while time.time() - start_time < duration:
            data = sim.read_data(timeout=0.5)
            if data:
                try:
                    json_data = json.loads(data)
                    if "v" in json_data and "a" in json_data and "w" in json_data:
                        data_count += 1
                        if data_count % 5 == 0:  # 5개마다 출력
                            print(
                                f"  📈 V={json_data['v']:.3f}V, "
                                f"A={json_data['a']:.3f}A, "
                                f"W={json_data['w']:.3f}W"
                            )
                except json.JSONDecodeError:
                    pass

            time.sleep(0.1)

        print(f"✅ Collected {data_count} data samples")
        sim.disconnect()
    else:
        print("❌ Failed to connect to simulator")


# 패키지 임포트 시 정보 출력 (선택적)
if __name__ == "__main__":
    print_package_info()
    quick_start()
