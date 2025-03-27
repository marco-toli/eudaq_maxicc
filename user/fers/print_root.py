import ROOT

# Open the ROOT file
file = ROOT.TFile("run739_240719162716.root", "READ")

# Get the tree from the file
tree = file.Get("EventTree")

# Create a variable to hold the branch data
energy_PID_1 = []
energy_lg_1 = []
energy_drs_1 = []

# Loop over the entries in the tree
for entry in tree:
    # Access the branch and append the value to the list
    energy_PID_1.append(entry.FERS_Board0_PID)
    energy_lg_1.append(entry.FERS_Board0_energyLG[1])
    energy_drs_1.append(entry.DRS_Board0_Group0_Channel0[0])

# Print the values from the branch
print("FERS_Board0_energyLG[3] values:")
cnt=0
for value in energy_PID_1:
    print(cnt,value)
    cnt+=1

cnt=0
for value in energy_lg_1:
    print(cnt,value)
    cnt+=1

cnt=0
for value in energy_drs_1:
    print(cnt,value)
    cnt+=1
# Close the file
file.Close()
