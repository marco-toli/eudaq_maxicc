import ROOT
import numpy as np
from array import array
import os
import json
import argparse
from analysis_functions import get_pedestal, get_gr_ch, get_times
from tree_init import save_root_tree, find_position_in_map

ROOT.gROOT.Reset()
ROOT.gROOT.SetBatch(True)

# Create the parser
parser = argparse.ArgumentParser(description="DQM RECO")

# Add arguments
parser.add_argument('--run', type=int, help='Run number')
parser.add_argument('--config', type=str, default="reco_config_drs.json", help='Reco json config file')
parser.add_argument('--prescale', type=int, default=1, help='1/fraction of events to be analyzed: 1 all, 10=1/10')

# Parse the arguments
args = parser.parse_args()


with open(args.config, 'r') as f:
    config = json.load(f)


# read config json file
nDigiGroups = 0
nDigiCh = []
nFersBoards = 0

if "digitizer" in config:
    digitizer = config["digitizer"]

    # Count groups
    group_keys = [key for key in digitizer.keys() if key.startswith("group")]
    nDigiGroups = len(group_keys)
    print(f"Number of groups in json: {nDigiGroups}")
    
    #Count ch in each group
    for group in group_keys:
        ch_keys = [key for key in digitizer[group].keys() if key.startswith("ch")]
        nDigiCh.append(len(ch_keys))
        print(f"{group} has {len(ch_keys)} channels")
        
if "fers" in config:
    fers = config["fers"]
    # Count boards
    board_keys = [key for key in fers.keys() if key.startswith("board")]
    nFersBoards = len(board_keys)
    print(f"Number of FERS boards in json: {nFersBoards}")
    

#read input root file
run_id = args.run
path_plots = "/var/www/html/MAXICC/run_%d"%run_id
path_plots_drs = "/var/www/html/MAXICC/run_%d/drs/"%run_id
path_plots_fers = "/var/www/html/MAXICC/run_%d/fers/"%run_id
path_reco = "/data/reco/"
os.makedirs(path_plots, exist_ok=True)
os.makedirs(path_plots_drs, exist_ok=True)
os.makedirs(path_plots_fers, exist_ok=True)
file = ROOT.TFile.Open("/data/run%04d.root"%run_id)


#read tree
all_wf = {}
all_fers_hg = {}
all_fers_lg = {}

# Get the EventTree
tree = file.Get("EventTree")

for i, event in enumerate(tree):
    if (i%args.prescale != 0): continue

    #readout digitizer branches, if they exist
    for group in range(nDigiGroups):
        for ch in range(nDigiCh[group]):        

            branch_name = f"DRS_Board{0}_Group{group}_Channel{ch}"        
            if not hasattr(tree, branch_name):                       
                if (i == 0): print(f"Branch {branch_name} does not exist --> check your config file!")
                continue
        
            if (i == 0):
                all_wf[branch_name] = []                 
            
            all_wf[branch_name].append(np.array(list(getattr(event, branch_name))))

            #readout fers branches, if they exist
    for board in range(nFersBoards):
        branch_name_hg = f"FERS_Board{board}_energyHG"
        branch_name_lg = f"FERS_Board{board}_energyLG"

        if not hasattr(tree, branch_name_hg):                       
            if (i == 0): print(f"Branch {branch_name_hg} does not exist --> check your config file!")
            continue
        
        if (i == 0):
            all_fers_hg[branch_name_hg] = []
            all_fers_lg[branch_name_lg] = []
            
        all_fers_hg[branch_name_hg].append(np.array(list(getattr(event, branch_name_hg))))
        all_fers_lg[branch_name_lg].append(np.array(list(getattr(event, branch_name_lg))))

file.Close()

#define histos
results = {}
gWf2 = {}
gWf = {}
h_maxAmp_DRS = {}
h_integral_DRS = {}
h_times_DRS = {}

wcL_name = ""
wcR_name = ""
wcT_name = ""
wcB_name = ""

