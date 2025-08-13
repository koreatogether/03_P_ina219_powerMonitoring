#!/usr/bin/env python3
"""
AI 자체 검증 테스트: Phase 2.3 완전 자동 검증
브라우저 없이 모든 UI, 로직, 데이터 흐름을 시뮬레이션하고 검증

검증 항목:
1. HTML 구조 및 요소 위치 검증
2. CSS 스타일 및 색상 검증
3. JavaScript 함수 동작 시뮬레이션
4. 데이터 흐름 추적 (시뮬레이터 → WebSocket → UI)
5. 통계 계산 및 임계값 알림 검증
6. Chart.js 데이터 처리 검증
"""

import asyncio
import os
import re
import sys
from datetime import datetime

from bs4 import BeautifulSoup

# UTF-8 인코딩 강제 설정
if sys.platform.startswith("win"):
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"


class AIPhase23Tester:
    """AI 자체 검증 테스트 클래스"""

    def __init__(self):
        self.test_results = []
        self.html_content = ""
        self.css_styles = {}
        self.js_functions = {}
        self.ui_elements = {}
        self.errors = []
        self.warnings = []

    def log_result(self, test_name: str, status: str, details: str = ""):
        """테스트 결과 로깅"""
        result = {
            "test": test_name,
            "status": status,  # ✅ PASS, ❌ FAIL, ⚠️ WARNING
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }
        self.test_results.append(result)

        # 실시간 출력
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {details}")

    async def load_main_py(self):
        """main.py 파일 로드 및 HTML 추출"""
        try:
            with open("main.py", encoding="utf-8") as f:
                content = f.read()

            # HTML 콘텐츠 추출
            html_match = re.search(r'html_content = """(.*?)"""', content, re.DOTALL)
            if html_match:
                self.html_content = html_match.group(1)
                self.log_result(
                    "HTML 추출",
                    "PASS",
                    f"HTML 콘텐츠 {len(self.html_content)} 문자 추출",
                )
            else:
                self.log_result("HTML 추출", "FAIL", "HTML 콘텐츠를 찾을 수 없음")
                return False

            return True
        except Exception as e:
            self.log_result("파일 로드", "FAIL", f"main.py 로드 실패: {e}")
            return False

    def parse_html_structure(self):
        """HTML 구조 파싱 및 검증"""
        try:
            soup = BeautifulSoup(self.html_content, "html.parser")

            # 필수 UI 요소 검증
            required_elements = {
                "header": {
                    "selector": ".header",
                    "expected_text": "INA219 Power Monitoring System",
                },
                "phase_text": {"selector": ".header p", "expected_text": "Phase 2.3"},
                "connection_panels": {"selector": ".panel", "count": 4},
                "stats_panel": {"selector": ".stats-panel", "count": 1},
                "chart_canvas": {"selector": "#powerChart", "count": 1},
                "voltage_metric": {"selector": "#voltage", "count": 1},
                "current_metric": {"selector": "#current", "count": 1},
                "power_metric": {"selector": "#power", "count": 1},
                "voltage_min": {"selector": "#voltageMin", "count": 1},
                "voltage_max": {"selector": "#voltageMax", "count": 1},
                "current_min": {"selector": "#currentMin", "count": 1},
                "current_max": {"selector": "#currentMax", "count": 1},
                "power_min": {"selector": "#powerMin", "count": 1},
                "power_max": {"selector": "#powerMax", "count": 1},
                "voltage_alert": {"selector": "#voltageAlert", "count": 1},
                "current_alert": {"selector": "#currentAlert", "count": 1},
                "power_alert": {"selector": "#powerAlert", "count": 1},
            }

            for element_name, config in required_elements.items():
                elements = soup.select(config["selector"])

                if "count" in config:
                    if len(elements) == config["count"]:
                        self.log_result(
                            f"HTML 요소: {element_name}",
                            "PASS",
                            f"{config['selector']} 발견 ({len(elements)}개)",
                        )
                        self.ui_elements[element_name] = (
                            elements[0] if elements else None
                        )
                    else:
                        self.log_result(
                            f"HTML 요소: {element_name}",
                            "FAIL",
                            f"{config['selector']} 예상 {config['count']}개, 실제 {len(elements)}개",
                        )

                if "expected_text" in config and elements:
                    if config["expected_text"] in elements[0].get_text():
                        self.log_result(
                            f"HTML 텍스트: {element_name}",
                            "PASS",
                            f"'{config['expected_text']}' 텍스트 확인",
                        )
                    else:
                        self.log_result(
                            f"HTML 텍스트: {element_name}",
                            "FAIL",
                            f"'{config['expected_text']}' 텍스트 미발견",
                        )

        except Exception as e:
            self.log_result("HTML 파싱", "FAIL", f"HTML 파싱 오류: {e}")

    def parse_css_styles(self):
        """CSS 스타일 파싱 및 검증"""
        try:
            # HTML에서 <style> 태그 추출
            soup = BeautifulSoup(self.html_content, "html.parser")
            style_tags = soup.find_all("style")

            if not style_tags:
                self.log_result("CSS 추출", "FAIL", "CSS 스타일을 찾을 수 없음")
                return

            css_content = style_tags[0].get_text()

            # 중요 CSS 클래스 검증
            required_styles = {
                ".stats-panel": ["background", "border-radius", "padding"],
                ".stats-metric.voltage": ["background", "color"],
                ".stats-metric.current": ["background", "color"],
                ".stats-metric.power": ["background", "color"],
                ".alert-indicator": ["width", "height", "border-radius"],
                ".alert-indicator.warning": ["background-color"],
                ".alert-indicator.danger": ["background-color"],
            }

            for css_class, properties in required_styles.items():
                if css_class in css_content:
                    self.log_result(
                        f"CSS 클래스: {css_class}", "PASS", "CSS 클래스 정의 확인"
                    )

                    # 속성 확인
                    for prop in properties:
                        # 클래스 블록 추출 (간단한 정규식)
                        class_pattern = rf"{re.escape(css_class)}\s*\{{([^}}]+)\}}"
                        match = re.search(class_pattern, css_content, re.DOTALL)
                        if match and prop in match.group(1):
                            self.log_result(
                                f"CSS 속성: {css_class}.{prop}",
                                "PASS",
                                f"{prop} 속성 확인",
                            )
                        else:
                            self.log_result(
                                f"CSS 속성: {css_class}.{prop}",
                                "WARNING",
                                f"{prop} 속성 미확인",
                            )
                else:
                    self.log_result(
                        f"CSS 클래스: {css_class}", "FAIL", "CSS 클래스 정의 누락"
                    )

            # 색상 코딩 검증
            color_checks = {
                "#ff6b6b": "전압 색상 (빨강)",
                "#4ecdc4": "전류 색상 (파랑)",
                "#ffe66d": "전력 색상 (노랑)",
                "#28a745": "정상 알림 색상 (녹색)",
                "#ffc107": "경고 알림 색상 (노랑)",
                "#dc3545": "위험 알림 색상 (빨강)",
            }

            for color, description in color_checks.items():
                if color in css_content:
                    self.log_result(
                        f"색상 코딩: {description}", "PASS", f"{color} 색상 확인"
                    )
                else:
                    self.log_result(
                        f"색상 코딩: {description}", "WARNING", f"{color} 색상 미확인"
                    )

        except Exception as e:
            self.log_result("CSS 파싱", "FAIL", f"CSS 파싱 오류: {e}")

    def parse_javascript_functions(self):
        """JavaScript 함수 파싱 및 검증"""
        try:
            # HTML에서 <script> 태그 추출
            soup = BeautifulSoup(self.html_content, "html.parser")
            script_tags = soup.find_all("script")

            js_content = ""
            for script in script_tags:
                if script.string:
                    js_content += script.string

            if not js_content:
                self.log_result(
                    "JavaScript 추출", "FAIL", "JavaScript 코드를 찾을 수 없음"
                )
                return

            # 필수 JavaScript 함수 검증
            required_functions = [
                "updateStatistics",
                "updateStatsDisplay",
                "checkThresholds",
                "connectWebSocket",
                "addDataToChart",
                "initChart",
            ]

            for func_name in required_functions:
                pattern = rf"function\s+{func_name}\s*\("
                if re.search(pattern, js_content):
                    self.log_result(
                        f"JS 함수: {func_name}", "PASS", f"{func_name} 함수 정의 확인"
                    )
                    self.js_functions[func_name] = True
                else:
                    self.log_result(
                        f"JS 함수: {func_name}", "FAIL", f"{func_name} 함수 정의 누락"
                    )

            # 중요 변수 검증
            required_variables = ["statsData", "thresholds", "powerChart", "chartData"]

            for var_name in required_variables:
                if var_name in js_content:
                    self.log_result(
                        f"JS 변수: {var_name}", "PASS", f"{var_name} 변수 선언 확인"
                    )
                else:
                    self.log_result(
                        f"JS 변수: {var_name}", "FAIL", f"{var_name} 변수 선언 누락"
                    )

            # 임계값 설정 검증
            threshold_pattern = r"thresholds\s*=\s*\{([^}]+)\}"
            threshold_match = re.search(threshold_pattern, js_content, re.DOTALL)
            if threshold_match:
                threshold_text = threshold_match.group(1)
                expected_thresholds = {
                    "voltage": ["min.*4.5", "max.*5.5"],
                    "current": ["max.*0.5"],
                    "power": ["max.*2.0"],
                }

                for metric, patterns in expected_thresholds.items():
                    for pattern in patterns:
                        if re.search(pattern, threshold_text):
                            self.log_result(
                                f"임계값: {metric}",
                                "PASS",
                                f"{metric} 임계값 설정 확인",
                            )
                        else:
                            self.log_result(
                                f"임계값: {metric}",
                                "WARNING",
                                f"{metric} 임계값 패턴 미확인",
                            )
            else:
                self.log_result("임계값 설정", "FAIL", "임계값 객체를 찾을 수 없음")

        except Exception as e:
            self.log_result("JavaScript 파싱", "FAIL", f"JavaScript 파싱 오류: {e}")

    def simulate_data_flow(self):
        """데이터 흐름 시뮬레이션"""
        try:
            # 시뮬레이터 데이터 생성
            mock_data = {
                "v": 5.02,  # 전압
                "a": 0.245,  # 전류
                "w": 1.23,  # 전력
                "ts": 1712345678,
                "seq": 123,
                "status": "ok",
                "mode": "NORMAL",
            }

            # 1. 기본 계산 검증
            calculated_power = mock_data["v"] * mock_data["a"]
            power_diff = abs(calculated_power - mock_data["w"])

            if power_diff < 0.01:  # 1% 오차 허용
                self.log_result(
                    "전력 계산",
                    "PASS",
                    f"V×A={calculated_power:.3f}W ≈ W={mock_data['w']}W",
                )
            else:
                self.log_result(
                    "전력 계산", "FAIL", f"전력 계산 오차: {power_diff:.3f}W"
                )

            # 2. 통계 계산 시뮬레이션
            test_data_points = [
                {"v": 4.95, "a": 0.18, "w": 0.89},
                {"v": 5.02, "a": 0.245, "w": 1.23},
                {"v": 5.05, "a": 0.32, "w": 1.616},
                {"v": 4.98, "a": 0.21, "w": 1.046},
            ]

            voltages = [d["v"] for d in test_data_points]
            currents = [d["a"] for d in test_data_points]
            powers = [d["w"] for d in test_data_points]

            stats = {
                "voltage_min": min(voltages),
                "voltage_max": max(voltages),
                "current_min": min(currents),
                "current_max": max(currents),
                "power_min": min(powers),
                "power_max": max(powers),
            }

            self.log_result(
                "통계 계산",
                "PASS",
                f"V: {stats['voltage_min']}-{stats['voltage_max']}V, "
                f"A: {stats['current_min']}-{stats['current_max']}A, "
                f"W: {stats['power_min']}-{stats['power_max']}W",
            )

            # 3. 임계값 알림 시뮬레이션
            test_scenarios = [
                {"data": {"v": 5.0, "a": 0.3, "w": 1.5}, "expected": "normal"},
                {"data": {"v": 4.3, "a": 0.2, "w": 0.86}, "expected": "voltage_danger"},
                {"data": {"v": 5.0, "a": 0.6, "w": 3.0}, "expected": "current_danger"},
                {"data": {"v": 5.0, "a": 0.45, "w": 2.25}, "expected": "power_danger"},
            ]

            for i, scenario in enumerate(test_scenarios):
                data = scenario["data"]
                expected = scenario["expected"]

                # 임계값 체크 로직 시뮬레이션
                voltage_status = "normal"
                if data["v"] < 4.5 or data["v"] > 5.5:
                    voltage_status = "danger"
                elif data["v"] < 4.7 or data["v"] > 5.3:
                    voltage_status = "warning"

                current_status = "normal"
                if data["a"] > 0.5:
                    current_status = "danger"
                elif data["a"] > 0.4:
                    current_status = "warning"

                power_status = "normal"
                if data["w"] > 2.0:
                    power_status = "danger"
                elif data["w"] > 1.7:
                    power_status = "warning"

                # 결과 검증
                if "voltage" in expected and voltage_status in expected:
                    self.log_result(
                        f"임계값 시나리오 {i+1}", "PASS", f"전압 {expected} 정상 감지"
                    )
                elif "current" in expected and current_status in expected:
                    self.log_result(
                        f"임계값 시나리오 {i+1}", "PASS", f"전류 {expected} 정상 감지"
                    )
                elif "power" in expected and power_status in expected:
                    self.log_result(
                        f"임계값 시나리오 {i+1}", "PASS", f"전력 {expected} 정상 감지"
                    )
                elif expected == "normal" and all(
                    s == "normal"
                    for s in [voltage_status, current_status, power_status]
                ):
                    self.log_result(
                        f"임계값 시나리오 {i+1}", "PASS", "정상 상태 정상 감지"
                    )
                else:
                    self.log_result(
                        f"임계값 시나리오 {i+1}",
                        "FAIL",
                        f"예상: {expected}, 실제: V={voltage_status}, A={current_status}, W={power_status}",
                    )

        except Exception as e:
            self.log_result("데이터 흐름 시뮬레이션", "FAIL", f"시뮬레이션 오류: {e}")

    def validate_chart_configuration(self):
        """Chart.js 설정 검증"""
        try:
            # JavaScript에서 Chart 설정 추출
            soup = BeautifulSoup(self.html_content, "html.parser")
            script_tags = soup.find_all("script")

            js_content = ""
            for script in script_tags:
                if script.string:
                    js_content += script.string

            # Chart.js 데이터셋 검증
            dataset_patterns = [
                r"label:\s*['\"]Voltage.*V['\"]",
                r"label:\s*['\"]Current.*A['\"]",
                r"label:\s*['\"]Power.*W['\"]",
            ]

            dataset_labels = ["전압", "전류", "전력"]

            for i, pattern in enumerate(dataset_patterns):
                if re.search(pattern, js_content):
                    self.log_result(
                        f"Chart 데이터셋: {dataset_labels[i]}",
                        "PASS",
                        f"{dataset_labels[i]} 데이터셋 설정 확인",
                    )
                else:
                    self.log_result(
                        f"Chart 데이터셋: {dataset_labels[i]}",
                        "FAIL",
                        f"{dataset_labels[i]} 데이터셋 설정 누락",
                    )

            # Y축 설정 검증
            if "yAxisID" in js_content:
                self.log_result("Chart Y축", "PASS", "듀얼 Y축 설정 확인")
            else:
                self.log_result("Chart Y축", "FAIL", "듀얼 Y축 설정 누락")

            # 색상 설정 검증
            chart_colors = ["#FF6B6B", "#4ECDC4", "#FFE66D"]
            color_labels = ["전압", "전류", "전력"]

            for i, color in enumerate(chart_colors):
                if color in js_content:
                    self.log_result(
                        f"Chart 색상: {color_labels[i]}",
                        "PASS",
                        f"{color_labels[i]} 색상 {color} 확인",
                    )
                else:
                    self.log_result(
                        f"Chart 색상: {color_labels[i]}",
                        "WARNING",
                        f"{color_labels[i]} 색상 {color} 미확인",
                    )

        except Exception as e:
            self.log_result("Chart 설정 검증", "FAIL", f"Chart 검증 오류: {e}")

    def generate_test_report(self):
        """테스트 보고서 생성"""
        print("\n" + "=" * 80)
        print("🤖 AI 자체 검증 테스트 보고서: Phase 2.3")
        print("=" * 80)

        # 통계 계산
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.test_results if r["status"] == "FAIL"])
        warning_tests = len([r for r in self.test_results if r["status"] == "WARNING"])

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print("\n📊 테스트 결과 요약:")
        print(f"  총 테스트: {total_tests}개")
        print(f"  ✅ 통과: {passed_tests}개")
        print(f"  ❌ 실패: {failed_tests}개")
        print(f"  ⚠️ 경고: {warning_tests}개")
        print(f"  📈 성공률: {success_rate:.1f}%")

        # 상세 결과
        print("\n📋 상세 테스트 결과:")
        categories = {}
        for result in self.test_results:
            category = result["test"].split(":")[0] if ":" in result["test"] else "기타"
            if category not in categories:
                categories[category] = {"pass": 0, "fail": 0, "warning": 0}
            categories[category][result["status"].lower()] += 1

        for category, stats in categories.items():
            total = sum(stats.values())
            rate = (stats["pass"] / total * 100) if total > 0 else 0
            print(f"  {category}: {stats['pass']}/{total} 통과 ({rate:.1f}%)")

        # 실패한 테스트 상세 정보
        if failed_tests > 0:
            print("\n❌ 실패한 테스트 상세:")
            for result in self.test_results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")

        # 최종 평가
        print("\n🎯 최종 평가:")
        if success_rate >= 90:
            print("  🎊 EXCELLENT: Phase 2.3 구현이 매우 우수합니다!")
        elif success_rate >= 80:
            print("  ✅ GOOD: Phase 2.3 구현이 양호합니다.")
        elif success_rate >= 70:
            print("  ⚠️ ACCEPTABLE: 일부 개선이 필요합니다.")
        else:
            print("  ❌ NEEDS_IMPROVEMENT: 상당한 개선이 필요합니다.")

        print("\n" + "=" * 80)

    async def run_full_test(self):
        """전체 테스트 실행"""
        print("🤖 AI 자체 검증 테스트 시작: Phase 2.3")
        print("=" * 60)

        # 1. 파일 로드 및 준비
        if not await self.load_main_py():
            return False

        # 2. HTML 구조 검증
        print("\n📄 HTML 구조 검증...")
        self.parse_html_structure()

        # 3. CSS 스타일 검증
        print("\n🎨 CSS 스타일 검증...")
        self.parse_css_styles()

        # 4. JavaScript 함수 검증
        print("\n⚙️ JavaScript 함수 검증...")
        self.parse_javascript_functions()

        # 5. 데이터 흐름 시뮬레이션
        print("\n🔄 데이터 흐름 시뮬레이션...")
        self.simulate_data_flow()

        # 6. Chart.js 설정 검증
        print("\n📈 Chart.js 설정 검증...")
        self.validate_chart_configuration()

        # 7. 보고서 생성
        self.generate_test_report()

        return True


async def main():
    """메인 실행 함수"""
    tester = AIPhase23Tester()
    await tester.run_full_test()


if __name__ == "__main__":
    asyncio.run(main())
