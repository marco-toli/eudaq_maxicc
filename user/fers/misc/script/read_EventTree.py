import ROOT
import numpy as np
from array import array
ROOT.gROOT.Reset()


def integrate_waveform(gWaveform, x_min, x_max):
    n_points = gWaveform.GetN()
    x = np.zeros(n_points, dtype='float64')
    y = np.zeros(n_points, dtype='float64')

    x_val = array('d', [0.])
    y_val = array('d', [0.])

    for i in range(n_points):
        gWaveform.GetPoint(i, x_val, y_val)
        x[i] = x_val[0]
        y[i] = y_val[0]

    # Select points within the desired range
    mask = (x >= x_min) & (x <= x_max)
    x_selected = x[mask]
    y_selected = y[mask]

    if len(x_selected) < 2:
        print("Warning: Not enough points in the integration range.")
        return 0

    integral = np.trapz(y_selected, x_selected)
    return integral



h_integral_DRS = ROOT.TH1F("h_integral_DRS","h_integral_DRS", 1000, 0, 500000)
h_integral_FERS = ROOT.TH1F("h_integral_FERS","h_integral_FERS", 1000, 0, 8000)
h_scatter  = ROOT.TH2F("h_scatter","h_scatter", 1000, 0, 500000, 1000, 0, 8000)

#run_id = 100
#input("Insert run number: ", run_id)
# Open the ROOT file
file = ROOT.TFile.Open("../run109.root")

# Get the EventTree
tree = file.Get("EventTree")

# Read scalar branches
run_n = ROOT.std.vector('unsigned int')()
event_n = ROOT.std.vector('unsigned int')()
event_flag = ROOT.std.vector('unsigned int')()
device_n = ROOT.std.vector('unsigned int')()
trigger_n = ROOT.std.vector('unsigned int')()
timestampbegin = ROOT.std.vector('long')()
timestampend = ROOT.std.vector('long')()
DRS_Board0_PID = ROOT.std.vector('int')()
FERS_Board0_PID = ROOT.std.vector('int')()
FERS_Board0_tstamp_us = ROOT.std.vector('double')()
FERS_Board0_rel_tstamp_us = ROOT.std.vector('double')()
FERS_Board0_trigger_id = ROOT.std.vector('unsigned long long')()
FERS_Board0_chmask = ROOT.std.vector('unsigned long long')()
FERS_Board0_qdmask = ROOT.std.vector('unsigned long long')()

# For the waveform channels (arrays of 1024 floats per entry)
import numpy as np

nEvt = tree.GetEntries()

# Prepare x-axis once
x = np.arange(1024, dtype='double')
#x_ptr = x.ctypes.data_as(ROOT.AddressOf(ROOT.TVectorD(1024)))



for i in range(nEvt):
    tree.GetEntry(i)

    # Scalars
    run_n = tree.run_n
    event_n = tree.event_n
    event_flag = tree.event_flag
    device_n = tree.device_n
    trigger_n = tree.trigger_n
    timestampbegin = tree.timestampbegin
    timestampend = tree.timestampend
    DRS_Board0_PID = tree.DRS_Board0_PID
    FERS_Board0_PID = tree.FERS_Board0_PID
    FERS_Board0_tstamp_us = tree.FERS_Board0_tstamp_us
    FERS_Board0_rel_tstamp_us = tree.FERS_Board0_rel_tstamp_us
    FERS_Board0_trigger_id = tree.FERS_Board0_trigger_id
    FERS_Board0_chmask = tree.FERS_Board0_chmask
    FERS_Board0_qdmask = tree.FERS_Board0_qdmask

    # Waveform channels: example for Channel0
    data_ch0 = np.array(list(tree.DRS_Board0_Group0_Channel0))

    #gWaveform[nEvt][ch]

    # You can also loop over channels dynamically if needed:
    channels = {}
    integral = 0

    ch = 0
    branch_name = f"DRS_Board0_Group0_Channel{ch}"
#    print("ch: ", ch)
    #channels[ch] = np.array(list(getattr(tree, branch_name)))

    waveform_array = np.array(list(getattr(tree, branch_name)), dtype='double')
    # Create the TGraph
    gWaveform = ROOT.TGraph(1024, x, waveform_array)

    # Optional: Set styles
    gWaveform.SetTitle(f"Waveform Entry {i} Channel {ch};Sample;ADC Value")
    gWaveform.SetLineColor(ROOT.kBlue)

    ped_min = 0
    ped_max = 250
    pedestal = integrate_waveform(gWaveform, ped_min, ped_max) / (ped_max-ped_min)
#    print("pedestal = ", pedestal)

    waveform_array_pedsub = waveform_array- pedestal
    
    # Create the TGraph
    gWaveform = ROOT.TGraph(1024, x, waveform_array_pedsub)


    x_min = 250  # sample index start
    x_max = 1000  # sample index end
    integral = - integrate_waveform(gWaveform, x_min, x_max)
#        print(f"Integral for entry {i} channel {ch} in range [{x_min}, {x_max}]: {integral}")
    

    # Draw and optionally save or inspect
    if i < 1 and ch < 1:  # Only plot first waveform for visualization
         canvas = ROOT.TCanvas("c", "Waveform", 800, 600)
         gWaveform.Draw("AL")
         canvas.Update()
         input("Press Enter to continue...")

#    print("integral = ", integral)                
    # FERS energy arrays
    energyHG = np.array(list(tree.FERS_Board0_energyHG))
    energyLG = np.array(list(tree.FERS_Board0_energyLG))

    h_integral_DRS.Fill(integral) #DRS wf integral
    h_integral_FERS.Fill(energyHG[0]) #FERS HG
    h_scatter.Fill(integral,energyHG[0])          # scatter tra DRS integral e HG FERS


    # Example: print summary for first 5 events
    if i < 5:
        print(f"Entry {i}: run_n={run_n}, event_n={event_n}")
        print(f"  Ch0 waveform first 5 samples: {data_ch0[:5]}")
        print(f"  FERS energyHG first 5: {energyHG[:5]}")


file.Close()


cIntegral = ROOT.TCanvas("cIntegral","cIntegral", 1200, 500)
cIntegral.Divide(3,1)
cIntegral.cd(1)
h_integral_DRS.Draw()
cIntegral.cd(2)
h_integral_FERS.Draw()
cIntegral.cd(3)
h_scatter.Draw("COLZ")
cIntegral.Update()
input()

