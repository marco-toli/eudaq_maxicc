import ROOT
import numpy as np
from array import array
import os
import json
import argparse
from analysis_functions import get_pedestal, get_gr_ch, get_times
from tree_init import save_root_tree, find_position_in_map
os.environ["OPENBLAS_NUM_THREADS"] = "1"


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

# Load config
with open(args.config, 'r') as f:
    config = json.load(f)

# Read digitizer and FERS info
nDigiGroups = 0
nDigiCh = []
nFersBoards = 0

digitizer = config.get("digitizer", {})
fers = config.get("fers", {})

# Count digitizer groups and channels
group_keys = [key for key in digitizer.keys() if key.startswith("group")]
nDigiGroups = len(group_keys)
print(f"Number of groups in json: {nDigiGroups}")
for group in group_keys:
    ch_keys = [key for key in digitizer[group].keys() if key.startswith("ch")]
    nDigiCh.append(len(ch_keys))
    print(f"{group} has {len(ch_keys)} channels")

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
os.makedirs(path_plots, exist_ok=True)
os.makedirs(path_plots_drs, exist_ok=True)
os.makedirs(path_plots_fers, exist_ok=True)

file = ROOT.TFile.Open(f"/mnt/mybook/MAXICC/CERNTB_Sept2025/data/root/run{run_id:04d}.root")

# Read tree
all_wf = {}
all_fers_hg = {}
all_fers_lg = {}

tree = file.Get("EventTree")

for i, event in enumerate(tree):
    if i % args.prescale != 0:
        continue

    # Digitizer branches
    for group in range(nDigiGroups):
        for ch in range(nDigiCh[group]):
            branch_name = f"DRS_Board0_Group{group}_Channel{ch}"
            if not hasattr(tree, branch_name):
                if i == 0:
                    print(f"Branch {branch_name} does not exist --> check your config file!")
                continue

            if i == 0:
                all_wf[branch_name] = []

            all_wf[branch_name].append(np.array(list(getattr(event, branch_name))))

    # FERS branches
    for board in range(nFersBoards):
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

#-------------------------------------------------------
# Analyze digitizer waveforms
#-------------------------------------------------------
results = {}
gWf2 = {}
gWf = {}
h_maxAmp_DRS = {}
h_integral_DRS = {}
h_times_DRS = {}

wc_names = {"wcL": "", "wcR": "", "wcT": "", "wcB": ""}

