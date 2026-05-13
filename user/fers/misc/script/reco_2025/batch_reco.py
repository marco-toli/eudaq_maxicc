#!/usr/bin/env python3
import subprocess
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def run_single_job(run, args):
    """Run reco_ntuple.py for a single run."""
    cmd = [
        args.python,
        "reco_ntuple.py",
        "--run", str(run),
        "--config", args.config,
        "--prescale", str(args.prescale),
        "--makeplots", str(args.makeplots)
    ]
    print(f"➡️  Launching run {run}: {' '.join(cmd)}")

    if args.dryrun:
        return (run, 0)

    ret = subprocess.run(cmd, capture_output=False)
    return (run, ret.returncode)

def main():
    parser = argparse.ArgumentParser(description="Parallel batch launcher for reco_ntuple.py")
    parser.add_argument("--run_min", type=int, required=True, help="First run number")
    parser.add_argument("--run_max", type=int, required=True, help="Last run number (inclusive)")
    parser.add_argument("--config", type=str, default="reco_config_drs_fers.json", help="Config file path")
    parser.add_argument("--prescale", type=int, default=1, help="Prescale factor")
    parser.add_argument("--makeplots", type=int, default=1, help="Whether to make plots (1=yes, 0=no)")
    parser.add_argument("--python", type=str, default="python3", help="Python interpreter to use")
    parser.add_argument("--n_jobs", type=int, default=4, help="Number of parallel jobs")
    parser.add_argument("--dryrun", action="store_true", help="Print commands without executing them")

    args = parser.parse_args()

    runs = list(range(args.run_min, args.run_max + 1))

    print(f"\n🚀 Launching {len(runs)} runs ({args.run_min} → {args.run_max}) with {args.n_jobs} parallel jobs\n")

    with ThreadPoolExecutor(max_workers=args.n_jobs) as executor:
        future_to_run = {executor.submit(run_single_job, run, args): run for run in runs}
        for future in as_completed(future_to_run):
            run = future_to_run[future]
            try:
                run_id, retcode = future.result()
                if retcode == 0:
                    print(f"✅ Run {run_id} completed successfully")
                else:
                    print(f"❌ Run {run_id} failed with exit code {retcode}")
            except Exception as e:
                print(f"💥 Run {run} crashed: {e}")

    print("\n🎯 All jobs finished.")

if __name__ == "__main__":
    main()
