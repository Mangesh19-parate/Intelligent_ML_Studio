#!/usr/bin/env python3
"""
Intelligent ML Studio - Unified Verification Suite
Runs end-to-end verification across Backend Tests, Frontend Typechecks, Frontend Tests, and Production Builds.
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Ensure UTF-8 output on all platforms including Windows CP1252 consoles
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
BACKEND_DIR = ROOT_DIR / "backend"

def run_step(step_name: str, cmd: list[str], cwd: Path) -> tuple[bool, str, float]:
    print(f"\n[{step_name}] Running: {' '.join(cmd)}")
    start_time = time.time()
    
    # On Windows, resolve npm / npx to .cmd if needed
    executable = cmd[0]
    if sys.platform == "win32" and executable in ["npm", "npx"]:
        cmd[0] = f"{executable}.cmd"
        
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env
        )
        duration = time.time() - start_time
        success = (proc.returncode == 0)
        output = proc.stdout.strip()
        
        if success:
            print(f"[{step_name}] PASSED ({duration:.2f}s)")
        else:
            print(f"[{step_name}] FAILED (exit code {proc.returncode}, {duration:.2f}s)")
            print("-" * 40 + " OUTPUT " + "-" * 40)
            clean_out = output.encode('ascii', errors='replace').decode('ascii')
            print(clean_out[:3000] + ("\n... [truncated]" if len(clean_out) > 3000 else ""))
            print("-" * 88)
            
        return success, output, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"[{step_name}] ERROR: {e}")
        return False, str(e), duration

def main():
    print("=" * 80)
    print(" INTELLIGENT ML STUDIO - END-TO-END VERIFICATION SUITE")
    print("=" * 80)
    
    results = []
    
    # Stage 1: Python Dependencies & Modules
    s1_success, s1_out, s1_dur = run_step(
        "1. Python Environment Check",
        [sys.executable, "-c", "import fastapi, sqlalchemy, pydantic, jose, sklearn; print('Core backend dependencies verified.')"],
        ROOT_DIR
    )
    results.append(("Python Dependencies Check", s1_success, s1_dur))
    
    # Stage 2: Backend Test Suite (Pytest)
    s2_success, s2_out, s2_dur = run_step(
        "2. Backend Pytest Suite",
        [sys.executable, "-m", "pytest", "backend/tests", "-q"],
        ROOT_DIR
    )
    results.append(("Backend Test Suite (467 Tests)", s2_success, s2_dur))
    
    # Stage 3: Frontend TypeScript Typecheck
    s3_success, s3_out, s3_dur = run_step(
        "3. Frontend Typecheck (tsc)",
        ["npm", "run", "typecheck"],
        FRONTEND_DIR
    )
    results.append(("Frontend Typecheck (tsc --noEmit)", s3_success, s3_dur))
    
    # Stage 4: Frontend Unit & Component Tests
    s4_success, s4_out, s4_dur = run_step(
        "4. Frontend Unit Tests (vitest)",
        ["npm", "test"],
        FRONTEND_DIR
    )
    results.append(("Frontend Unit Tests (Vitest)", s4_success, s4_dur))
    
    # Stage 5: Frontend Production Build
    s5_success, s5_out, s5_dur = run_step(
        "5. Frontend Production Build",
        ["npm", "run", "build"],
        FRONTEND_DIR
    )
    results.append(("Frontend Production Build (Vite)", s5_success, s5_dur))
    
    # Summary Scorecard
    print("\n" + "=" * 80)
    print(" VERIFICATION SCORECARD")
    print("=" * 80)
    print(f"{'Verification Stage':<45} | {'Duration':<10} | {'Status':<10}")
    print("-" * 80)
    
    all_passed = True
    total_time = 0.0
    for name, success, dur in results:
        status_str = "PASSED" if success else "FAILED"
        print(f"{name:<45} | {dur:>8.2f}s | {status_str:<10}")
        if not success:
            all_passed = False
        total_time += dur
        
    print("-" * 80)
    print(f"{'Total Elapsed Time':<45} | {total_time:>8.2f}s |")
    print("=" * 80)
    
    if all_passed:
        print("\n>>> ALL VERIFICATION CHECKS PASSED: SYSTEM IS 100% CLIENT-READY <<<\n")
        sys.exit(0)
    else:
        print("\n>>> VERIFICATION FAILED: PLEASE RESOLVE THE ABOVE ERRORS <<<\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
