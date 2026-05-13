# analysis_functions.py
import ROOT
import numpy as np
from array import array
from scipy.interpolate import interp1d
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

import numpy as np
from scipy.interpolate import interp1d

def get_aligned_waveforms(waveforms, times, maxamp, dt=1.0, amp_threshold=100):
    """
    Align waveforms in time using extracted hit times.

    Parameters
    ----------
    waveforms : np.ndarray
        Array of shape (nEvents, nSamples)
    times : np.ndarray
        Array of shape (nEvents,) with signal time (e.g. from CFD or threshold crossing)
    maxamp : np.ndarray
        Array of shape (nEvents,) with maximum amplitude per event
    dt : float
        Sampling interval (ns or arbitrary units)
    amp_threshold : float
        Minimum amplitude to consider an event for reference time

    Returns
    -------
    aligned_waveforms : np.ndarray
        Time-aligned waveforms, same shape as input.
    """

    nEvents, nSamples = waveforms.shape
    t = np.arange(nSamples) * dt

    # --- compute reference only from "good" events ---
    good_mask = maxamp > amp_threshold
    if np.any(good_mask):
        t_ref = np.median(times[good_mask])
    else:
        print("⚠️ No good events found above threshold — using all events for t_ref.")
        t_ref = np.median(times)

    aligned = np.zeros_like(waveforms)

    for i in range(nEvents):
        f = interp1d(t, waveforms[i], kind="linear", fill_value=0, bounds_error=False)
        shifted_t = t + (times[i] - t_ref)
        aligned[i] = f(shifted_t)

    return aligned



def template_fit(waveform, dt=1.0, window=10):
    """
    Fit waveform with a Gaussian around the maximum using ROOT TF1.
    waveform : 1D numpy array of amplitudes
    dt       : time step per sample
    window   : number of samples around peak to fit
    Returns: amp_fit, t0_fit
    """
    waveform = np.ravel(waveform)  # ensures 1D array
    n = len(waveform)
    times = np.arange(n) * dt

    peak_idx = int(np.argmax(waveform))  # make sure it's a scalar integer

    # Define fit range around peak
    fit_min = max(0, (peak_idx - window) * dt)
    fit_max = min(n*dt, (peak_idx + window) * dt)

    # ROOT TF1 Gaussian
    f1 = ROOT.TF1("f1", "[0]*exp(-0.5*((x-[1])/[2])**2)", fit_min, fit_max)
    f1.SetParameters(waveform[peak_idx], times[peak_idx], dt*5)  # initial amp, t0, width

    # TGraph for fitting
    tg = ROOT.TGraph(len(waveform), array("d", times), array("d", waveform))
    tg.Fit(f1, "Q")  # quiet

    amp_fit = f1.GetParameter(0)
    t0_fit  = f1.GetParameter(1)

    return amp_fit, t0_fit
