import ROOT
import numpy as np
from array import array
import pandas as pd

def init_info_tree():
    tree = ROOT.TTree("infoTree", "Run-level information")
    tree.t_beam = ROOT.std.string()
    tree.t_angle = array('f', [0])
    tree.t_ene   = array('f', [0])
    tree.t_vb1   = array('f', [0])
    tree.t_vb2   = array('f', [0])
    tree.t_vb3   = array('f', [0])
    tree.t_hgain = array('f', [0])
    tree.t_lgain = array('f', [0])
    tree.t_stime = array('f', [0])
    tree.t_holdt = array('f', [0])    
    tree.t_conf  = array('i', [0])
    tree.Branch("t_angle", tree.t_angle, "t_angle/F")
    tree.Branch("t_beam", tree.t_beam)
    tree.Branch("t_ene", tree.t_ene, "t_ene/F")
    tree.Branch("t_vb1", tree.t_vb1, "t_vb1/F")
    tree.Branch("t_vb2", tree.t_vb2, "t_vb2/F")
    tree.Branch("t_vb3", tree.t_vb3, "t_vb3/F")
    tree.Branch("t_hgain", tree.t_hgain, "t_hgain/F")
    tree.Branch("t_lgain", tree.t_lgain, "t_lgain/F")
    tree.Branch("t_stime", tree.t_stime, "t_stime/F")
    tree.Branch("t_holdt", tree.t_holdt, "t_holdt/F")    
    tree.Branch("t_conf", tree.t_conf, "t_conf/I")
    return tree#, {"t_angle": t_angle, "t_ene": t_ene, "t_conf": t_conf, "t_vb1": t_vb1, "t_vb2": t_vb2, "t_vb3": t_vb3}


def init_evt_tree():
    tree = ROOT.TTree("evtTree", "Event-level information")
    tree.evt_id = array('i', [0])
    tree.t_beamX = array('f', [0])
    tree.t_beamY = array('f', [0])
    tree.Branch("evt_id", tree.evt_id, "evt_id/I")
    tree.Branch("t_beamX", tree.t_beamX, "t_beamX/F")
    tree.Branch("t_beamY", tree.t_beamY, "t_beamY/F")
    return tree#, {"evt_id": evt_id, "t_beamX": t_beamX, "t_beamY": t_beamY}


def init_drs_tree():
    tree = ROOT.TTree("drsTree", "DRS data")
    tree.evt_ref = array('i', [0])
    # Fixed-size arrays
    tree.t_ped   = array('f', 8*[0])
    tree.t_amp   = array('f', 8*[0])
    tree.t_int   = array('f', 8*[0])
    tree.t_time1 = array('f', 8*[0])
    tree.t_time2 = array('f', 8*[0])

    tree.Branch("evt_ref", tree.evt_ref, "evt_ref/I")
    tree.Branch("t_ped", tree.t_ped, "t_ped[8]/F")
    tree.Branch("t_amp", tree.t_amp, "t_amp[8]/F")
    tree.Branch("t_int", tree.t_int, "t_int[8]/F")
    tree.Branch("t_time1", tree.t_time1, "t_time1[8]/F")
    tree.Branch("t_time2", tree.t_time2, "t_time2[8]/F")
    return tree#, {"evt_ref": evt_ref, "t_ped": t_ped, "t_amp": t_amp, "t_int": t_int, "t_time1": t_time1, "t_time2": t_time2 }



def init_fers_tree(nFers):
    tree = ROOT.TTree("fersTree", "FERS data")
    tree.evt_ref = array('i', [0])
    tree.t_hg    = array('f', 64*nFers*[0])
    tree.t_lg    = array('f', 64*nFers*[0])

    tree.Branch("evt_ref", tree.evt_ref, "evt_ref/I")
    tree.Branch("t_hg", tree.t_hg, f"t_hg[{64*nFers}]/F")
    tree.Branch("t_lg", tree.t_lg, f"t_lg[{64*nFers}]/F")

    return tree

def fill_info_tree_from_logbook(run_number, logbook, readFromLogbook=True):
    """
    Reads metadata for a single run from an Excel logbook and fills a ROOT TTree.
    Returns a ROOT TTree object ready to be written.
    """
    tree_info = init_info_tree()

    # Default values
    angle = ene = vb1 = vb2 = vb3 = -999.0    
    beam = "unknown"
    hgain = lgain = stime = holdt = -999.0
    conf = -999

    if not readFromLogbook:
        print("readFromLogbook = False → filling default values only")
    else:
        try:
            df = pd.read_excel(logbook)
            print(f"Reading logbook: {logbook}")

            selected_row = df.loc[df["Run number"] == run_number]
            if not selected_row.empty:
                print(f"✅ Found metadata for run {run_number}")
                angle = float(selected_row["Angle"].values[0])
                ene   = float(selected_row["Energy"].values[0])
                beam  = str(selected_row["Beam"].values[0])
                vb1   = float(selected_row["Vbias_S_rear"].values[0])
                vb2   = float(selected_row["Vbias_C_rear"].values[0])
                vb3   = float(selected_row["Vbias_S_front"].values[0])
                hgain = float(selected_row["HG"].values[0])
                lgain = float(selected_row["LG"].values[0])
                stime = float(selected_row["Shaping_time"].values[0])
                holdt = float(selected_row["HoldOff_delay"].values[0])                
                conf  = int(selected_row["Conf"].values[0]) if "Conf" in selected_row else -999
            else:
                print(f"⚠️ Run {run_number} not found in logbook. Using default values.")

        except Exception as e:
            print(f"❌ Error reading logbook or parsing run {run_number}: {e}")
            print("Filling default values.")

    # --- Fill tree directly ---
    tree_info.t_angle[0] = angle
    tree_info.t_ene[0]   = ene
    tree_info.t_conf[0]  = conf
    tree_info.t_vb1[0]   = vb1
    tree_info.t_vb2[0]   = vb2
    tree_info.t_vb3[0]   = vb3
    tree_info.t_hgain[0] = hgain
    tree_info.t_lgain[0] = lgain
    tree_info.t_stime[0] = stime
    tree_info.t_holdt[0] = holdt

    tree_info.t_beam.clear()
    tree_info.t_beam.replace(0, len(tree_info.t_beam), beam)  # beam è una stringa
    tree_info.Fill()
    return tree_info



def find_position_in_map(config_map, value):
    """
    Find the (row, col) position of a given value in a 2D list (map).

    Parameters:
        config_map (list of list of int): The map matrix.
        value (int): The value to search for.

    Returns:
        tuple: (row, col) if found, else None
    """
    for row_idx, row in enumerate(config_map):
        for col_idx, cell in enumerate(row):
            if cell == value:
                return (row_idx, col_idx)
    return None
