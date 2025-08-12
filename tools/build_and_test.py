#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Build and Test Automation
다중 언어 프로젝트를 위한 빌드 및 테스트 자동화 도구

기능:
- Arduino 프로젝트 컴파일 (PlatformIO)
- Python 코드 테스트 실행
- Dash 대시보드 테스트
- 성능 벤치마크 실행
- 결과 로깅 및 리포트 생성
"""

import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
import json


class MultiLanguageBuildTester:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.log_dir = self.project_root / "logs" / "build_test"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 빌드 및 테스트 결과
        self.results = {
            "timestamp": self.timestamp,
            "builds": {},
            "tests": {},
            "benchmarks": {}
        }
        
    def run_command(self, cmd, desc, cwd=None, timeout=300):
        """명령어 실행 및 결과 반환"""
        print(f"🔧 {desc}...")
        
        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=cwd or self.project_root,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )
            end_time = time.time()
            
            return {
                "command": cmd,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "duration": end_time - start_time,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "command": cmd,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "duration": timeout,
                "success": False
            }
        except Exception as e:
            return {
                "command": cmd,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "duration": 0,
                "success": False
            }
    
    def build_arduino(self):
        """Arduino 프로젝트 빌드 (PlatformIO)"""
        print("\n🔨 Arduino 프로젝트 빌드")
        print("-" * 30)
        
        # PlatformIO 설치 확인
        pio_check = self.run_command("pio --version", "PlatformIO 버전 확인")
        if not pio_check["success"]:
            self.results["builds"]["arduino"] = {
                "status": "failed",
                "reason": "PlatformIO not installed",
                "message": "Install PlatformIO: python -m uv add platformio"
            }
            return
        
        # 각 환경별 빌드
        environments = ["uno", "nano", "esp32"]
        build_results = {}
        
        for env in environments:
            print(f"  📦 빌드 중: {env}")
            result = self.run_command(f"pio run -e {env}", f"Build {env} environment")
            build_results[env] = result
            
            if result["success"]:
                print(f"    ✅ {env} 빌드 성공")
            else:
                print(f"    ❌ {env} 빌드 실패")
                
        self.results["builds"]["arduino"] = build_results
    
    def test_python(self):
        """Python 코드 테스트"""
        print("\n🐍 Python 코드 테스트")
        print("-" * 30)
        
        python_src = self.project_root / "src" / "python"
        if not python_src.exists():
            self.results["tests"]["python"] = {
                "status": "skipped",
                "reason": "No Python source directory found"
            }
            return
        
        # pytest 실행
        test_dir = self.project_root / "tests"
        if test_dir.exists():
            result = self.run_command(
                "python -m uv run pytest tests/ -v --tb=short",
                "Python 단위 테스트 실행"
            )
            self.results["tests"]["python"] = result
        else:
            # 기본 Python 파일 실행 테스트
            python_files = list(python_src.rglob("*.py"))
            test_results = {}
            
            for py_file in python_files:
                if py_file.name.startswith("test_") or py_file.name == "__init__.py":
                    continue
                    
                print(f"  🧪 테스트 중: {py_file.name}")
                result = self.run_command(
                    f"python -m uv run python {py_file}",
                    f"Run {py_file.name}",
                    timeout=30
                )
                test_results[py_file.name] = result
                
                if result["success"]:
                    print(f"    ✅ {py_file.name} 실행 성공")
                else:
                    print(f"    ❌ {py_file.name} 실행 실패")
                    
            self.results["tests"]["python"] = test_results
    
    def test_dash_dashboard(self):
        """Dash 대시보드 테스트"""
        print("\n📊 Dash 대시보드 테스트")
        print("-" * 30)
        
        dashboard_dir = self.project_root / "src" / "python" / "dashboard"
        if not dashboard_dir.exists():
            self.results["tests"]["dashboard"] = {
                "status": "skipped",
                "reason": "No dashboard directory found"
            }
            return
        
        # 대시보드 앱 파일 찾기
        app_files = list(dashboard_dir.glob("app.py")) + list(dashboard_dir.glob("main.py"))
        
        if not app_files:
            self.results["tests"]["dashboard"] = {
                "status": "skipped",
                "reason": "No dashboard app file found"
            }
            return
        
        # 대시보드 임포트 테스트
        app_file = app_files[0]
        print(f"  🧪 대시보드 임포트 테스트: {app_file.name}")
        
        # 임포트만 테스트 (실제 실행은 하지 않음)
        test_script = f"""
import sys
sys.path.insert(0, '{dashboard_dir}')
try:
    import {app_file.stem}
    print("Dashboard import successful")
except Exception as e:
    print(f"Dashboard import failed: {{e}}")
    sys.exit(1)
