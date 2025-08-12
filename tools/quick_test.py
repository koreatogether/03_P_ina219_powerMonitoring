#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Quick Test
빠른 환경 검증 및 기본 테스트
"""

import os
import subprocess
import sys
from pathlib import Path
import importlib.util


def check_command(cmd, description):
    """명령어 실행 가능 여부 확인"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception:
        return False, ""


def check_python_import(module_name, description):
    """Python 모듈 임포트 가능 여부 확인"""
    try:
        importlib.import_module(module_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)


def check_file_exists(file_path, description):
    """파일 존재 여부 확인"""
    path = Path(file_path)
    return path.exists(), str(path.absolute()) if path.exists() else "Not found"


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    print("🚀 INA219 Power Monitoring - 빠른 환경 검증")
    print("=" * 60)
    
    # 검사 항목들
    checks = [
        # Python 환경
        ("Python 버전", lambda: (True, sys.version.split()[0])),
        ("uv 설치", lambda: check_command("python -m uv --version", "uv version")),
        ("가상환경", lambda: check_file_exists(project_root / ".venv", "Virtual environment")),
        
        # 프로젝트 구조
        ("pyproject.toml", lambda: check_file_exists(project_root / "pyproject.toml", "Project config")),
        ("platformio.ini", lambda: check_file_exists(project_root / "platformio.ini", "PlatformIO config")),
        ("소스 디렉토리", lambda: check_file_exists(project_root / "src", "Source directory")),
        
        # Python 패키지들
        ("numpy", lambda: check_python_import("numpy", "NumPy")),
        ("pandas", lambda: check_python_import("pandas", "Pandas")),
        ("matplotlib", lambda: check_python_import("matplotlib", "Matplotlib")),
        ("plotly", lambda: check_python_import("plotly", "Plotly")),
        ("dash", lambda: check_python_import("dash", "Dash")),
        ("pytest", lambda: check_python_import("pytest", "Pytest")),
        ("ruff", lambda: check_python_import("ruff", "Ruff")),
        
        # 개발 도구들
        ("PlatformIO", lambda: check_command("pio --version", "PlatformIO")),
        ("Git", lambda: check_command("git --version", "Git")),
    ]
    
    # 검사 실행
    results = []
    max_name_length = max(len(name) for name, _ in checks)
    
    for check_name, check_func in checks:
        try:
            success, details = check_func()
            status = "✅" if success else "❌"
            results.append((check_name, success, details))
            
            # 결과 출력 (이름을 일정 길이로 맞춤)
            padded_name = check_name.ljust(max_name_length)
            if success:
                print(f"  {status} {padded_name} : {details}")
            else:
                print(f"  {status} {padded_name} : 실패 - {details}")
                
        except Exception as e:
            results.append((check_name, False, str(e)))
            padded_name = check_name.ljust(max_name_length)
            print(f"  ❌ {padded_name} : 오류 - {e}")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 검증 결과 요약")
    print("=" * 60)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    success_rate = success_count / total_count * 100
    
    print(f"성공: {success_count}/{total_count} ({success_rate:.1f}%)")
    
    # 실패한 항목들 상세 정보
    failed_items = [(name, details) for name, success, details in results if not success]
    if failed_items:
        print(f"\n❌ 실패한 항목들:")
        for name, details in failed_items:
            print(f"   • {name}: {details}")
        
        print(f"\n💡 해결 방법:")
        
        # 일반적인 해결책 제시
        if any("uv" in name.lower() for name, _ in failed_items):
            print("   1. uv 설치: pip install uv")
        
        if any("가상환경" in name for name, _ in failed_items):
            print("   2. 가상환경 생성: python -m uv sync")
        
        if any(pkg in name.lower() for name, _ in failed_items for pkg in ["numpy", "pandas", "matplotlib", "plotly", "dash"]):
            print("   3. Python 패키지 설치: python -m uv sync --extra dev")
        
        if any("platformio" in name.lower() for name, _ in failed_items):
            print("   4. PlatformIO 설치: python -m uv add platformio")
        
        if any("git" in name.lower() for name, _ in failed_items):
            print("   5. Git 설치: https://git-scm.com/downloads")
        
        print("   6. 전체 환경 설정: python tools/setup_dev_environment.py")
    
    else:
        print(f"\n🎉 모든 검사를 통과했습니다!")
        print(f"\n💡 다음 단계:")
        print("   1. 전체 검사 실행: python tools/run_all_checks.py")
        print("   2. 코드 품질 검사: python tools/code_quality_checker.py")
        print("   3. 빌드 및 테스트: python tools/build_and_test.py")
        print("   4. 성능 분석: python tools/performance_analyzer.py")
    
    # 프로젝트 정보
    print(f"\n📁 프로젝트 정보:")
    print(f"   경로: {project_root}")
    print(f"   Python: {sys.executable}")
    
    # 로그 디렉토리 확인
    logs_dir = project_root / "logs"
    if logs_dir.exists():
        print(f"   로그: {logs_dir}")
    
    # 종료 코드
    return 0 if success_count == total_count else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)