for branch_name, waveforms in all_wf.items():
    group, ch = get_gr_ch(branch_name)
    waveforms = np.array(waveforms)
    pedestals = get_pedestal(waveforms)
    polarity  = digitizer[f"group{group}"][f"ch{ch}"]["polarity"]
    sigtype   = digitizer[f"group{group}"][f"ch{ch}"]["type"]
    waveforms = (waveforms - pedestals[:, None]) * polarity

    if sigtype in wc_names:
        wc_names[sigtype] = branch_name

    avg_waveform = np.mean(waveforms, axis=0)
    maxamp       = np.max(waveforms, axis=1)
    integral     = np.sum(waveforms, axis=1)
    times        = get_times(waveforms, thresholds=maxamp*0.5)

    results[branch_name] = {
        "waveforms": waveforms,
        "avg_waveform": avg_waveform,
        "maxamp": maxamp,
        "integral": integral,
        "times": times
    }

    # Plotting: individual and average waveforms
    num_samples = avg_waveform.shape[0]
    x = array("d", np.arange(num_samples))
    y_avg = array("d", avg_waveform)
    gWf[branch_name] = ROOT.TGraph(num_samples, x, y_avg)
    gWf[branch_name].SetTitle(f"{branch_name};Sample;Amplitude (V)")
    gWf[branch_name].SetLineColor(ROOT.kBlue)
    gWf[branch_name].SetLineWidth(2)
    cAvgWf = ROOT.TCanvas(f"cAvgWf_{branch_name}", f"cAvgWf_{branch_name}", 500, 500)
    gWf[branch_name].Draw("ALPE")
    cAvgWf.SaveAs(f"{path_plots_drs}/cAvgWf_{branch_name}.png")
    del cAvgWf

    # Max amplitude histogram
    h_maxAmp_DRS[branch_name] = ROOT.TH1F(f"h_maxAmp_DRS_gr{group}_ch{ch}", f"h_maxAmp_DRS_gr{group}_ch{ch}", 4096, 0, 4096)
    h_maxAmp_DRS[branch_name].FillN(len(maxamp), maxamp, np.ones_like(maxamp))
    cMaxAmp = ROOT.TCanvas(f"cMaxAmp_{branch_name}", f"cMaxAmp_{branch_name}", 500, 500)
    h_maxAmp_DRS[branch_name].Draw()
    cMaxAmp.SetLogy()
    cMaxAmp.SaveAs(f"{path_plots_drs}/cMaxAmp_{branch_name}.png")
    del cMaxAmp

    # Integral histogram
    h_integral_DRS[branch_name] = ROOT.TH1F(f"h_integral_DRS_gr{group}_ch{ch}", f"h_integral_DRS_gr{group}_ch{ch}", 4096, 0, 4096*200)
    h_integral_DRS[branch_name].FillN(len(integral), integral, np.ones_like(integral))
    cIntegral = ROOT.TCanvas(f"cIntegral_{branch_name}", f"cIntegral_{branch_name}", 500, 500)
    h_integral_DRS[branch_name].Draw()
    cIntegral.SetLogy()
    cIntegral.SaveAs(f"{path_plots_drs}/cIntegral_{branch_name}.png")
    del cIntegral

    # Times histogram
    h_times_DRS[branch_name] = ROOT.TH1F(f"h_times_DRS_gr{group}_ch{ch}", f"h_times_DRS_gr{group}_ch{ch}", 4096, 0, 1024)
    h_times_DRS[branch_name].FillN(len(times), times, np.ones_like(times))
    cTimes = ROOT.TCanvas(f"cTimes_{branch_name}", f"cTimes_{branch_name}", 500, 500)
    h_times_DRS[branch_name].Draw()
    cTimes.SetLogy()
    cTimes.SaveAs(f"{path_plots_drs}/cTimes_{branch_name}.png")
    del cTimes



chList = [4]
#-------------------------------------------------------
# Filter WC channels with common maxamp >= 100
#-------------------------------------------------------
wc_branches = [wc_names[k] for k in ["wcL","wcR","wcT","wcB"] if wc_names[k] != ""]
if len(wc_branches) == 4:
#    masks = [results[b]["maxamp"] >= 100 for b in wc_branches]
    masks = [(results[b]["maxamp"] >= 100) & (results[b]["integral"] < 100e3) & (results[b]["times"] < 650) &(results[b]["times"] > 350) for b in wc_branches]
    common_mask = np.logical_and.reduce(masks)
    for b in wc_branches:
        for key in ["waveforms","maxamp","integral","times"]:
            results[b][key] = results[b][key][common_mask]
    for key in ["waveforms","maxamp","integral","times"]:
        for ch in chList:
            results[f"DRS_Board0_Group0_Channel{ch}"][key] = results[f"DRS_Board0_Group0_Channel{ch}"][key][common_mask]            


#-------------------------------------------------------
# Compute beam positions
#-------------------------------------------------------
WC_calibX = 0.00450
WC_calibY = 0.00453

beamX = (results[wc_names["wcR"]]["times"] - results[wc_names["wcL"]]["times"]) * WC_calibX * 40
beamY = (results[wc_names["wcT"]]["times"] - results[wc_names["wcB"]]["times"]) * WC_calibY * 40

print("len beamX = ", len(beamX))

