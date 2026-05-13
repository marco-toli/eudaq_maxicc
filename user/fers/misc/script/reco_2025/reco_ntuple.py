import ROOT
import sys
import numpy as np
from array import array
import os
import json
import argparse
from analysis_functions import get_pedestal, get_gr_ch, get_times, template_fit, get_aligned_waveforms
from tree_init import find_position_in_map, init_info_tree, init_evt_tree, init_drs_tree, init_fers_tree, fill_info_tree_from_logbook
import pandas as pd
from collections import defaultdict
os.environ["OPENBLAS_NUM_THREADS"] = "1"


ROOT.gROOT.Reset()
ROOT.gROOT.SetBatch(True)

# Create the parser
parser = argparse.ArgumentParser(description="DQM RECO")

# Add arguments
parser.add_argument('--run', type=int, help='Run number')
parser.add_argument('--config', type=str, default="reco_config_drs.json", help='Reco json config file')
parser.add_argument('--prescale', type=int, default=1, help='1/fraction of events to be analyzed: 1 all, 10=1/10')
parser.add_argument('--makeplots', type=int, default=0, help='0 to not make plots, 1 to make DQM plots')

# Parse the arguments
args = parser.parse_args()

# Load config
with open(args.config, 'r') as f:
    config = json.load(f)

# Read logbook info
readFromLogbook = True
logbook = "MAXICC_CERN_Sept2025_TB_Logbook.xlsx"
tree_info = fill_info_tree_from_logbook(args.run, logbook)

#tree_info.Fill()


# Read digitizer and FERS info
nDigiGroups = 0
digiCh = []
nFersBoards = 0

digitizer = config.get("digitizer", {})
fers = config.get("fers", {})

# Count digitizer groups and channels
group_keys = [key for key in digitizer.keys() if key.startswith("group")]
nDigiGroups = len(group_keys)
print(f"Number of groups in json: {nDigiGroups}")
for group in group_keys:
    ch_keys = [key for key in digitizer[group].keys() if key.startswith("ch")]
    digiCh.append(ch_keys)
    print(f"{group} has {len(ch_keys)} channels: {ch_keys}")

# Count FERS boards
board_keys = [key for key in fers.keys() if key.startswith("board")]
nFersBoards = len(board_keys)
print(f"Number of FERS boards in json: {nFersBoards}")

# Input/output paths
run_id = args.run
path_plots = f"/var/www/html/MAXICC/run_{run_id}"
path_plots_drs = f"{path_plots}/drs/"
path_plots_fers = f"{path_plots}/fers/"
path_reco = "/mnt/mybook/MAXICC/CERNTB_Sept2025/data/reco/"

# path_plots = f"/home/toli/cernbox/WORKAREA/MAXICC/CERNTBSeptember2025/plots/run_{run_id}"
# path_plots_drs = f"{path_plots}/drs/"
# path_plots_fers = f"{path_plots}/fers/"
# path_reco = "/home/toli/cernbox/WORKAREA/MAXICC/CERNTBSeptember2025/reco/"

os.makedirs(path_plots, exist_ok=True)
os.makedirs(path_plots_drs, exist_ok=True)
os.makedirs(path_plots_fers, exist_ok=True)

file = ROOT.TFile.Open(f"/mnt/mybook/MAXICC/CERNTB_Sept2025/data/root/run{run_id:04d}.root")
#file = ROOT.TFile.Open(f"/home/toli/cernbox/WORKAREA/MAXICC/CERNTBSeptember2025/root/run{run_id:04d}.root")
out_file = ROOT.TFile(f"{path_reco}/reco_run{run_id:04d}.root", "RECREATE")
                      
# Read tree
all_wf = {}
all_fers_hg = {}
all_fers_lg = {}

tree = file.Get("EventTree")
nentries = tree.GetEntries()

