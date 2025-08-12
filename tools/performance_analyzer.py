#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Performance Analyzer
전력 모니터링 시스템의 성능 분석 도구

분석 항목:
- 데이터 수집 성능 측정
- 대시보드 응답 시간 분석
- 메모리 사용량 분석
- 전력 측정 정확도 검증
- Arduino 통신 성능 측정
"""

import os
import subprocess
import sys
import time
import statistics
from datetime import datetime
from pathlib import Path
import json
import psutil


class PowerMonitoringPerformanceAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.log_dir = self.project_root / "logs" / "performance"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 성능 테스트 설정
        self.test_iterations = 100
        self.warmup_iterations = 10
        
        # 결과 저장
        self.results = {
            "timestamp": self.timestamp,
            "test_config": {
                "iterations": self.test_iterations,
                "warmup_iterations": self.warmup_iterations
            },
            "performance": {},
            "system_info": self.get_system_info()
        }
    
    def get_system_info(self):
        """시스템 정보 수집"""
        return {
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "python_version": sys.version,
            "platform": sys.platform
        }
    
    def run_command_with_timing(self, cmd, desc, cwd=None, iterations=1):
        """명령어 실행 시간 측정"""
        print(f"⏱️  {desc} (반복: {iterations}회)")
        
        times = []
        outputs = []
        memory_usage = []
        
        for i in range(iterations):
            try:
                # 메모리 사용량 측정 시작
                process = psutil.Process()
                memory_before = process.memory_info().rss
                
                start_time = time.perf_counter()
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=cwd or self.project_root,
                    timeout=30,
                    encoding='utf-8',
                    errors='replace'
                )
                end_time = time.perf_counter()
                
                # 메모리 사용량 측정 종료
                memory_after = process.memory_info().rss
                memory_diff = memory_after - memory_before
                
                execution_time = end_time - start_time
                times.append(execution_time)
                memory_usage.append(memory_diff)
                
                if result.returncode == 0:
                    outputs.append(result.stdout.strip())
                else:
                    print(f"    ❌ 실행 실패 (반복 {i+1}): {result.stderr}")
                    return None
                    
            except subprocess.TimeoutExpired:
                print(f"    ⏰ 타임아웃 (반복 {i+1})")
                return None
            except Exception as e:
                print(f"    ❌ 오류 (반복 {i+1}): {e}")
                return None
        
        if not times:
            return None
            
        return {
            "times": times,
            "outputs": outputs,
            "memory_usage": memory_usage,
            "avg_time": statistics.mean(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_memory": statistics.mean(memory_usage) if memory_usage else 0,
            "success_rate": len(times) / iterations
        }
    
    def analyze_data_processing_performance(self):
        """데이터 처리 성능 분석"""
        print("\n📊 데이터 처리 성능 분석")
        print("-" * 30)
        
        data_processing_dir = self.project_root / "src" / "python" / "data_processing"
        if not data_processing_dir.exists():
            self.results["performance"]["data_processing"] = {
                "status": "skipped", 
                "reason": "No data processing module found"
            }
            return
        
        # 데이터 처리 스크립트 찾기
        processing_files = list(data_processing_dir.glob("*.py"))
        if not processing_files:
            self.results["performance"]["data_processing"] = {
                "status": "skipped", 
                "reason": "No data processing files found"
            }
            return
        
        processing_results = {}
        
        for py_file in processing_files:
            if py_file.name.startswith("test_") or py_file.name == "__init__.py":
                continue
                
            print(f"  📊 분석 중: {py_file.name}")
            
            # 워밍업
            warmup_result = self.run_command_with_timing(
                f"python -m uv run python {py_file}",
                f"워밍업 {py_file.name}",
                iterations=self.warmup_iterations
            )
            
            if warmup_result is None:
                processing_results[py_file.name] = {"status": "failed", "reason": "Warmup failed"}
                continue
            
            # 실제 성능 측정
            perf_result = self.run_command_with_timing(
                f"python -m uv run python {py_file}",
                f"성능 측정 {py_file.name}",
                iterations=self.test_iterations
            )
            
            if perf_result is None:
                processing_results[py_file.name] = {"status": "failed", "reason": "Performance test failed"}
                continue
            
            processing_results[py_file.name] = {
                "performance": perf_result,
                "status": "success"
            }
            
            print(f"    ✅ 평균 실행시간: {perf_result['avg_time']:.6f}초")
            print(f"    💾 평균 메모리 사용: {perf_result['avg_memory']/1024/1024:.2f}MB")
        
        self.results["performance"]["data_processing"] = processing_results
    
    def analyze_dashboard_performance(self):
        """대시보드 성능 분석"""
        print("\n📈 대시보드 성능 분석")
        print("-" * 30)
        
        dashboard_dir = self.project_root / "src" / "python" / "dashboard"
        if not dashboard_dir.exists():
            self.results["performance"]["dashboard"] = {
                "status": "skipped", 
                "reason": "No dashboard directory found"
            }
            return
        
        # 대시보드 앱 파일 찾기
        app_files = list(dashboard_dir.glob("app.py")) + list(dashboard_dir.glob("main.py"))
        
        if not app_files:
            self.results["performance"]["dashboard"] = {
                "status": "skipped", 
                "reason": "No dashboard app file found"
            }
            return
        
        app_file = app_files[0]
        print(f"  📊 대시보드 로딩 성능 테스트: {app_file.name}")
        
        # 대시보드 임포트 성능 측정
        test_script = f"""