#analyze digitizer waveforms
for branch_name, waveforms in all_wf.items():
    # Convert to 2D array if not already
    group, ch = get_gr_ch(branch_name)
    waveforms = np.array(waveforms)  # shape: (num_events, num_samples)
    pedestals = get_pedestal(waveforms)
    polarity  = digitizer[f"group{group}"][f"ch{ch}"]["polarity"]
    sigtype   = digitizer[f"group{group}"][f"ch{ch}"]["type"]
    waveforms = (waveforms-pedestals[:,None])*polarity #/1024

    if   (sigtype == "wcL"): wcL_name = branch_name
    elif (sigtype == "wcR"): wcR_name = branch_name
    elif (sigtype == "wcT"): wcT_name = branch_name
    elif (sigtype == "wcB"): wcB_name = branch_name

    # Average waveform over all events
    avg_waveform = np.mean(waveforms, axis=0)
    # Maximum waveform value for each event
    maxamp = np.max(waveforms, axis=1)
    # Integral (sum) for each waveform/event
    integral = np.sum(waveforms, axis=1)
    # time
    times = get_times(waveforms, thresholds=maxamp*0.5)
    
    results[branch_name] = {
    "avg_waveform": avg_waveform,
    "maxamp": maxamp,
    "integral": integral,
    "times": times
    }

    # print the first 10 waveforms
    if sigtype == "wcL" or sigtype == "wcR" or sigtype == "wcT" or sigtype == "wcB":
        for it in range(10):
            num_samples = waveforms.shape[1]
            x = array("d", np.arange(num_samples))
            y = array("d", waveforms[it])
            
            gWf2[branch_name] = ROOT.TGraph(num_samples, x, y)
            gWf2[branch_name].SetTitle(f"{branch_name};Sample;Amplitude (mV)")
            gWf2[branch_name].SetLineColor(ROOT.kBlue)
            gWf2[branch_name].SetLineWidth(2)

            print(it,branch_name,results[branch_name]["times"][it])
            cWf = ROOT.TCanvas("cWf%d_%s"%(it,branch_name),"cWf%d_%s"%(it,branch_name), 500, 500)
            gWf2[branch_name].Draw("ALPE")
            cWf.SaveAs("%s/cWf%d_%s.png"%(path_plots_drs,it,branch_name))
            
    
    # average waveforms
    num_samples = avg_waveform.shape[0]
    x = array("d", np.arange(num_samples))
    y = array("d", avg_waveform)
    
    gWf[branch_name] = ROOT.TGraph(num_samples, x, y)
    gWf[branch_name].SetTitle(f"{branch_name};Sample;Amplitude (V)")
    gWf[branch_name].SetLineColor(ROOT.kBlue)
    gWf[branch_name].SetLineWidth(2)
    
    cAvgWf = ROOT.TCanvas("cAvgWf_%s"%branch_name,"cAvgWf_%s"%branch_name, 500, 500)
    gWf[branch_name].Draw("ALPE")
    #gWf[branch_name].Write(branch_name)
    cAvgWf.SaveAs("%s/cAvgWf_%s.png"%(path_plots_drs,branch_name))

    #max amplitude
    h_maxAmp_DRS[branch_name] = ROOT.TH1F("h_maxAmp_DRS_gr%d_ch%d"%(group, ch),"h_maxAmp_DRS_gr%d_ch%d"%(group, ch), 4096, 0, 4096)  # in V
    h_maxAmp_DRS[branch_name].FillN(len(maxamp), maxamp, np.ones_like(maxamp))
   
    cMaxAmp = ROOT.TCanvas("cMaxAmp_%s"%branch_name,"cMaxAmp_%s"%branch_name, 500, 500)
    h_maxAmp_DRS[branch_name].Draw("")
    cMaxAmp.SaveAs("%s/cMaxAmp_%s.png"%(path_plots_drs,branch_name))

    #integral
    h_integral_DRS[branch_name] = ROOT.TH1F("h_integral_DRS_gr%d_ch%d"%(group, ch),"h_integral_DRS_gr%d_ch%d"%(group, ch), 4096, 0, 4096*200)  # in V
    h_integral_DRS[branch_name].FillN(len(integral), integral, np.ones_like(integral))
   
    cIntegral = ROOT.TCanvas("cIntegral_%s"%branch_name,"cIntegral_%s"%branch_name, 500, 500)
    h_integral_DRS[branch_name].Draw("")
    cIntegral.SaveAs("%s/cIntegral_%s.png"%(path_plots_drs,branch_name))


    #times
    h_times_DRS[branch_name] = ROOT.TH1F("h_times_DRS_gr%d_ch%d"%(group, ch),"h_times_DRS_gr%d_ch%d"%(group, ch), 4096, 0, 1024)  # in V
    h_times_DRS[branch_name].FillN(len(times), times, np.ones_like(times))
   
    cTimes = ROOT.TCanvas("cTimes_%s"%branch_name,"cTimes_%s"%branch_name, 500, 500)
    h_times_DRS[branch_name].Draw("")
    cTimes.SaveAs("%s/cTimes_%s.png"%(path_plots_drs,branch_name))


beamX = []
beamY = []

