#!/usr/bin/env python3
"""
Intelligent ML Studio - Unified Verification Suite
Runs end-to-end verification across Backend Tests, Frontend Typechecks, Frontend Tests, and Production Builds.
Streams real-time output for complete transparency.
"""

import sys
import os
import re
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
FRONTEND_DIR = ROOT_DIR / "apps" / "frontend"
BACKEND_DIR = ROOT_DIR / "apps" / "backend"

def run_step(step_name: str, cmd: list[str], cwd: Path) -> tuple[bool, str, float]:
    print(f"\n[{step_name}] Running: {' '.join(cmd)}", flush=True)
    start_time = time.time()
    
    is_win = (sys.platform == "win32")
    is_npm = cmd[0] in ["npm", "npx"]
    
    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        
        if is_win and is_npm:
            exec_args = " ".join(cmd)
            use_shell = True
        else:
            exec_args = cmd
            use_shell = False
        
        proc = subprocess.Popen(
            exec_args,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            shell=use_shell
        )
        
        output_lines = []
        for line in iter(proc.stdout.readline, ""):
            output_lines.append(line)
            # Print condensed progress if line contains dots or passed
            if ("passed" in line.lower() or "error" in line.lower() or "failed" in line.lower() or "building" in line.lower() or "built" in line.lower() or "%" in line):
                print(f"  > {line.strip()}", flush=True)
                
        proc.stdout.close()
        proc.wait()
        
        duration = time.time() - start_time
        success = (proc.returncode == 0)
        full_output = "".join(output_lines).strip()
        
        if success:
            print(f"[{step_name}] PASSED ({duration:.2f}s)", flush=True)
        else:
            print(f"[{step_name}] FAILED (exit code {proc.returncode}, {duration:.2f}s)", flush=True)
            print("-" * 40 + " OUTPUT " + "-" * 40, flush=True)
            clean_out = full_output.encode('ascii', errors='replace').decode('ascii')
            print(clean_out[:3000] + ("\n... [truncated]" if len(clean_out) > 3000 else ""), flush=True)
            print("-" * 88, flush=True)
            
        return success, full_output, duration
    except Exception as e:
        duration = time.time() - start_time
        print(f"[{step_name}] ERROR: {e}", flush=True)
        return False, str(e), duration

def main():
    print("=" * 80, flush=True)
    print(" INTELLIGENT ML STUDIO - END-TO-END VERIFICATION SUITE", flush=True)
    print("=" * 80, flush=True)
    
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
        [sys.executable, "-m", "pytest", "apps/backend/tests", "-q"],
        ROOT_DIR
    )
    match = re.search(r"(\d+)\s+passed", s2_out)
    count_label = f" ({match.group(1)} Passed)" if match else ""
    results.append((f"Backend Test Suite{count_label}", s2_success, s2_dur))
    
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
    print("\n" + "=" * 80, flush=True)
    print(" VERIFICATION SCORECARD", flush=True)
    print("=" * 80, flush=True)
    print(f"{'Verification Stage':<45} | {'Duration':<10} | {'Status':<10}", flush=True)
    print("-" * 80, flush=True)
    
    all_passed = True
    total_time = 0.0
    for name, success, dur in results:
        status_str = "PASSED" if success else "FAILED"
        print(f"{name:<45} | {dur:>8.2f}s | {status_str:<10}", flush=True)
        if not success:
            all_passed = False
        total_time += dur
        
    print("-" * 80, flush=True)
    print(f"{'Total Elapsed Time':<45} | {total_time:>8.2f}s |", flush=True)
    print("=" * 80, flush=True)
    
    if all_passed:
        print("\n>>> ALL VERIFICATION CHECKS PASSED: SYSTEM IS 100% CLIENT-READY <<<\n", flush=True)
        sys.exit(0)
    else:
        print("\n>>> VERIFICATION FAILED: PLEASE RESOLVE THE ABOVE ERRORS <<<\n", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