import time
import sys
sys.path.insert(0, '{dashboard_dir}')

start_time = time.perf_counter()
try:
    import {app_file.stem}
    end_time = time.perf_counter()
    print(f"Import time: {{end_time - start_time:.6f}} seconds")
except Exception as e:
    print(f"Import failed: {{e}}")
    sys.exit(1)
"""
        
        # 워밍업
        warmup_result = self.run_command_with_timing(
            f"python -m uv run python -c \"{test_script}\"",
            f"대시보드 임포트 워밍업",
            iterations=self.warmup_iterations
        )
        
        if warmup_result is None:
            self.results["performance"]["dashboard"] = {"status": "failed", "reason": "Warmup failed"}
            return
        
        # 실제 성능 측정
        perf_result = self.run_command_with_timing(
            f"python -m uv run python -c \"{test_script}\"",
            f"대시보드 임포트 성능 측정",
            iterations=self.test_iterations
        )
        
        if perf_result is None:
            self.results["performance"]["dashboard"] = {"status": "failed", "reason": "Performance test failed"}
            return
        
        self.results["performance"]["dashboard"] = {
            "performance": perf_result,
            "status": "success"
        }
        
        print(f"    ✅ 평균 임포트 시간: {perf_result['avg_time']:.6f}초")
        print(f"    💾 평균 메모리 사용: {perf_result['avg_memory']/1024/1024:.2f}MB")
    
    def analyze_serial_communication_performance(self):
        """시리얼 통신 성능 분석 (시뮬레이션)"""
        print("\n📡 시리얼 통신 성능 분석")
        print("-" * 30)
        
        # 시리얼 통신 시뮬레이션 스크립트 생성
        serial_test_script = """
import time
import random

# INA219 데이터 시뮬레이션
def simulate_ina219_reading():
    voltage = round(random.uniform(3.0, 5.0), 3)
    current = round(random.uniform(0.0, 1000.0), 2)
    power = round(voltage * current / 1000, 3)
    return f"V:{voltage},I:{current},P:{power}"

# 시뮬레이션 실행
start_time = time.perf_counter()
readings = []
for i in range(100):
    reading = simulate_ina219_reading()
    readings.append(reading)
    time.sleep(0.001)  # 1ms 지연 시뮬레이션