#find x,y beam positions from WC times
if (wcL_name != ""):
    WC_calibX = 0.00450 #calibration constants measured at H6 in July 2024                                                                                                                            
    WC_calibY = 0.00453
    beamX = (results[wcR_name]["times"] - results[wcL_name]["times"])*WC_calibX*100
    beamY = (results[wcT_name]["times"] - results[wcB_name]["times"])*WC_calibY*100

    h_beamX = ROOT.TH1F("h_beamX","h_beamX", 200, -100, 100)  # in mm?
    h_beamX.FillN(len(beamX), beamX, np.ones_like(beamX))
    cBeamX = ROOT.TCanvas("cBeamX_%s"%branch_name,"cBeamX_%s"%branch_name, 500, 500)
    h_beamX.Draw("")
    cBeamX.SaveAs("%s/cBeamX_%s.png"%(path_plots,branch_name))

    h_beamY = ROOT.TH1F("h_beamY","h_beamY", 200, -100, 100)  # in mm?
    h_beamY.FillN(len(beamY), beamY, np.ones_like(beamY))
    cBeamY = ROOT.TCanvas("cBeamY_%s"%branch_name,"cBeamY_%s"%branch_name, 500, 500)
    h_beamY.Draw("COLZ")
    cBeamY.SaveAs("%s/cBeamY_%s.png"%(path_plots,branch_name))

    h2_beamXY = ROOT.TH2F("h2_beamXY","h2_beamXY", 200, -100, 100, 200, -100, 100)  # in mm?
    h2_beamXY.FillN(len(beamX), beamX, beamY, np.ones_like(beamX))
    cBeamXY = ROOT.TCanvas("cBeamXY_%s"%branch_name,"cBeamXY_%s"%branch_name, 500, 500)
    h2_beamXY.Draw("COLZ")
    cBeamXY.SaveAs("%s/cBeamXY_%s.png"%(path_plots,branch_name))

    trigger_name = f"DRS_Board{0}_Group{0}_Channel{5}"
    h2_Amp_vs_Pos = ROOT.TH2F("h2_Amp_vs_Pos","h2_Amp_vs_Pos", 200, -100, 100, 200, -100, 100)  # in mm?
    h2_Amp_vs_Pos.FillN(len(beamX), beamX, beamY, results[trigger_name]["integral"])
    cAmp_vs_Pos = ROOT.TCanvas("cBeamXY_%s"%branch_name,"cBeamXY_%s"%branch_name, 500, 500)
    h2_Amp_vs_Pos.Draw("COLZ")
    cAmp_vs_Pos.SaveAs("%s/cAmp_vs_Pos_%s.png"%(path_plots,branch_name))



#analyze fers data
h_Ene_FERS_LG = {}
h_Ene_FERS_HG = {}
h2_Map_FERS_HG = {}
h2_Map_FERS_HG = {}

for board in range(len(all_fers_hg.items())):
    branch_name_hg = f"FERS_Board{board}_energyHG"
    branch_name_lg = f"FERS_Board{board}_energyLG"
    all_fers_hg[branch_name_hg] = np.vstack(all_fers_hg[branch_name_hg])
    all_fers_lg[branch_name_lg] = np.vstack(all_fers_lg[branch_name_lg])
    h2_Map_FERS_HG[branch_name_hg] = ROOT.TH2F("hMAP_%s"%branch_name_hg, "hMAP_%s;X;Y"%branch_name_hg, 9,0,9, 9,0,9)

    print(all_fers_lg[branch_name_lg][:, 0])
    for ch in range(len(all_fers_lg[branch_name_lg][0])):   
        pos = find_position_in_map(fers[f"board{board}"]["map"], ch)
        if pos == None: 
            continue
        
        h_Ene_FERS_LG[ch] = ROOT.TH1F(f"h_Ene_FERS_LG_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        values = all_fers_lg[branch_name_lg][:, ch]
        values_arr = array("d", values)   # convert to C array    
        weights = array("d", np.ones_like(values))  # all weights = 1
        h_Ene_FERS_LG[ch].FillN(len(values), values_arr, weights)

        cFERS_LG = ROOT.TCanvas("c%s_ch%d"%(branch_name_lg,ch),"c%s_ch%d"%(branch_name_lg,ch), 500, 500)
        h_Ene_FERS_LG[ch].Draw()
        cFERS_LG.SaveAs("%s/c%s_ch%d.png"%(path_plots_fers,branch_name_lg,ch))

        
        h_Ene_FERS_HG[ch] = ROOT.TH1F(f"h_Ene_FERS_HG_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        values = all_fers_hg[branch_name_hg][:, ch]
        values_arr = array("d", values)   # convert to C array    
        weights = array("d", np.ones_like(values))  # all weights = 1
        h_Ene_FERS_HG[ch].FillN(len(values), values_arr, weights)

        cFERS_HG = ROOT.TCanvas("c%s_ch%d"%(branch_name_hg,ch),"c%s_ch%d"%(branch_name_hg,ch), 500, 500)
        h_Ene_FERS_HG[ch].Draw()
        cFERS_HG.SaveAs("%s/c%s_ch%d.png"%(path_plots_fers,branch_name_hg,ch))
        
        h2_Map_FERS_HG[branch_name_hg].Fill(pos[0], pos[1], np.mean(values))


    cMAP_FERS_HG = ROOT.TCanvas("cMAP_%s"%branch_name_hg,"cMAP_%s"%branch_name_hg, 700, 700)
    h2_Map_FERS_HG[branch_name_hg].SetStats(0)
    h2_Map_FERS_HG[branch_name_hg].Draw("COLZ")
    cMAP_FERS_HG.SetGrid(1,1)
    cMAP_FERS_HG.SaveAs("%s/cMAP_%s.png"%(path_plots,branch_name_hg))


    
    



#write reco output root file
save_root_tree(results, beamX, beamY, "%s/reco_run%04d.root"%(path_reco, run_id))

print("dqm completed for run: ", run_id)

ROOT.gROOT.GetListOfCanvases().Delete()

#input()

