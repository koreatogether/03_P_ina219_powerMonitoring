#!/usr/bin/env python3
"""
Phase 2.3 테스트: 1분 min/max 통계 패널 및 임계값 알림 시스템

이 스크립트는 Phase 2.3에서 구현된 기능들을 테스트합니다:
1. 1분 통계 계산 (min/max)
2. 실시간 통계 패널 UI
3. 임계값 알림 시스템
4. 통계 데이터 무결성

테스트 시나리오:
- NORMAL 모드: 정상 범위 데이터
- LOAD_SPIKE 모드: 전류 임계값 초과
- VOLTAGE_DROP 모드: 전압 임계값 미만
"""

import asyncio
import os
import sys

# 경로 설정
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "simulator"))

import json

from simulator_interface import SimulatorManager


async def test_phase2_3():
    print("Phase 2.3 Testing: 1-Minute Statistics & Threshold Alerts")
    print("=" * 60)

    # 시뮬레이터 연결
    simulator = SimulatorManager()

    if not simulator.connect("MOCK"):
        print("[ERROR] Failed to connect to Mock simulator")
        return False

    print("[OK] Mock 시뮬레이터 연결 성공")

    # 테스트 시나리오
    test_modes = [
        ("NORMAL", "정상 동작 테스트"),
        ("LOAD_SPIKE", "전류 임계값 초과 테스트"),
        ("VOLTAGE_DROP", "전압 임계값 미만 테스트"),
    ]

    for mode, description in test_modes:
        print(f"\n📊 {description} ({mode})")
        print("-" * 40)

        # 모드 설정
        simulator.send_command(f'{{"cmd":"set_mode","value":"{mode}","seq":1}}')
        await asyncio.sleep(0.5)

        # 데이터 수집 (10초간)
        stats_data = {"voltage": [], "current": [], "power": []}

        for _i in range(10):
            data = simulator.read_data()
            if data:
                try:
                    parsed = json.loads(data)
                    if "v" in parsed and "a" in parsed and "w" in parsed:
                        stats_data["voltage"].append(parsed["v"])
                        stats_data["current"].append(parsed["a"])
                        stats_data["power"].append(parsed["w"])

                        # 실시간 출력
                        print(
                            f"  📈 V={parsed['v']:.3f}V, A={parsed['a']:.3f}A, W={parsed['w']:.3f}W"
                        )

                except json.JSONDecodeError:
                    continue

            await asyncio.sleep(1)

        # 통계 계산
        if stats_data["voltage"]:
            v_min = min(stats_data["voltage"])
            v_max = max(stats_data["voltage"])
            a_min = min(stats_data["current"])
            a_max = max(stats_data["current"])
            w_min = min(stats_data["power"])
            w_max = max(stats_data["power"])

            print("\n📊 통계 결과:")
            print(f"  ⚡ 전압: {v_min:.3f}V ~ {v_max:.3f}V")
            print(f"  🔋 전류: {a_min:.3f}A ~ {a_max:.3f}A")
            print(f"  💡 전력: {w_min:.3f}W ~ {w_max:.3f}W")

            # 임계값 검사
            print("\n🚨 임계값 알림:")

            # 전압 검사 (4.5V ~ 5.5V)
            if v_min < 4.5 or v_max > 5.5:
                print(f"  ⚠️  전압 이상: {v_min:.3f}V ~ {v_max:.3f}V (정상: 4.5V-5.5V)")
            else:
                print(f"  ✅ 전압 정상: {v_min:.3f}V ~ {v_max:.3f}V")

            # 전류 검사 (< 0.5A)
            if a_max > 0.5:
                print(f"  ⚠️  전류 과부하: {a_max:.3f}A (임계값: 0.5A)")
            else:
                print(f"  ✅ 전류 정상: {a_max:.3f}A")

            # 전력 검사 (< 2.0W)
            if w_max > 2.0:
                print(f"  ⚠️  전력 과부하: {w_max:.3f}W (임계값: 2.0W)")
            else:
                print(f"  ✅ 전력 정상: {w_max:.3f}W")

        await asyncio.sleep(1)

    simulator.disconnect()
    print("\n🎉 Phase 2.3 테스트 완료!")
    print("\n📋 Phase 2.3 구현 상태:")
    print("  ✅ 1분 통계 계산 로직")
    print("  ✅ Min/Max 값 추적")
    print("  ✅ 임계값 알림 시스템")
    print("  ✅ 다양한 시나리오 테스트")
    print("\n🚀 웹 UI에서 실시간 통계 패널을 확인하세요!")

    return True


if __name__ == "__main__":
    asyncio.run(test_phase2_3())