for i, event in enumerate(tree):
    if i % args.prescale != 0:
        continue

    if i % 1000 == 0:  # print every 1000 events
        percent = 100.0 * i / nentries
        sys.stdout.write(f"\rProcessing event {i}/{nentries} ({percent:.1f}%)")
        sys.stdout.flush()

    # Digitizer branches
    for group in range(nDigiGroups):
        for ch in digiCh[group]:
            #print(f"Reading data from DRS group: {group} - ch {ch[2:]}")
            branch_name = f"DRS_Board0_Group{group}_Channel{ch[2:]}"
            if not hasattr(tree, branch_name):
                if i == 0:
                    print(f"Branch {branch_name} does not exist --> check your config file!")
                continue

            if i == 0:
                all_wf[branch_name] = []

            all_wf[branch_name].append(np.array(list(getattr(event, branch_name))))

    # FERS branches
    for board in range(nFersBoards):
        #print(f"Reading data from FERS board: {board}")
        branch_name_hg = f"FERS_Board{board}_energyHG"
        branch_name_lg = f"FERS_Board{board}_energyLG"

        if not hasattr(tree, branch_name_hg):
            if i == 0:
                print(f"Branch {branch_name_hg} does not exist --> check your config file!")
            continue

        if i == 0:
            all_fers_hg[branch_name_hg] = []
            all_fers_lg[branch_name_lg] = []

        all_fers_hg[branch_name_hg].append(np.array(list(getattr(event, branch_name_hg))))
        all_fers_lg[branch_name_lg].append(np.array(list(getattr(event, branch_name_lg))))

file.Close()

print("All data have been readout from root file!")
print("Now, start processing...")

#-------------------------------------------------------
# Analyze digitizer waveforms
#-------------------------------------------------------
results = {}
gWf2 = {}
gWf = {}
gWfAligned = {}
h_maxAmp_DRS = {}
h_integral_DRS = {}
h_times_DRS = {}

wc_names = {"wcL": "", "wcR": "", "wcT": "", "wcB": ""}

for branch_name, waveforms in all_wf.items():
    group, ch = get_gr_ch(branch_name)
    waveforms = np.array(waveforms)

    #define time axis
    nSamples = waveforms.shape[1]
    dt = 1.0  # ns per sample, for example
    times = np.arange(nSamples) * dt

    #define integration window
    t_min, t_max = 200, 1000
    mask = (times >= t_min) & (times <= t_max)
    
    
    pedestals = get_pedestal(waveforms)
    polarity  = digitizer[f"group{group}"][f"ch{ch}"]["polarity"]
    sigtype   = digitizer[f"group{group}"][f"ch{ch}"]["type"]
    waveforms = (waveforms - pedestals[:, None]) * polarity

    if sigtype in wc_names:
        wc_names[sigtype] = branch_name
        
    avg_waveform = np.mean(waveforms, axis=0)       
    maxamp       = np.max(waveforms, axis=1)
    