end_time = time.perf_counter()
print(f"Readings: {len(readings)}")
print(f"Time: {end_time - start_time:.6f} seconds")
print(f"Rate: {len(readings)/(end_time - start_time):.2f} readings/sec")
"""
        
        # 임시 스크립트 파일 생성
        temp_script = self.project_root / "temp_serial_test.py"
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(serial_test_script)
        
        try:
            print("  📊 시리얼 통신 시뮬레이션 테스트")
            
            # 워밍업
            warmup_result = self.run_command_with_timing(
                f"python -m uv run python {temp_script}",
                "시리얼 통신 워밍업",
                iterations=self.warmup_iterations
            )
            
            if warmup_result is None:
                self.results["performance"]["serial_communication"] = {"status": "failed", "reason": "Warmup failed"}
                return
            
            # 실제 성능 측정
            perf_result = self.run_command_with_timing(
                f"python -m uv run python {temp_script}",
                "시리얼 통신 성능 측정",
                iterations=self.test_iterations
            )
            
            if perf_result is None:
                self.results["performance"]["serial_communication"] = {"status": "failed", "reason": "Performance test failed"}
                return
            
            self.results["performance"]["serial_communication"] = {
                "performance": perf_result,
                "status": "success"
            }
            
            print(f"    ✅ 평균 실행시간: {perf_result['avg_time']:.6f}초")
            print(f"    💾 평균 메모리 사용: {perf_result['avg_memory']/1024/1024:.2f}MB")
            
        finally:
            # 임시 파일 삭제
            if temp_script.exists():
                temp_script.unlink()
    
    def generate_performance_report(self):
        """성능 분석 리포트 생성"""
        print("\n📊 성능 분석 요약")
        print("-" * 30)
        
        summary = {
            "total_tests": 0,
            "successful_tests": 0,
            "average_times": {},
            "memory_usage": {}
        }
        
        # 성능 데이터 수집
        for component, results in self.results["performance"].items():
            if isinstance(results, dict) and results.get("status") == "success":
                if "performance" in results:
                    perf_data = results["performance"]
                    summary["total_tests"] += 1
                    summary["successful_tests"] += 1
                    summary["average_times"][component] = perf_data["avg_time"]
                    summary["memory_usage"][component] = perf_data.get("avg_memory", 0)
                else:
                    # 여러 파일 결과인 경우
                    for file_name, file_result in results.items():
                        if isinstance(file_result, dict) and file_result.get("status") == "success":
                            perf_data = file_result["performance"]
                            summary["total_tests"] += 1
                            summary["successful_tests"] += 1
                            summary["average_times"][f"{component}_{file_name}"] = perf_data["avg_time"]
                            summary["memory_usage"][f"{component}_{file_name}"] = perf_data.get("avg_memory", 0)
            else:
                summary["total_tests"] += 1
        
        self.results["summary"] = summary
        
        # 결과 출력
        if summary["average_times"]:
            print("\n🏆 성능 순위 (실행 시간):")
            sorted_times = sorted(summary["average_times"].items(), key=lambda x: x[1])
            for i, (component, avg_time) in enumerate(sorted_times, 1):
                print(f"    {i}. {component}: {avg_time*1000:.3f}ms")
            
            print("\n💾 메모리 사용량:")
            for component, memory in summary["memory_usage"].items():
                if memory > 0:
                    print(f"    {component}: {memory/1024/1024:.2f}MB")
        else:
            print("  ❌ 분석할 성능 데이터가 없습니다.")
    
    def save_results(self):
        """분석 결과 저장"""
        # JSON 결과 저장
        json_file = self.log_dir / f"performance_analysis_{self.timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        # 텍스트 리포트 저장
        text_file = self.log_dir / f"performance_report_{self.timestamp}.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write("INA219 Power Monitoring - Performance Analysis Report\n")
            f.write("=" * 60 + "\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Test Iterations: {self.test_iterations}\n")
            f.write(f"Warmup Iterations: {self.warmup_iterations}\n\n")
            
            # 시스템 정보
            f.write("SYSTEM INFO:\n")
            f.write("-" * 20 + "\n")
            f.write(json.dumps(self.results["system_info"], indent=2, ensure_ascii=False))
            f.write("\n\n")
            
            # 컴포넌트별 결과
            for component, results in self.results["performance"].items():
                f.write(f"\n{component.upper()} RESULTS:\n")
                f.write("-" * 30 + "\n")
                f.write(json.dumps(results, indent=2, ensure_ascii=False, default=str))
                f.write("\n")
        
        print(f"\n📝 결과 저장됨:")
        print(f"  📄 JSON: {json_file}")
        print(f"  📄 리포트: {text_file}")
    
    def run_analysis(self):
        """전체 성능 분석 실행"""
        print("🚀 INA219 Power Monitoring 성능 분석 시작")
        print("-" * 60)
        
        # 각 컴포넌트별 성능 분석
        self.analyze_data_processing_performance()
        self.analyze_dashboard_performance()
        self.analyze_serial_communication_performance()
        
        # 성능 리포트 생성
        self.generate_performance_report()
        
        # 결과 저장
        self.save_results()


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    analyzer = PowerMonitoringPerformanceAnalyzer(project_root)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()