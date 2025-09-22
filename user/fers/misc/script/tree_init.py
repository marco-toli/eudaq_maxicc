import ROOT
import numpy as np
from array import array
from analysis_functions import get_gr_ch

# def init(tree):
#     run_n = ROOT.std.vector('unsigned int')()
#     event_n = ROOT.std.vector('unsigned int')()
#     event_flag = ROOT.std.vector('unsigned int')()
#     device_n = ROOT.std.vector('unsigned int')()
#     trigger_n = ROOT.std.vector('unsigned int')()
#     timestampbegin = ROOT.std.vector('long')()
#     timestampend = ROOT.std.vector('long')()
#     DRS_Board0_PID = ROOT.std.vector('int')()
#     FERS_Board0_PID = ROOT.std.vector('int')()
#     FERS_Board0_tstamp_us = ROOT.std.vector('double')()
#     FERS_Board0_rel_tstamp_us = ROOT.std.vector('double')()
#     FERS_Board0_trigger_id = ROOT.std.vector('unsigned long long')()
#     FERS_Board0_chmask = ROOT.std.vector('unsigned long long')()
#     FERS_Board0_qdmask = ROOT.std.vector('unsigned long long')()


# def read_scalars(tree):
#     # Scalars
#     run_n = tree.run_n
#     event_n = tree.event_n
#     event_flag = tree.event_flag
#     device_n = tree.device_n
#     trigger_n = tree.trigger_n
#     timestampbegin = tree.timestampbegin
#     timestampend = tree.timestampend
#     DRS_Board0_PID = tree.DRS_Board0_PID
#     FERS_Board0_PID = tree.FERS_Board0_PID
#     FERS_Board0_tstamp_us = tree.FERS_Board0_tstamp_us
#     FERS_Board0_rel_tstamp_us = tree.FERS_Board0_rel_tstamp_us
#     FERS_Board0_trigger_id = tree.FERS_Board0_trigger_id
#     FERS_Board0_chmask = tree.FERS_Board0_chmask
#     FERS_Board0_qdmask = tree.FERS_Board0_qdmask

    

#     return ()


def save_root_tree(results, beamX, beamY, output_file):
    """
    Save a nested dictionary of waveform results to a ROOT TTree.

    Parameters
    ----------
    results : dict
        Dictionary structured as:
        results[branch_name] = {
            "avg_waveform": np.ndarray (num_events, waveform_length),
            "max_amp": np.ndarray (num_events,),
            "integral": np.ndarray (num_events,),
            ...
        }
    output_file : str or Path
        Path to the output ROOT file.
    """

    outfile = ROOT.TFile(str(output_file), "RECREATE")
    tree = ROOT.TTree("recoTree", "Processed waveforms")

    # Keep track of branch objects
    branch_vars = {}

    # Assume all branches have the same number of events
    #first_branch_name = next(iter(results))
    #print(first_branch_name)
    #num_events = next(iter(results[first_branch_name].values())).shape[0]

    #for branch_name, data in results:
    #    print(branch_name)

    # # Loop over all variables of the first branch to create branches
    # for var_name, array_data in results[first_branch_name].items():
    #     if array_data.ndim == 1:  # scalar per event
    #         arr = np.zeros(1, dtype=float)
    #         tree.Branch(var_name, arr, f"{var_name}/D")
    #     else:  # 2D waveform per event
    #         arr = std.vector("float")()
    #         tree.Branch(var_name, arr)
    #     branch_vars[var_name] = arr

    #print("Defining branches...")

    t_beamX = array("f", [0.0])
    t_beamY = array("f", [0.0])
    tree.Branch("beamX", t_beamX, "beamX/F")
    tree.Branch("beamY", t_beamY, "beamY/F")

    for branch_name, data_dict in results.items():
        for var_name, array_data in data_dict.items():
            #print(branch_name, var_name, array_data.shape)
            if var_name == "avg_waveform": continue
            group, ch = get_gr_ch(branch_name)
            new_branch_name = "%s_gr%d_ch%d"%(var_name, group, ch)
            #print("defining:",new_branch_name)

            if array_data.ndim == 1:  # scalar per event
                arr = np.zeros(1, dtype=float)
                tree.Branch(new_branch_name, arr, f"{new_branch_name}/D")

            branch_vars[new_branch_name] = arr

    
    # # Fill tree
    print("Filling branches...")
    
    for i in range(len(beamX)):
        t_beamX[0] = beamX[i]
        t_beamY[0] = beamY[i]
    #     # Use the first branch's data for filling (assuming same structure for all branches)
        for branch_name, data_dict in results.items():
            for var_name, array_data in data_dict.items():
                if var_name == "avg_waveform": continue
                group, ch = get_gr_ch(branch_name)
                new_branch_name = "%s_gr%d_ch%d"%(var_name, group, ch)                
                #print("filling:", new_branch_name)
                arr = branch_vars[new_branch_name]                
                if array_data.ndim == 1:
                  arr[0] = array_data[i]
    
        tree.Fill()

    tree.Write()

    outfile.Close()
    print(f"Saved ROOT file: {output_file}")


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