"""
        
        result = self.run_command(
            f"python -m uv run python -c \"{test_script}\"",
            "Dashboard import test",
            timeout=30
        )
        
        self.results["tests"]["dashboard"] = result
        
        if result["success"]:
            print("    ✅ 대시보드 임포트 성공")
        else:
            print("    ❌ 대시보드 임포트 실패")
    
    def run_benchmarks(self):
        """성능 벤치마크 실행"""
        print("\n📊 성능 벤치마크 실행")
        print("-" * 30)
        
        benchmark_dir = self.project_root / "benchmarks"
        if not benchmark_dir.exists():
            self.results["benchmarks"] = {
                "status": "skipped",
                "reason": "No benchmarks directory found"
            }
            return
        
        # 벤치마크 스크립트 찾기 및 실행
        benchmark_files = list(benchmark_dir.glob("*.py"))
        benchmark_results = {}
        
        for benchmark_file in benchmark_files:
            print(f"  📈 벤치마크 실행: {benchmark_file.name}")
            
            result = self.run_command(
                f"python -m uv run python {benchmark_file}",
                f"Run benchmark {benchmark_file.name}",
                timeout=60
            )
            benchmark_results[benchmark_file.name] = result
            
            if result["success"]:
                print(f"    ✅ {benchmark_file.name} 완료")
            else:
                print(f"    ❌ {benchmark_file.name} 실패")
                
        self.results["benchmarks"] = benchmark_results
    
    def generate_report(self):
        """빌드 및 테스트 리포트 생성"""
        # JSON 결과 저장
        json_report = self.log_dir / f"build_test_report_{self.timestamp}.json"
        with open(json_report, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        
        # 텍스트 요약 리포트 생성
        text_report = self.log_dir / f"build_test_summary_{self.timestamp}.txt"
        with open(text_report, 'w', encoding='utf-8') as f:
            f.write("INA219 Power Monitoring - Build & Test Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {self.timestamp}\n\n")
            
            # 빌드 결과 요약
            f.write("BUILD RESULTS:\n")
            f.write("-" * 20 + "\n")
            for platform, result in self.results["builds"].items():
                if isinstance(result, dict) and "status" in result:
                    f.write(f"{platform}: {result['status']}\n")
                elif isinstance(result, dict):
                    success_count = sum(1 for r in result.values() if isinstance(r, dict) and r.get("success", False))
                    total_count = len([r for r in result.values() if isinstance(r, dict)])
                    f.write(f"{platform}: {success_count}/{total_count} successful\n")
            
            # 테스트 결과 요약
            f.write("\nTEST RESULTS:\n")
            f.write("-" * 20 + "\n")
            for platform, result in self.results["tests"].items():
                if isinstance(result, dict) and "status" in result:
                    f.write(f"{platform}: {result['status']}\n")
                elif isinstance(result, dict) and "success" in result:
                    status = "PASS" if result["success"] else "FAIL"
                    f.write(f"{platform}: {status}\n")
                elif isinstance(result, dict):
                    success_count = sum(1 for r in result.values() if isinstance(r, dict) and r.get("success", False))
                    total_count = len([r for r in result.values() if isinstance(r, dict)])
                    f.write(f"{platform}: {success_count}/{total_count} successful\n")
        
        print(f"\n📝 리포트 저장됨:")
        print(f"  📄 JSON: {json_report}")
        print(f"  📄 요약: {text_report}")
    
    def print_summary(self):
        """빌드 및 테스트 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("🎯 빌드 및 테스트 결과 요약")
        print("=" * 60)
        
        # 빌드 결과
        print("\n🔨 빌드 결과:")
        for platform, result in self.results["builds"].items():
            if isinstance(result, dict) and "status" in result:
                status_icon = "⏭️" if result["status"] == "skipped" else "❌"
                print(f"  {platform}: {status_icon} {result['status']}")
            elif isinstance(result, dict):
                success_count = sum(1 for r in result.values() if isinstance(r, dict) and r.get("success", False))
                total_count = len([r for r in result.values() if isinstance(r, dict)])
                status_icon = "✅" if success_count == total_count else "⚠️"
                print(f"  {platform}: {status_icon} {success_count}/{total_count} 성공")
        
        # 테스트 결과
        print("\n🧪 테스트 결과:")
        for platform, result in self.results["tests"].items():
            if isinstance(result, dict) and "status" in result:
                status_icon = "⏭️" if result["status"] == "skipped" else "❌"
                print(f"  {platform}: {status_icon} {result['status']}")
            elif isinstance(result, dict) and "success" in result:
                status_icon = "✅" if result["success"] else "❌"
                print(f"  {platform}: {status_icon} {'성공' if result['success'] else '실패'}")
            elif isinstance(result, dict):
                success_count = sum(1 for r in result.values() if isinstance(r, dict) and r.get("success", False))
                total_count = len([r for r in result.values() if isinstance(r, dict)])
                status_icon = "✅" if success_count == total_count else "⚠️"
                print(f"  {platform}: {status_icon} {success_count}/{total_count} 성공")
        
        # 벤치마크 결과
        print("\n📊 벤치마크 결과:")
        if isinstance(self.results["benchmarks"], dict) and "status" in self.results["benchmarks"]:
            status_icon = "⏭️" if self.results["benchmarks"]["status"] == "skipped" else "❌"
            print(f"  벤치마크: {status_icon} {self.results['benchmarks']['status']}")
        elif isinstance(self.results["benchmarks"], dict):
            success_count = sum(1 for r in self.results["benchmarks"].values() 
                              if isinstance(r, dict) and r.get("success", False))
            total_count = len([r for r in self.results["benchmarks"].values() 
                             if isinstance(r, dict)])
            if total_count > 0:
                status_icon = "✅" if success_count == total_count else "⚠️"
                print(f"  벤치마크: {status_icon} {success_count}/{total_count} 성공")
            else:
                print(f"  벤치마크: ⏭️ 없음")
    
    def run_all(self):
        """모든 빌드 및 테스트 실행"""
        print("🚀 INA219 Power Monitoring 프로젝트 빌드 및 테스트 시작")
        print("-" * 60)
        
        # 빌드 실행
        self.build_arduino()
        
        # 테스트 실행
        self.test_python()
        self.test_dash_dashboard()
        
        # 벤치마크 실행
        self.run_benchmarks()
        
        # 결과 저장 및 출력
        self.generate_report()
        self.print_summary()


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    tester = MultiLanguageBuildTester(project_root)
    tester.run_all()


if __name__ == "__main__":
    main()