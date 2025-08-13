#!/usr/bin/env python3
"""
INA219 전력 모니터링 시스템 - 코드 품질 검사 도구
====================================================
INA219 프로젝트에 특화된 통합 코드 품질 검사 도구

지원 언어:
- Arduino C++ (.ino, .cpp, .h) - INA219 센서 코드 특화 검사
- Python (.py) - FastAPI, 데이터 분석, WebSocket 코드 검사
- JavaScript (.js) - Chart.js, 웹 대시보드 코드 검사

INA219 특화 검사 항목:
- INA219 센서 초기화 및 에러 처리
- 전력 측정 단위 표시 (V, mA, W)
- WebSocket 실시간 통신 품질
- 데이터베이스 연결 안정성
- Docker 설정 최적화
- 보안 취약점 (하드코딩된 비밀번호 등)

일반 검사 항목:
- 코드 스타일 및 포맷팅 (Ruff, Black)
- 타입 힌트 검사 (MyPy)
- 잠재적 버그 및 보안 이슈
- 성능 최적화 제안
- 문서화 품질

작성: INA219 프로젝트 팀
버전: 2.0.0 (2025-08-13)
"""

import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
import json


class MultiLanguageQualityChecker:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.log_dir = self.project_root / "logs" / "quality"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 언어별 파일 확장자
        self.language_extensions = {
            'arduino': ['.ino', '.cpp', '.h'],
            'python': ['.py'],
            'javascript': ['.js']
        }
        
        # 검사 결과 저장
        self.results = {}
        
    def find_source_files(self):
        """프로젝트에서 소스 파일들을 찾아 언어별로 분류"""
        files_by_language = {lang: [] for lang in self.language_extensions}
        
        src_dir = self.project_root / "src"
        if not src_dir.exists():
            print("❌ src 디렉토리가 존재하지 않습니다.")
            return files_by_language
        
        print(f"소스 파일 검색 중: {src_dir}")
        
        # 각 언어별 확장자로 파일 검색
        for lang, extensions in self.language_extensions.items():
            for ext in extensions:
                found_files = list(src_dir.rglob(f"*{ext}"))
                files_by_language[lang].extend(found_files)
                
        # 검색 결과 출력
        total_files = 0
        for lang, files in files_by_language.items():
            if files:
                print(f"  {lang}: {len(files)}개 파일 발견")
                for file in files[:3]:
                    print(f"    - {file.relative_to(self.project_root)}")
                if len(files) > 3:
                    print(f"    ... 및 {len(files) - 3}개 파일 더")
                total_files += len(files)
            else:
                print(f"  {lang}: 파일 없음")
                
        print(f"  총 {total_files}개 소스 파일 발견")
        return files_by_language
    
    def auto_fix_python_files(self, python_files):
        """Python 파일 자동 수정"""
        if not python_files:
            return {"status": "skipped", "reason": "No Python files found"}
            
        print("Python 파일 자동 수정 중...")
        results = {}
        
        # Ruff auto-fix
        try:
            cmd = ["python", "-m", "uv", "run", "ruff", "check", "--fix"] + [str(f) for f in python_files]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            stdout = result.stdout if result.stdout is not None else ""
            results["ruff_autofix"] = {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": result.stderr,
                "fixed_count": len([line for line in stdout.split('\n') if 'fixed' in line.lower()])
            }
            if results["ruff_autofix"]["fixed_count"] > 0:
                print(f"   Ruff가 {results['ruff_autofix']['fixed_count']}개 문제를 자동 수정했습니다.")
        except FileNotFoundError:
            results["ruff_autofix"] = {"status": "not_installed", "message": "uv add ruff"}
            
        # Black auto-format
        try:
            cmd = ["python", "-m", "uv", "run", "black"] + [str(f) for f in python_files]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            stdout = result.stdout if result.stdout is not None else ""
            results["black_format"] = {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": result.stderr,
                "formatted": result.returncode == 0
            }
            formatted_files = [line for line in stdout.split('\n') if 'reformatted' in line]
            if formatted_files:
                print(f"   Black이 {len(formatted_files)}개 파일을 포맷했습니다.")
        except FileNotFoundError:
            results["black_format"] = {"status": "not_installed", "message": "uv add black"}
            
        return results

    def check_python_quality(self, python_files):
        """Python 코드 품질 검사 (INA219 프로젝트 특화)"""
        if not python_files:
            return {"status": "skipped", "reason": "No Python files found"}
            
        print("Python 코드 품질 검사 중...")
        results = {}
        
        # Ruff 검사
        try:
            cmd = ["python", "-m", "uv", "run", "ruff", "check"] + [str(f) for f in python_files]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            stdout = result.stdout if result.stdout is not None else ""
            results["ruff"] = {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": result.stderr,
                "issues_count": len([line for line in stdout.split('\n') if line.strip() and ':' in line])
            }
        except FileNotFoundError:
            results["ruff"] = {"status": "not_installed", "message": "pip install ruff"}
            
        # MyPy 타입 검사
        try:
            cmd = ["python", "-m", "uv", "run", "mypy", "--ignore-missing-imports"] + [str(f) for f in python_files]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            stdout = result.stdout if result.stdout is not None else ""
            results["mypy"] = {
                "returncode": result.returncode,
                "stdout": stdout,
                "stderr": result.stderr,
                "issues_count": len([line for line in stdout.split('\n') if 'error:' in line])
            }
        except FileNotFoundError:
            results["mypy"] = {"status": "not_installed", "message": "pip install mypy"}
        
        # INA219 프로젝트 특화 Python 검사
        ina219_results = self.ina219_python_analysis(python_files)
        results["ina219_analysis"] = ina219_results
            
        return results
    
    def ina219_python_analysis(self, python_files):
        """INA219 프로젝트 특화 Python 분석"""
        issues = []
        recommendations = []
        security_issues = []
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # FastAPI 관련 검사
                    has_fastapi = 'from fastapi import' in content or 'import fastapi' in content
                    has_websocket = 'WebSocket' in content or 'websocket' in content.lower()
                    has_database = 'sqlite' in content.lower() or 'database' in content.lower()
                    has_data_analysis = 'numpy' in content or 'pandas' in content
                    
                    for i, line in enumerate(lines, 1):
                        line_clean = line.strip()
                        line_lower = line_clean.lower()
                        
                        # FastAPI 보안 검사
                        if has_fastapi:
                            if 'app = FastAPI(' in line_clean and 'docs_url=None' not in content:
                                recommendations.append(f"{file_path}:{i}: Consider disabling docs in production (docs_url=None)")
                            
                            if '@app.on_event(' in line_clean:
                                recommendations.append(f"{file_path}:{i}: @app.on_event is deprecated, use lifespan events")
                        
                        # WebSocket 품질 검사
                        if has_websocket:
                            if 'await websocket.send_text(' in line_clean and 'json.dumps' not in line_clean:
                                recommendations.append(f"{file_path}:{i}: WebSocket should send JSON formatted data")
                            
                            if 'websocket.accept()' in line_clean and 'try:' not in content:
                                issues.append(f"{file_path}:{i}: WebSocket connections should include error handling")
                        
                        # 데이터베이스 보안 검사
                        if has_database:
                            if 'execute(' in line_clean and 'f"' in line_clean:
                                security_issues.append(f"{file_path}:{i}: Potential SQL injection - use parameterized queries")
                            
                            if 'password' in line_lower and ('=' in line_clean or '"' in line_clean):
                                if not line_clean.startswith('#'):
                                    security_issues.append(f"{file_path}:{i}: Hardcoded database password detected")
                        
                        # INA219 데이터 분석 검사
                        if has_data_analysis:
                            if 'numpy' in line_clean and 'import numpy as np' not in content:
                                recommendations.append(f"{file_path}:{i}: Use standard numpy import convention (import numpy as np)")
                            
                            if '.mean()' in line_clean or '.std()' in line_clean:
                                if 'axis=' not in line_clean:
                                    recommendations.append(f"{file_path}:{i}: Specify axis parameter for numpy operations")
                        
                        # 환경 변수 및 설정 검사
                        if 'os.environ' in line_clean or 'getenv' in line_clean:
                            if '.get(' not in line_clean and 'getenv(' not in line_clean:
                                recommendations.append(f"{file_path}:{i}: Use os.environ.get() with default values")
                        
                        # 로깅 품질 검사
                        if 'print(' in line_clean and 'debug' not in str(file_path).lower():
                            recommendations.append(f"{file_path}:{i}: Consider using logging instead of print()")
                        
                        # Docker 관련 검사
                        if 'dockerfile' in str(file_path).lower() or 'docker' in line_lower:
                            if 'root' in line_lower and 'user' in line_lower:
                                security_issues.append(f"{file_path}:{i}: Avoid running as root user in Docker")
                        
                        # 하드코딩된 값 검사
                        if any(keyword in line_lower for keyword in ['api_key', 'secret', 'token', 'password']):
                            if '=' in line_clean and '"' in line_clean and not line_clean.startswith('#'):
                                security_issues.append(f"{file_path}:{i}: Hardcoded sensitive information detected")
                        
                        # INA219 특화 상수 검사
                        if any(keyword in line_lower for keyword in ['voltage', 'current', 'power']):
                            if 'magic number' in line_lower or re.search(r'\b\d+\.\d+\b', line_clean):
                                recommendations.append(f"{file_path}:{i}: Consider using named constants for measurement thresholds")
                                
            except Exception as e:
                issues.append(f"{file_path}: Error reading file: {e}")
        
        return {
            "issues": issues,
            "recommendations": recommendations, 
            "security_issues": security_issues,
            "count": len(issues) + len(recommendations) + len(security_issues)
        }
    
    def check_cpp_quality(self, cpp_files, arduino_files=None):
        """C++/Arduino 코드 품질 검사"""
        all_cpp_files = list(cpp_files)
        if arduino_files:
            all_cpp_files.extend(arduino_files)
            
        if not all_cpp_files:
            return {"status": "skipped", "reason": "No C++/Arduino files found"}
            
        print("C++/Arduino 코드 품질 검사 중...")
        results = {}
        
        # 기본 정적 분석
        basic_issues = self.basic_cpp_analysis(all_cpp_files)
        results["basic_analysis"] = basic_issues
        
        # INA219 특화 검사
        ina219_issues = self.ina219_specific_analysis(all_cpp_files)
        results["ina219_analysis"] = ina219_issues
        
        return results
    
    def basic_cpp_analysis(self, cpp_files):
        """기본 C++ 정적 분석"""
        issues = []
        
        for file_path in cpp_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    for i, line in enumerate(lines, 1):
                        line_clean = line.strip()
                        
                        # 잠재적 문제 검사
                        if 'malloc(' in line_clean and 'free(' not in content:
                            issues.append(f"{file_path}:{i}: Potential memory leak - malloc without free")
                            
                        if 'strcpy(' in line_clean or 'strcat(' in line_clean:
                            issues.append(f"{file_path}:{i}: Unsafe string function")
                            
                        if 'TODO' in line_clean.upper() or 'FIXME' in line_clean.upper():
                            issues.append(f"{file_path}:{i}: TODO/FIXME comment")
                            
                        # Arduino 특화 검사
                        if file_path.suffix == '.ino':
                            if 'delay(' in line_clean and 'millis()' not in content:
                                issues.append(f"{file_path}:{i}: Consider using millis() instead of delay()")
                                
            except Exception as e:
                issues.append(f"{file_path}: Error reading file: {e}")
                
        return {"issues": issues, "count": len(issues)}
    
    def ina219_specific_analysis(self, cpp_files):
        """INA219 프로젝트 특화 분석"""
        issues = []
        recommendations = []
        security_issues = []
        
        for file_path in cpp_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    lines = content.split('\n')
                    
                    # INA219 관련 패턴 검사
                    has_ina219_include = '#include' in content and 'INA219' in content
                    has_i2c_init = 'Wire.begin()' in content or 'I2C' in content
                    has_error_handling = 'if' in content and ('error' in content.lower() or 'fail' in content.lower())
                    has_wifi_code = 'WiFi' in content or 'wifi' in content.lower()
                    
                    for i, line in enumerate(lines, 1):
                        line_clean = line.strip()
                        line_lower = line_clean.lower()
                        
                        # INA219 센서 특화 검사
                        if 'ina219.begin()' in line_clean and not has_error_handling:
                            issues.append(f"{file_path}:{i}: INA219 initialization should include error handling")
                        
                        if 'getBusVoltage_V()' in line_clean or 'getCurrent_mA()' in line_clean:
                            if 'delay(' in content and 'millis()' not in content:
                                recommendations.append(f"{file_path}:{i}: Consider non-blocking measurement intervals using millis()")
                        
                        # 전력 측정 단위 검사
                        if 'Serial.print' in line_clean and 'voltage' in line_lower:
                            if not any(unit in line_clean for unit in ['V', 'mV', 'volt']):
                                issues.append(f"{file_path}:{i}: Voltage output should include units (V or mV)")
                        
                        if 'Serial.print' in line_clean and 'current' in line_lower:
                            if not any(unit in line_clean for unit in ['mA', 'A', 'amp']):
                                issues.append(f"{file_path}:{i}: Current output should include units (mA or A)")
                        
                        if 'Serial.print' in line_clean and 'power' in line_lower:
                            if not any(unit in line_clean for unit in ['W', 'mW', 'watt']):
                                issues.append(f"{file_path}:{i}: Power output should include units (W or mW)")
                        
                        # JSON 프로토콜 검사 (INA219 프로젝트 특화)
                        if '"v":' in line_clean or '"a":' in line_clean or '"w":' in line_clean:
                            if '"ts":' not in content:
                                recommendations.append(f"{file_path}:{i}: JSON data should include timestamp field")
                            if '"seq":' not in content:
                                recommendations.append(f"{file_path}:{i}: JSON data should include sequence number for integrity")
                        
                        # WiFi 보안 검사
                        if has_wifi_code:
                            if 'password' in line_lower and ('=' in line_clean or '"' in line_clean):
                                if not line_clean.startswith('//') and not line_clean.startswith('*'):
                                    security_issues.append(f"{file_path}:{i}: Hardcoded WiFi password detected - use environment variables")
                            
                            if 'ssid' in line_lower and ('=' in line_clean or '"' in line_clean):
                                if not line_clean.startswith('//') and not line_clean.startswith('*'):
                                    recommendations.append(f"{file_path}:{i}: Consider using environment variables for SSID")
                        
                        # UNO R4 WiFi 특화 검사
                        if 'uno_r4_wifi' in str(file_path).lower() or 'UNO_R4' in content:
                            if 'WiFiS3.h' not in content and has_wifi_code:
                                issues.append(f"{file_path}:{i}: UNO R4 WiFi should use WiFiS3.h library")
                            
                            if 'delay(' in line_clean and int(re.findall(r'\d+', line_clean)[0] if re.findall(r'\d+', line_clean) else '0') > 1000:
                                recommendations.append(f"{file_path}:{i}: Long delays can affect real-time monitoring - consider shorter intervals")
                        
                        # 시뮬레이터 모드 검사
                        if 'simulator' in str(file_path).lower() or 'SIMULATOR' in content:
                            if 'NORMAL' in content and 'LOAD_SPIKE' in content:
                                if 'ERROR_TEST' not in content:
                                    recommendations.append(f"{file_path}:{i}: Simulator should include error test mode")
                                
            except Exception as e:
                issues.append(f"{file_path}: Error reading file: {e}")
        
        return {
            "issues": issues, 
            "recommendations": recommendations,
            "security_issues": security_issues,
            "count": len(issues) + len(recommendations) + len(security_issues)
        }
    
    def save_results(self):
        """검사 결과를 로그 파일로 저장"""
        log_file = self.log_dir / f"quality_check_{self.timestamp}.json"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
            
        # 텍스트 요약 로그도 생성
        summary_file = self.log_dir / f"quality_summary_{self.timestamp}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("INA219 Power Monitoring - Code Quality Report\n")
            f.write("=" * 50 + "\n")
            f.write(f"Timestamp: {self.timestamp}\n\n")
            
            for lang, result in self.results.items():
                f.write(f"\n{lang.upper()} Results:\n")
                f.write("-" * 20 + "\n")
                f.write(json.dumps(result, indent=2, ensure_ascii=False, default=str))
                f.write("\n")
                
        print(f"결과 저장됨: {log_file}")
        print(f"요약 저장됨: {summary_file}")
    
    def print_summary(self):
        """검사 결과 요약 출력"""
        print("\n" + "=" * 60)
        print("코드 품질 검사 결과 요약")
        print("=" * 60)
        
        total_issues = 0
        
        for lang, result in self.results.items():
            print(f"\n{lang.upper()}:")
            
            if result.get("status") == "skipped":
                print(f"   건너뜀: {result.get('reason', 'Unknown')}")
                continue
                
            lang_issues = 0
            
            # 각 도구별 결과 요약
            for tool, tool_result in result.items():
                if isinstance(tool_result, dict):
                    if "issues_count" in tool_result:
                        issues = tool_result["issues_count"]
                        lang_issues += issues
                        status = "통과" if issues == 0 else f"{issues}개 이슈"
                        print(f"   {tool}: {status}")
                    elif "count" in tool_result:
                        issues = tool_result["count"]
                        lang_issues += issues
                        status = "통과" if issues == 0 else f"{issues}개 이슈"
                        print(f"   {tool}: {status}")
                    elif tool_result.get("status") == "not_installed":
                        print(f"   {tool}: 미설치 - {tool_result.get('message', '')}")
                        
            total_issues += lang_issues
            
        print(f"\n전체 이슈: {total_issues}개")
        
        if total_issues == 0:
            print("✅ 모든 검사를 통과했습니다!")
        else:
            print("📋 상세 내용은 logs/quality/ 디렉토리를 확인하세요.")
    
    def run_all_checks(self, auto_fix=True):
        """모든 언어에 대한 품질 검사 실행"""
        print("🚀 INA219 Power Monitoring 프로젝트 코드 품질 검사 시작")
        print("-" * 60)
        
        # 소스 파일 찾기
        files_by_language = self.find_source_files()
        
        # 1단계: 자동 수정 (선택적)
        if auto_fix and files_by_language['python']:
            print("\n1단계: 자동 수정 실행")
            print("-" * 30)
            auto_fix_results = self.auto_fix_python_files(files_by_language['python'])
            
            if 'autofix' not in self.results:
                self.results['autofix'] = {}
            self.results['autofix']['python'] = auto_fix_results
        
        # 2단계: 품질 검사
        print(f"\n{'2단계: ' if auto_fix else ''}품질 검사 실행")
        print("-" * 30)
        
        # 각 언어별 검사 실행
        if files_by_language['python']:
            self.results['python'] = self.check_python_quality(files_by_language['python'])
            
        if files_by_language['arduino']:
            self.results['arduino'] = self.check_cpp_quality([], files_by_language['arduino'])
        
        # 결과 저장 및 출력
        self.save_results()
        self.print_summary()


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    checker = MultiLanguageQualityChecker(project_root)
    checker.run_all_checks()


if __name__ == "__main__":
    main()