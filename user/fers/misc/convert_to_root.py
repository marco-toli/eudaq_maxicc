import argparse
import subprocess

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Convert to root and store log and config files")
    parser.add_argument("--run", type=int, help="run number")
    args = parser.parse_args()

    runId = "%04d"%(args.run)
#    path_raw = "/home/maxiccdaq/DAQ/eudaq_maxicc/user/fers/misc/"
    path_raw = "/mnt/mybook/MAXICC/CERNTB_Sept2025/data/raw/"
    path_root = "/mnt/mybook/MAXICC/CERNTB_Sept2025/data/root/"
    
    # Run the OS command
    print("Converting raw to root ...")
    try:
        result = subprocess.run(f"/home/maxiccdaq/DAQ/eudaq_maxicc/bin/euCliConverter -i {path_raw}/run{runId}.raw -o {path_root}/run{runId}.root", shell=True, check=True, capture_output=True, text=True)
        print("Output:\n", result.stdout)        
        if result.stderr:
            print("Errors:\n", result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Command failed with return code {e.returncode}")
        print("Error output:\n", e.stderr)


    
if __name__ == "__main__":
    main()