#    integral     = np.sum(waveforms, axis=1)
    integral = np.sum(waveforms[:, mask], axis=1)*dt
    times        = get_times(waveforms, thresholds=maxamp*0.5)

    aligned_waveforms = get_aligned_waveforms(waveforms, times, maxamp, dt=1.0, amp_threshold=100 )
    avg_waveform_aligned = np.mean(aligned_waveforms, axis=0)

    # template = np.mean(aligned_waveforms, axis=0)
    # template /= np.max(template)  # normalize to 1
    # maxfit, tfit = zip(*[template_fit(wf, template) for wf in waveforms])
    # maxfit = np.array(maxfit)
    # tfit  = np.array(tfit)
    
    results[branch_name] = {
        "waveforms": waveforms,
        "avg_waveform": avg_waveform,
        "avg_waveform_aligned": avg_waveform_aligned,
        "pedestals": pedestals,
        "maxamp": maxamp,
        "integral": integral,
        "times": times
    }

    # Plotting: individual and average waveforms
    num_samples = avg_waveform.shape[0]
    x = array("d", np.arange(num_samples))
    y_avg = array("d", avg_waveform)   
    gWf[branch_name] = ROOT.TGraph(num_samples, x, y_avg)

    num_samples_al = avg_waveform_aligned.shape[0] 
    x_al = array("d", np.arange(num_samples_al))
    y_avg_aligned = array("d", avg_waveform_aligned)        
    gWfAligned[branch_name] = ROOT.TGraph(num_samples_al, x_al, y_avg_aligned)    
    gWfAligned[branch_name].SetTitle(f"{branch_name};Sample;Amplitude (V)")
    gWfAligned[branch_name].GetXaxis().SetLimits(0,1000)
    gWfAligned[branch_name].SetLineColor(ROOT.kBlue)
    gWfAligned[branch_name].SetMarkerColor(ROOT.kBlue)
    gWfAligned[branch_name].SetLineWidth(2)
    
    cAvgWf = ROOT.TCanvas(f"cAvgWf_{branch_name}", f"cAvgWf_{branch_name}", 500, 500)
    gWfAligned[branch_name].Draw("ALPE")    
    gWf[branch_name].SetLineColor(1)    
    gWf[branch_name].Draw("same LE")
    
    if(args.makeplots!=0): 
        cAvgWf.SaveAs(f"{path_plots_drs}/cAvgWf_{branch_name}.png")
    del cAvgWf
    

    # Max amplitude histogram
    h_maxAmp_DRS[branch_name] = ROOT.TH1F(f"h_maxAmp_DRS_gr{group}_ch{ch}", f"h_maxAmp_DRS_gr{group}_ch{ch}", 4096, 0, 4096)
    h_maxAmp_DRS[branch_name].FillN(len(maxamp), maxamp, np.ones_like(maxamp))
    cMaxAmp = ROOT.TCanvas(f"cMaxAmp_{branch_name}", f"cMaxAmp_{branch_name}", 500, 500)
    h_maxAmp_DRS[branch_name].Draw()
    cMaxAmp.SetLogy()
    if(args.makeplots!=0): 
        cMaxAmp.SaveAs(f"{path_plots_drs}/cMaxAmp_{branch_name}.png")
    del cMaxAmp
    
    # Integral histogram
    h_integral_DRS[branch_name] = ROOT.TH1F(f"h_integral_DRS_gr{group}_ch{ch}", f"h_integral_DRS_gr{group}_ch{ch}", 4096, 0, 4096*200)
    h_integral_DRS[branch_name].FillN(len(integral), integral, np.ones_like(integral))
    cIntegral = ROOT.TCanvas(f"cIntegral_{branch_name}", f"cIntegral_{branch_name}", 500, 500)
    h_integral_DRS[branch_name].Draw()
    cIntegral.SetLogy()
    if(args.makeplots!=0): 
        cIntegral.SaveAs(f"{path_plots_drs}/cIntegral_{branch_name}.png")
    del cIntegral

    # Times histogram
    h_times_DRS[branch_name] = ROOT.TH1F(f"h_times_DRS_gr{group}_ch{ch}", f"h_times_DRS_gr{group}_ch{ch}", 4096, 0, 1024)
    h_times_DRS[branch_name].FillN(len(times), times, np.ones_like(times))
    cTimes = ROOT.TCanvas(f"cTimes_{branch_name}", f"cTimes_{branch_name}", 500, 500)
    h_times_DRS[branch_name].Draw()
    cTimes.SetLogy()
    if(args.makeplots!=0): 
        cTimes.SaveAs(f"{path_plots_drs}/cTimes_{branch_name}.png")
    del cTimes
    


print("Now reconstructing beam position...")

chList = [4]
#-------------------------------------------------------
# Filter WC channels and mark bad events instead of masking
#-------------------------------------------------------
wc_branches = [wc_names[k] for k in ["wcL","wcR","wcT","wcB"] if wc_names[k] != ""]
if len(wc_branches) == 4:
    # Costruisci la maschera dei "buoni"
    masks = [
        (results[b]["maxamp"] >= 100)
        & (results[b]["integral"] < 100e3)
        & (results[b]["times"] < 650)
        & (results[b]["times"] > 350)
        for b in wc_branches
    ]
    common_mask = np.logical_and.reduce(masks)

    print(f"Selected {np.count_nonzero(common_mask)} good events out of {len(common_mask)}")

#-------------------------------------------------------
# Compute beam positions with sentinel values for bad events
#-------------------------------------------------------
WC_calibX = 0.00450
WC_calibY = 0.00453

# Inizializza array beamX, beamY a -999
n_events = len(results[wc_names["wcR"]]["times"])
beamX = np.full(n_events, -999.0, dtype=float)
beamY = np.full(n_events, -999.0, dtype=float)

