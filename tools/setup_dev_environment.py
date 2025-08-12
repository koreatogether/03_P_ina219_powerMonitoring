#!/usr/bin/env python3
"""
INA219 Power Monitoring System - Development Environment Setup
개발 환경 자동 설정 도구

기능:
- Python 가상환경 생성 (uv 사용)
- 개발 의존성 설치
- PlatformIO 설정
- Git hooks 설정
- 프로젝트 구조 검증
"""

import os
import subprocess
import sys
from pathlib import Path


class DevEnvironmentSetup:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.venv_path = self.project_root / ".venv"
        
    def run_command(self, cmd, desc, check=True):
        """명령어 실행"""
        print(f"🔧 {desc}...")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=self.project_root,
                check=check
            )
            if result.returncode == 0:
                print(f"  ✅ {desc} 완료")
                return True
            else:
                print(f"  ❌ {desc} 실패")
                return False
        except subprocess.CalledProcessError as e:
            print(f"  ❌ {desc} 실패: {e}")
            return False
        except Exception as e:
            print(f"  ❌ {desc} 오류: {e}")
            return False
    
    def setup_uv_environment(self):
        """uv를 사용한 Python 환경 설정"""
        print("\n🐍 uv Python 환경 설정")
        print("-" * 30)
        
        # uv 설치 확인
        try:
            result = subprocess.run(["python", "-m", "uv", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                print("  📥 uv 설치 중...")
                success = self.run_command("pip install uv", "uv 설치")
                if not success:
                    return False
        except FileNotFoundError:
            print("  📥 uv 설치 중...")
            success = self.run_command("pip install uv", "uv 설치")
            if not success:
                return False
        
        # uv sync 실행 (가상환경 생성 및 의존성 설치)
        success = self.run_command("python -m uv sync --extra dev", "uv 환경 동기화")
        if not success:
            print("  💡 python -m uv sync --extra dev 를 수동으로 실행해보세요.")
            return False
        
        return True
    
    def setup_platformio(self):
        """PlatformIO 설정"""
        print("\n🔧 PlatformIO 설정")
        print("-" * 30)
        
        # PlatformIO 설치 확인
        pio_check = subprocess.run(
            ["pio", "--version"],
            capture_output=True,
            text=True
        )
        
        if pio_check.returncode != 0:
            print("  📥 PlatformIO 설치 중...")
            success = self.run_command(
                "python -m uv add platformio",
                "PlatformIO 설치"
            )
            if not success:
                print("  ⚠️  PlatformIO 설치 실패. 수동으로 설치해주세요.")
                return False
        
        # PlatformIO 프로젝트 초기화 (이미 있다면 스킵)
        platformio_ini = self.project_root / "platformio.ini"
        if platformio_ini.exists():
            print("  ℹ️  PlatformIO 프로젝트가 이미 설정되어 있습니다.")
        else:
            self.run_command(
                "pio project init --project-dir .",
                "PlatformIO 프로젝트 초기화"
            )
        
        return True
    
    def setup_git_hooks(self):
        """Git hooks 설정"""
        print("\n🔗 Git hooks 설정")
        print("-" * 30)
        
        # .git 디렉토리 확인
        git_dir = self.project_root / ".git"
        if not git_dir.exists():
            print("  ⚠️  Git 저장소가 아닙니다. git init을 먼저 실행하세요.")
            return False
        
        # pre-commit 설정 파일 생성
        pre_commit_config = self.project_root / ".pre-commit-config.yaml"
        if not pre_commit_config.exists():
            config_content = """repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black
        language_version: python3
  
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.0.270
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
"""
            with open(pre_commit_config, 'w', encoding='utf-8') as f:
                f.write(config_content)
            print("  📝 .pre-commit-config.yaml 생성됨")
        
        # pre-commit hooks 설치
        self.run_command(
            "python -m uv run pre-commit install",
            "pre-commit hooks 설치"
        )
        
        return True
    
    def create_project_structure(self):
        """프로젝트 구조 생성"""
        print("\n📁 프로젝트 구조 생성")
        print("-" * 30)
        
        # 필요한 디렉토리들
        directories = [
            "src/arduino",
            "src/python/dashboard", 
            "src/python/data_processing",
            "tests",
            "docs",
            "benchmarks",
            "logs/quality",
            "logs/build_test",
            "logs/performance",
            "data/raw",
            "data/processed"
        ]
        
        for dir_path in directories:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                print(f"  📂 {dir_path}/ 생성됨")
            else:
                print(f"  ✅ {dir_path}/ 이미 존재")
        
        return True
    
    def verify_setup(self):
        """설정 검증"""
        print("\n✅ 설정 검증")
        print("-" * 30)
        
        checks = [
            ("uv 가상환경", self.venv_path.exists()),
            ("PlatformIO 설정", (self.project_root / "platformio.ini").exists()),
            ("pyproject.toml", (self.project_root / "pyproject.toml").exists()),
            ("Git 저장소", (self.project_root / ".git").exists()),
            ("소스 디렉토리", (self.project_root / "src").exists()),
            ("테스트 디렉토리", (self.project_root / "tests").exists()),
            ("도구 디렉토리", (self.project_root / "tools").exists())
        ]
        
        all_good = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"  {status} {check_name}")
            if not check_result:
                all_good = False
        
        return all_good
    
    def print_next_steps(self):
        """다음 단계 안내"""
        print("\n🎯 다음 단계")
        print("-" * 30)
        
        print("1. uv 환경 활성화:")
        print("   python -m uv shell")
        print()
        print("2. 빠른 테스트 실행:")
        print("   python tools/quick_test.py")
        print()
        print("3. 전체 검사 실행:")
        print("   python tools/run_all_checks.py")
        print()
        print("4. 개별 도구 실행:")
        print("   python tools/code_quality_checker.py")
        print("   python tools/build_and_test.py")
        print("   python tools/performance_analyzer.py")
        print()
        print("5. Dash 대시보드 실행:")
        print("   python -m uv run python src/python/dashboard/app.py")
        print()
        print("6. 코드 작성 후 커밋:")
        print("   git add .")
        print("   git commit -m \"Your message\"")
        print("   (pre-commit hooks가 자동으로 실행됩니다)")
    
    def setup_all(self):
        """전체 개발 환경 설정"""
        print("🚀 INA219 Power Monitoring 개발 환경 설정")
        print("=" * 50)
        
        steps = [
            ("uv 환경 설정", self.setup_uv_environment),
            ("PlatformIO 설정", self.setup_platformio),
            ("Git hooks 설정", self.setup_git_hooks),
            ("프로젝트 구조 생성", self.create_project_structure)
        ]
        
        success_count = 0
        for step_name, step_func in steps:
            try:
                if step_func():
                    success_count += 1
                else:
                    print(f"  ⚠️  {step_name} 단계에서 문제가 발생했습니다.")
            except Exception as e:
                print(f"  ❌ {step_name} 단계 오류: {e}")
        
        print(f"\n📊 설정 완료: {success_count}/{len(steps)} 단계 성공")
        
        # 최종 검증
        if self.verify_setup():
            print("\n🎉 개발 환경 설정이 완료되었습니다!")
            self.print_next_steps()
        else:
            print("\n⚠️  일부 설정이 완료되지 않았습니다. 위의 오류를 확인해주세요.")


def main():
    """메인 함수"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    setup = DevEnvironmentSetup(project_root)
    setup.setup_all()


if __name__ == "__main__":
    main()