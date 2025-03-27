import ROOT
import argparse

# Set up argument parser
parser = argparse.ArgumentParser(description="Filter events from a ROOT file based on FERS_Board0_PID.")
parser.add_argument("-i", "--input_file", required=True, help="Path to the input ROOT file")
parser.add_argument("-o", "--output_file", required=True, help="Path to the output ROOT file")

# Parse the command-line arguments
args = parser.parse_args()

# Open the original ROOT file
input_file = ROOT.TFile(args.input_file, "READ")

# Get the tree from the input file
input_tree = input_file.Get("EventTree")

# Create a new ROOT file to store the filtered tree
output_file = ROOT.TFile(args.output_file, "RECREATE")

# Create a new tree in the output file with the same structure as the input tree
output_tree = input_tree.CloneTree(0)

# Loop over the entries in the input tree and copy the desired ones
for entry in input_tree:
    if entry.FERS_Board0_PID > 0 and entry.FERS_Board0_PID <23000:
        output_tree.Fill()

# Write the new tree to the output file
output_tree.Write()

# Close both files
input_file.Close()
output_file.Close()