# Calcola solo per eventi buoni
good_idx = np.where(common_mask)[0]
beamX[good_idx] = (
    (results[wc_names["wcR"]]["times"][good_idx] - results[wc_names["wcL"]]["times"][good_idx])
    * WC_calibX * 40
)
beamY[good_idx] = (
    (results[wc_names["wcT"]]["times"][good_idx] - results[wc_names["wcB"]]["times"][good_idx])
    * WC_calibY * 40
)


print("len beamX = ", len(beamX))

# Beam histograms
h_beamX = ROOT.TH1F("h_beamX","h_beamX", 100, -50, 50)
h_beamX.FillN(len(beamX), beamX, np.ones_like(beamX))
cBeamX = ROOT.TCanvas("cBeamX","cBeamX",500,500)
h_beamX.Draw()
if(args.makeplots!=0): cBeamX.SaveAs(f"{path_plots}/cBeamX.png")

h_beamY = ROOT.TH1F("h_beamY","h_beamY", 100, -50, 50)
h_beamY.FillN(len(beamY), beamY, np.ones_like(beamY))
cBeamY = ROOT.TCanvas("cBeamY","cBeamY",500,500)
h_beamY.Draw()
if(args.makeplots!=0): cBeamY.SaveAs(f"{path_plots}/cBeamY.png")

h2_beamXY = ROOT.TH2F("h2_beamXY","h2_beamXY", 100, -50, 50, 100, -50, 50)
h2_beamXY.FillN(len(beamX), beamX, beamY, np.ones_like(beamX))
cBeamXY = ROOT.TCanvas("cBeamXY","cBeamXY",500,500)
h2_beamXY.Draw("COLZ")
if(args.makeplots!=0): cBeamXY.SaveAs(f"{path_plots}/cBeamXY.png")


print("Now saving to output root file...")
# initialize evt and drs tree
if (nDigiGroups!=0):
    tree_evt = init_evt_tree()
    tree_drs = init_drs_tree()

if (nFersBoards!=0):
    # tree_fers, vars_fers = init_fers_tree(nFers=nFersBoards)
    tree_fers = init_fers_tree(nFers=nFersBoards)


# Loop over events
nEvents = len(beamX)  # e.g. use number of valid beam events
for i in range(nEvents):
    # --- Fill evtTree ---
    tree_evt.evt_id[0] = i
    tree_evt.t_beamX[0] = float(beamX[i])
    tree_evt.t_beamY[0] = float(beamY[i])
    tree_evt.Fill()

    # -----------------------
    # Fill drsTree
    # -----------------------
    tree_drs.evt_ref[0] = i

    # Here you select which channel’s results to store (example: first 8 valid channels)
    # You can adjust this mapping based on your analysis structure

    for j in range(8):
        # Example: pick one waveform channel per array index
        branch_name = f"DRS_Board0_Group0_Channel{j}"
        if branch_name not in results:
            tree_drs.t_ped[j] = -999
            tree_drs.t_amp[j] = -999
            tree_drs.t_int[j] = -999
            tree_drs.t_time1[j] = -999
            continue

        # Each quantity is a per-event array, so index with [i]
        if i < len(results[branch_name]["maxamp"]):
            tree_drs.t_ped[j]   = results[branch_name]["pedestals"][i]
            tree_drs.t_amp[j]   = results[branch_name]["maxamp"][i]
            tree_drs.t_int[j]   = results[branch_name]["integral"][i]
            tree_drs.t_time1[j] = results[branch_name]["times"][i]
        else:
            tree_drs.t_pde[j] = -999
            tree_drs.t_amp[j] = -999
            tree_drs.t_int[j] = -999
            tree_drs.t_time1[j] = -999

    tree_drs.Fill()

    # -----------------------
    # Fill fersTree
    # -----------------------
    if nFersBoards > 0:
        tree_fers.evt_ref[0] = i
        for board in range(nFersBoards):
            branch_name_hg = f"FERS_Board{board}_energyHG"
            branch_name_lg = f"FERS_Board{board}_energyLG"
            if branch_name_hg not in all_fers_hg:
                continue

            for ch in range(64):
                idx = board * 64 + ch  # flat index across boards
                tree_fers.t_hg[idx] = all_fers_hg[branch_name_hg][i][ch]
                tree_fers.t_lg[idx] = all_fers_lg[branch_name_lg][i][ch]
        #print("filling fers tree for event ", i)
        tree_fers.Fill()

