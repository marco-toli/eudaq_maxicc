# analysis_functions.py
import ROOT
import numpy as np
from array import array

import re

def get_gr_ch(branch_name):
    """
    Extract group and channel numbers from a branch name string.
    
    Example: "DRS_Board0_Group1_Channel7" -> (1, 7)
    """
    match = re.search(r"Group(\d+)_Channel(\d+)", branch_name)
    if match:
        group = int(match.group(1))
        ch = int(match.group(2))
        return group, ch
    else:
        raise ValueError(f"Invalid branch name format: {branch_name}")
    


def get_pedestal(waveforms, minPed=10, maxPed=40):

    """
    Compute average of samples between [minPed, maxPed) for each event.
    
    Parameters
    ----------
    waveforms : np.ndarray
        2D array of shape (num_events, num_samples).
    start : int
        Start index of slice (inclusive).
    stop : int
        Stop index of slice (exclusive).
    
    Returns
    -------
    np.ndarray
        1D array of length num_events with the average values.
    """
    return waveforms[:, minPed:maxPed].mean(axis=1)




def get_times(waveforms, thresholds, dt=1.0):
    
    """
    Find threshold crossing times with linear fit over 4 points,
    each waveform can have its own threshold.

    Parameters
    ----------
    waveforms : np.ndarray
        Shape (num_events, num_samples).
    thresholds : np.ndarray
        Shape (num_events,), threshold value for each waveform.
    dt : float
        Sampling interval (time between samples).

    Returns
    -------
    np.ndarray
        1D array of crossing times (length = num_events).
        -1 if no crossing found for that waveform.
    """
    num_events, num_samples = waveforms.shape
    times = np.full(num_events, -1.0)

    for i, wf in enumerate(waveforms):
        thr = thresholds[i]
        above = np.where(wf > thr)[0]
        if above.size > 0:
            i0 = above[0]
            # take two samples before and after crossing (clamped inside waveform)
            i_start = max(i0 - 2, 0)
            i_stop = min(i0 + 2, num_samples)
            xs = np.arange(i_start, i_stop) * dt
            ys = wf[i_start:i_stop]

            # linear fit
            coeffs = np.polyfit(xs, ys, 1)
            slope, intercept = coeffs[0], coeffs[1]

            if slope != 0:
                t_cross = (thr - intercept) / slope
                times[i] = t_cross

    return times