# Beam histograms
h_beamX = ROOT.TH1F("h_beamX","h_beamX", 100, -50, 50)
h_beamX.FillN(len(beamX), beamX, np.ones_like(beamX))
cBeamX = ROOT.TCanvas("cBeamX","cBeamX",500,500)
h_beamX.Draw()
cBeamX.SaveAs(f"{path_plots}/cBeamX.png")

h_beamY = ROOT.TH1F("h_beamY","h_beamY", 100, -50, 50)
h_beamY.FillN(len(beamY), beamY, np.ones_like(beamY))
cBeamY = ROOT.TCanvas("cBeamY","cBeamY",500,500)
h_beamY.Draw()
cBeamY.SaveAs(f"{path_plots}/cBeamY.png")

h2_beamXY = ROOT.TH2F("h2_beamXY","h2_beamXY", 100, -50, 50, 100, -50, 50)
h2_beamXY.FillN(len(beamX), beamX, beamY, np.ones_like(beamX))
cBeamXY = ROOT.TCanvas("cBeamXY","cBeamXY",500,500)
h2_beamXY.Draw("COLZ")
cBeamXY.SaveAs(f"{path_plots}/cBeamXY.png")


# Trigger-based 2D histogram


for ch in chList:
    trigger_name = f"DRS_Board0_Group0_Channel{ch}"
    p2_Amp_vs_Pos = ROOT.TProfile2D(f"p2_Amp{ch}_vs_Pos",f"p2_Amp{ch}_vs_Pos",
                                100, -50, 50, 100, -50, 50)

    amps = np.array(results[trigger_name]["maxamp"], dtype=float)
    for x, y, amp in zip(beamX, beamY, amps):
#        print(x,y,amp,amp>150.)
        p2_Amp_vs_Pos.Fill(x, y, amp>150.)
#        p2_Amp_vs_Pos.Fill(x, y, amp)

    cname = f"cAmp{ch}_vs_Pos"
    cAmp_vs_Pos = ROOT.TCanvas(cname,cname,500,500)
#    p2_Amp_vs_Pos.GetZaxis().SetRangeUser(0.,1.)
    p2_Amp_vs_Pos.Draw("COLZ")
    cAmp_vs_Pos.SaveAs(f"{path_plots}/cAmp{ch}_vs_Pos_ch.png")
    del cAmp_vs_Pos

#-------------------------------------------------------
# Analyze FERS data
#-------------------------------------------------------
h_Ene_FERS_LG = {}
h_Ene_FERS_HG = {}
h2_Map_FERS_LG = {}
h2_Map_FERS_HG = {}