# Write output file
out_file.cd()

tree_info.Write()
if (nDigiGroups!=0):
    tree_evt.Write()
    tree_drs.Write()
if (nFersBoards!=0):
    tree_fers.Write()

out_file.Close()
print("*****************************\n Output reco file written!\n*****************************")



# Trigger-based 2D histogram

for ch in chList:
    trigger_name = f"DRS_Board0_Group0_Channel{ch}"
    p2_Amp_vs_Pos = ROOT.TProfile2D(f"p2_Amp{ch}_vs_Pos",f"p2_Amp{ch}_vs_Pos",
                                100, -50, 50, 100, -50, 50)

    amps = np.array(results[trigger_name]["maxamp"], dtype=float)
    print("len amps = ", len(amps))
    for x, y, amp in zip(beamX, beamY, amps):
#        print(x,y,amp,amp>150.)
        p2_Amp_vs_Pos.Fill(x, y, amp>150.)
#        p2_Amp_vs_Pos.Fill(x, y, amp)

    cname = f"cAmp{ch}_vs_Pos"
    cAmp_vs_Pos = ROOT.TCanvas(cname,cname,500,500)
#    p2_Amp_vs_Pos.GetZaxis().SetRangeUser(0.,1.)
    p2_Amp_vs_Pos.Draw("COLZ")
    if(args.makeplots!=0): 
        cAmp_vs_Pos.SaveAs(f"{path_plots}/cAmp{ch}_vs_Pos_ch.png")
    del cAmp_vs_Pos

#-------------------------------------------------------
# Analyze FERS data
#-------------------------------------------------------
h_Ene_FERS_LG = {}
h_Ene_FERS_HG = {}
h2_Map_FERS_LG = {}
h2_Map_FERS_HG = {}

chFERSmask = defaultdict(list)
chFERSmask[0] = [21,26,28,33,34,39,43,46,36]
chFERSmask[2] =[33,35]


