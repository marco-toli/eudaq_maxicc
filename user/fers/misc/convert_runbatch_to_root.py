import argparse
import subprocess
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm  # installa con: pip install tqdm

def convert_run(run, path_raw, path_root):
    run_id = f"{run:04d}"
    raw_file = os.path.join(path_raw, f"run{run_id}.raw")
    root_file = os.path.join(path_root, f"run{run_id}.root")

    if not os.path.exists(raw_file):
        return (run, "missing")

    try:
        result = subprocess.run(
            f"/home/maxiccdaq/DAQ/eudaq_maxicc/bin/euCliConverter -i {raw_file} -o {root_file}",
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        if result.stderr:
            print(f"[run {run_id}] stderr:\n{result.stderr}")
        return (run, "ok")
    except subprocess.CalledProcessError as e:
        print(f"[run {run_id}] ❌ Errore (codice {e.returncode})")
        print(f"stderr:\n{e.stderr}")
        return (run, "error")


def main():
    parser = argparse.ArgumentParser(description="Convert raw to root for multiple runs")
    parser.add_argument("--run", nargs="+", type=int, required=True,
                        help="Singoli run o intervallo (es. --run 100 105)")
    parser.add_argument("--parallel", type=int, default=1,
                        help="Numero di job in parallelo (default=1, seriale)")
    args = parser.parse_args()

    # Determina lista di run
    if len(args.run) == 1:
        runs = args.run
    elif len(args.run) == 2:
        runs = list(range(args.run[0], args.run[1] + 1))
    else:
        runs = args.run

    path_raw = "/mnt/mybook/MAXICC/CERNTB_Sept2025/data/raw/"
    path_root = "/mnt/mybook/MAXICC/CERNTB_Sept2025/data/root/"

    print(f"[INFO] Processando {len(runs)} run: {runs}")
    print(f"[INFO] Esecuzione in parallelo: {args.parallel} job\n")

    results = []

    # Usa tqdm per visualizzare l’avanzamento
    with tqdm(total=len(runs), desc="Conversione run", ncols=100) as pbar:
        if args.parallel > 1:
            with ThreadPoolExecutor(max_workers=args.parallel) as executor:
                futures = {executor.submit(convert_run, run, path_raw, path_root): run for run in runs}
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
                    pbar.update(1)
        else:
            for run in runs:
                result = convert_run(run, path_raw, path_root)
                results.append(result)
                pbar.update(1)

    # Riepilogo finale
    print("\n=== Riepilogo ===")
    ok = sum(1 for _, s in results if s == "ok")
    missing = sum(1 for _, s in results if s == "missing")
    error = sum(1 for _, s in results if s == "error")

    for run, status in sorted(results):
        if status == "ok":
            print(f"✅ run {run:04d} completato")
        elif status == "missing":
            print(f"⚠️  run {run:04d} non trovato")
        else:
            print(f"❌ run {run:04d} errore nella conversione")

    print(f"\nTotale: {len(runs)} | ✅ {ok} | ⚠️ {missing} | ❌ {error}")


if __name__ == "__main__":
    main()