chFERSmask = [21,26,28,33,34,39,43,46,29,35,36]

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
        print(pos)
    #     if pos is None: 
    #         continue

        # LG
        h_Ene_FERS_LG[ch] = ROOT.TH1F(f"h_Ene_FERS_LG_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        valuesLG = all_fers_lg[branch_name_lg][:, ch]
        h_Ene_FERS_LG[ch].FillN(len(valuesLG), array("d", valuesLG), array("d", np.ones_like(valuesLG)))
        
        # HG
        h_Ene_FERS_HG[ch] = ROOT.TH1F(f"h_Ene_FERS_HG_{ch}", f"Channel {ch};Value;Counts", 8000, 0, 8000)
        valuesHG = all_fers_hg[branch_name_hg][:, ch]
        h_Ene_FERS_HG[ch].FillN(len(valuesHG), array("d", valuesHG), array("d", np.ones_like(valuesHG)))

        if (pos is not None):
            h2_Map_FERS_LG[branch_name_lg].Fill(pos[0], pos[1], np.mean(valuesLG))
            h2_Map_FERS_HG[branch_name_hg].Fill(pos[0], pos[1], np.mean(valuesHG))
        
        if (ch not in chFERSmask):
            continue


        cFERS_LG = ROOT.TCanvas(f"c{branch_name_lg}_ch{ch}", f"c{branch_name_lg}_ch{ch}", 500, 500)
        h_Ene_FERS_LG[ch].Draw()
        cFERS_LG.SetLogy()        
        cFERS_LG.SaveAs(f"{path_plots_fers}/{branch_name_lg}_ch{ch}.png")
        del cFERS_LG
        del h_Ene_FERS_LG[ch]
        
        cFERS_HG = ROOT.TCanvas(f"c{branch_name_hg}_ch{ch}", f"c{branch_name_hg}_ch{ch}", 500, 500)
        h_Ene_FERS_HG[ch].Draw()
        cFERS_HG.SetLogy()
        cFERS_HG.SaveAs(f"{path_plots_fers}/{branch_name_hg}_ch{ch}.png")
        del cFERS_HG
        del h_Ene_FERS_HG[ch]
                
        p2_AmpFERS_vs_Pos = ROOT.TProfile2D(f"p2_Amp{branch_name_hg}_ch{ch}_vs_Pos",f"p2_Amp{branch_name_hg}_ch{ch}_vs_Pos",
                                100, -50, 50, 100, -50, 50)

#        amps = np.array(results[trigger_name]["maxamp"], dtype=float)
        for x, y, amp in zip(beamX, beamY, valuesLG):
            #        print(x,y,amp,amp>150.)
            p2_AmpFERS_vs_Pos.Fill(x, y, amp>1000.)
            #        p2_Amp_vs_Pos.Fill(x, y, amp)
        cname = f"{branch_name_hg}_ch{ch}"
        cAmpFERS_vs_Pos = ROOT.TCanvas(cname,cname,500,500)
            #    p2_Amp_vs_Pos.GetZaxis().SetRangeUser(0.,1.)
        p2_AmpFERS_vs_Pos.Draw("COLZ")
        cAmpFERS_vs_Pos.SaveAs(f"{path_plots}/cAmpFERS{cname}_vs_Pos.png")
        del cAmpFERS_vs_Pos

        
    # Map HG
#    h2_Map_FERS_HG[branch_name_hg].Fill(pos[0], pos[1], np.mean(values))
    cMAP_FERS_HG = ROOT.TCanvas(f"cMAP_{branch_name_hg}", f"cMAP_{branch_name_hg}", 700, 700)
    h2_Map_FERS_HG[branch_name_hg].SetStats(0)
    h2_Map_FERS_HG[branch_name_hg].Draw("COLZ")
    cMAP_FERS_HG.SetGrid(1,1)
    cMAP_FERS_HG.SaveAs(f"{path_plots}/{branch_name_hg}.png")
    cMAP_FERS_HG.SetLogz()
    cMAP_FERS_HG.SaveAs(f"{path_plots}/{branch_name_hg}_Log.png")    
    del cMAP_FERS_HG

    cMAP_FERS_LG = ROOT.TCanvas(f"cMAP_{branch_name_lg}", f"cMAP_{branch_name_lg}", 700, 700)
    h2_Map_FERS_LG[branch_name_lg].SetStats(0)
    h2_Map_FERS_LG[branch_name_lg].Draw("COLZ")
    cMAP_FERS_LG.SetGrid(1,1)
    cMAP_FERS_LG.SaveAs(f"{path_plots}/{branch_name_lg}.png")
    cMAP_FERS_LG.SetLogz()
    cMAP_FERS_LG.SaveAs(f"{path_plots}/{branch_name_lg}_Log.png")    
    del cMAP_FERS_LG

 


#-------------------------------------------------------
# Write reco output
#-------------------------------------------------------
#save_root_tree(results, beamX, beamY, f"{path_reco}/reco_run{run_id:04d}.root")
print("dqm completed for run: ", run_id)
ROOT.gROOT.GetListOfCanvases().Clear()
ROOT.gROOT.GetListOfCanvases().Delete()
#ROOT.gDirectory.GetList().Delete()