for board in range(len(all_fers_hg.items())):
    branch_name_hg = f"FERS_Board{board}_energyHG"
    branch_name_lg = f"FERS_Board{board}_energyLG"
    all_fers_hg[branch_name_hg] = np.vstack(all_fers_hg[branch_name_hg])
    all_fers_lg[branch_name_lg] = np.vstack(all_fers_lg[branch_name_lg])
    h2_Map_FERS_LG[branch_name_lg] = ROOT.TH2F(f"hMAP_{branch_name_lg}", f"hMAP_{branch_name_lg};X;Y", 9,0,9,9,0,9)
    h2_Map_FERS_HG[branch_name_hg] = ROOT.TH2F(f"hMAP_{branch_name_hg}", f"hMAP_{branch_name_hg};X;Y", 9,0,9,9,0,9)

    if (board == 1):
        continue
    
    for ch in range(all_fers_lg[branch_name_lg].shape[1]):
        pos = find_position_in_map(fers[f"board{board}"]["map"], ch)
    #    print(pos)
    #     if pos is None: 
    #         continue

        # LG
        h_Ene_FERS_LG[ch] = ROOT.TH1F(f"h_Ene_FERS_LG_board{board}_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        valuesLG = all_fers_lg[branch_name_lg][:, ch]
        h_Ene_FERS_LG[ch].FillN(len(valuesLG), array("d", valuesLG), array("d", np.ones_like(valuesLG)))
        
        # HG
        h_Ene_FERS_HG[ch] = ROOT.TH1F(f"h_Ene_FERS_HG_board{board}_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        valuesHG = all_fers_hg[branch_name_hg][:, ch]
        h_Ene_FERS_HG[ch].FillN(len(valuesHG), array("d", valuesHG), array("d", np.ones_like(valuesHG)))

        if (pos is not None):
            h2_Map_FERS_LG[branch_name_lg].Fill(pos[0], pos[1], np.mean(valuesLG))
            h2_Map_FERS_HG[branch_name_hg].Fill(pos[0], pos[1], np.mean(valuesHG))
        
        if (ch not in chFERSmask[board]):
            continue


        cFERS_LG = ROOT.TCanvas(f"c{branch_name_lg}_ch{ch}", f"c{branch_name_lg}_ch{ch}", 500, 500)
        h_Ene_FERS_LG[ch].Draw()
        cFERS_LG.SetLogy()        
        if(args.makeplots!=0): 
            cFERS_LG.SaveAs(f"{path_plots_fers}/{branch_name_lg}_ch{ch}.png")
        del cFERS_LG
        del h_Ene_FERS_LG[ch]
        
        cFERS_HG = ROOT.TCanvas(f"c{branch_name_hg}_ch{ch}", f"c{branch_name_hg}_ch{ch}", 500, 500)
        h_Ene_FERS_HG[ch].Draw()
        cFERS_HG.SetLogy()
        if(args.makeplots!=0): 
            cFERS_HG.SaveAs(f"{path_plots_fers}/{branch_name_hg}_ch{ch}.png")
        del cFERS_HG
        del h_Ene_FERS_HG[ch]
                
        p2_AmpFERS_vs_Pos = ROOT.TProfile2D(f"p2_Amp{branch_name_hg}_ch{ch}_vs_Pos",f"p2_Amp{branch_name_hg}_ch{ch}_vs_Pos",
                                100, -50, 50, 100, -50, 50)
        
#        amps = np.array(results[trigger_name]["maxamp"], dtype=float)
        for x, y, amp in zip(beamX, beamY, valuesLG):
            p2_AmpFERS_vs_Pos.Fill(x, y, amp>1000.)
        cname = f"{branch_name_hg}_ch{ch}"
        cAmpFERS_vs_Pos = ROOT.TCanvas(cname,cname,500,500)
            #    p2_Amp_vs_Pos.GetZaxis().SetRangeUser(0.,1.)
        p2_AmpFERS_vs_Pos.Draw("COLZ")
        if(args.makeplots!=0): 
            cAmpFERS_vs_Pos.SaveAs(f"{path_plots}/cAmp{cname}_vs_Pos.png")
        del cAmpFERS_vs_Pos

        
    # Map HG
#    h2_Map_FERS_HG[branch_name_hg].Fill(pos[0], pos[1], np.mean(values))
    cMAP_FERS_HG = ROOT.TCanvas(f"cMAP_{branch_name_hg}", f"cMAP_{branch_name_hg}", 700, 700)
    h2_Map_FERS_HG[branch_name_hg].SetStats(0)
    h2_Map_FERS_HG[branch_name_hg].Draw("COLZ")
    cMAP_FERS_HG.SetGrid(1,1)
    if(args.makeplots!=0): cMAP_FERS_HG.SaveAs(f"{path_plots}/{branch_name_hg}.png")
    cMAP_FERS_HG.SetLogz()
    if(args.makeplots!=0): 
        cMAP_FERS_HG.SaveAs(f"{path_plots}/{branch_name_hg}_Log.png")    
    del cMAP_FERS_HG

    cMAP_FERS_LG = ROOT.TCanvas(f"cMAP_{branch_name_lg}", f"cMAP_{branch_name_lg}", 700, 700)
    h2_Map_FERS_LG[branch_name_lg].SetStats(0)
    h2_Map_FERS_LG[branch_name_lg].Draw("COLZ")
    cMAP_FERS_LG.SetGrid(1,1)
    if(args.makeplots!=0): cMAP_FERS_LG.SaveAs(f"{path_plots}/{branch_name_lg}.png")
    cMAP_FERS_LG.SetLogz()
    if(args.makeplots!=0): 
        cMAP_FERS_LG.SaveAs(f"{path_plots}/{branch_name_lg}_Log.png")    
    del cMAP_FERS_LG

 
print("dqm completed for run: ", run_id)
ROOT.gROOT.GetListOfCanvases().Clear()
ROOT.gROOT.GetListOfCanvases().Delete()
#ROOT.gDirectory.GetList().Delete()

