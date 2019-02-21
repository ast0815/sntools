#!/usr/bin/python

from datetime import datetime
from importlib import import_module
from math import pi, sin, cos, acos
import numpy as np
import random
from scipy import integrate, interpolate


def setup(_channel, _format):
    global channel, format, cached_flux
    channel = import_module("interaction_channels." + _channel)
    format = import_module("formats." + _format)

    # dFlux_dE(eNu, time) is called hundreds of times for each generated event,
    # often with repetitive arguments (when integrating ddEventRate over eE).
    # To save time, we cache results in a dictionary.
    cached_flux = {}

    return channel, format


def gen_evts(_channel, input, _format, inflv, scale, starttime, endtime, verbose):
    """Generate events.

    * Get event rate by interpolating from time steps in the input data.
    * For each 1ms bin, get number of events from a Poisson distribution.
    * Generate these events from time-dependent energy & direction distribution.

    Arguments:
    _channel -- abbreviation of interaction channel, e.g. 'ibd', 'es', ...
    input -- name (or common prefix) of file(s) containing neutrino fluxes
    _format -- which parser (in folder `formats/`) to use for input file(s)
    inflv -- original neutrino flavor (at time of production in the SN)
    scale -- constant factor, accounts for oscillation probability, distance of SN, size of detector
    starttime -- start time set by user via command line option (or None)
    endtime -- end time set by user via command line option (or None)
    """
    setup(_channel, _format) # import appropriate modules
    scale *= channel.targets_per_molecule
    thr_e = 3.511 # detection threshold in HK: 3 MeV kinetic energy + rest mass

    (starttime, endtime, raw_times) = format.parse_input(input, inflv, starttime, endtime)

    # integrate over eE and then eNu to obtain the event rate at time t
    raw_nevts = [scale * integrate.nquad(ddEventRate, [channel.bounds_eE, channel.bounds_eNu], args=[t])[0]
                 for t in raw_times]
    event_rate = interpolate.pchip(raw_times, raw_nevts)

    bin_width = 1 # in ms
    n_bins = int((endtime - starttime)/bin_width) # number of full-width bins; int() implies floor()
    if verbose: print "Now generating events in", bin_width, "ms bins from", starttime, "to", endtime, "ms"

    # scipy is optimized for operating on large arrays, making it orders of
    # magnitude faster to pre-compute all values of the interpolated functions.
    binned_t = [starttime + (i+0.5)*bin_width for i in range(n_bins)]
    binned_nevt_th = event_rate(binned_t)
    # check for unphysical values of interpolated function event_rate(t)
    for _i, _n in enumerate(binned_nevt_th):
        if _n < 0:
            binned_nevt_th[_i] = 0
    binned_nevt = np.random.poisson(binned_nevt_th) # Get random number of events in each bin from Poisson distribution
    format.prepare_evt_gen(binned_t) # give flux script a chance to pre-compute values

    # FOR GENERATING FILES CONTAINING THE NUMBER OF EXPECTED EVENTS PER ENERGY/TIME BIN
    with open("nevt_" + _format + "_" + _channel + "-" + inflv + ".txt", 'w') as outfile:
        outfile.write("# Generated on %s with the options:\n" % datetime.now())
        outfile.write("# " + _cmd + "\n")

        ebinned_nevts = []
        ebin_width = 2
        outfile.write("# Format: time bin, expected number of events (total), <10MeV, ... " + str(ebin_width) + "MeV bins ..., >50MeV\n")
        for _e_upper in range(10, 51 + ebin_width, ebin_width):
            _e_lower = _e_upper - ebin_width
            # energy bins: <10 MeV, 1 MeV bins up to 50 MeV, then >50 MeV
            e_lower = lambda _eNu, *args: max(_e_lower, channel.bounds_eE(_eNu)[0])
            e_upper = lambda _eNu, *args: min(_e_upper, channel.bounds_eE(_eNu)[1])
            if _e_upper == 10:
                _e_lower = thr_e
                e_lower = lambda _eNu, *args: max(thr_e, channel.bounds_eE(_eNu)[0])
            elif _e_upper == 50 + ebin_width:
                _e_upper = channel.bounds_eNu[1]
                e_upper = lambda _eNu, *args: channel.bounds_eE(_eNu)[1]

            def bounds_eE(_eNu, *args):
                e_min = e_lower(_eNu, *args)
                e_max = e_upper(_eNu, *args)
                if e_min > e_max: # kinematically forbidden
                    return [0, 0]
                else:
                    return [e_min, e_max]

            bounds_eNu = [max(channel.bounds_eNu[0], channel._bounds_eNu(_e_lower)[0]),
                          min(channel.bounds_eNu[1], channel._bounds_eNu(_e_upper)[1])]

            nevts = [scale * integrate.nquad(ddEventRate, [bounds_eE, bounds_eNu], args=[t])[0]
                     for t in raw_times]
            nevts = interpolate.pchip(raw_times, nevts)
            ebinned_nevts.append(nevts(binned_t))

        for i, (t, n) in enumerate(zip(binned_t, binned_nevt_th)):
            outfile.write("%s, %s" %(t, n))
            _sum_over_bins = 0
            for energy_bin in ebinned_nevts:
                outfile.write(", %s" %(energy_bin[i]))
                _sum_over_bins += energy_bin[i]
#             if i < 250 or i%1000 == 0:
#                 # check that numerical difference of different integrations is small
#                 print i, (n-_sum_over_bins)/n, n, _sum_over_bins
            outfile.write("\n")


    if verbose: # compute events above threshold energy `thr_e`
        thr_bounds_eE = lambda _eNu, *args: [max(thr_e, channel.bounds_eE(_eNu)[0]), max(thr_e, channel.bounds_eE(_eNu)[1])]
        thr_raw_nevts = [scale * integrate.nquad(ddEventRate, [thr_bounds_eE, channel.bounds_eNu], args=[t])[0]
                         for t in raw_times]
        thr_event_rate = interpolate.pchip(raw_times, thr_raw_nevts)
        thr_binned_nevt_th = thr_event_rate(binned_t)
        thr_nevt = sum(binned_nevt)

    # FOR GENERATING RANDOM EVENTS ASSUMING A FIXED SN DISTANCE
    events = []
    for i in range(n_bins):
        t0 = starttime + i * bin_width

        if verbose and i%(10**(4-verbose)) == 0:
            print "%s-%s ms: %d events (%.5f expected)" % (t0, t0+bin_width, binned_nevt[i], binned_nevt_th[i])

        # generate events in this time bin
        for _ in range(binned_nevt[i]):
            t = t0 + random.random() * bin_width
            eNu = get_eNu(binned_t[i])
            (dirx, diry, dirz) = get_direction(eNu)
            eE = channel.get_eE(eNu, dirz)
            if verbose and eE < thr_e: thr_nevt -= 1
            events.append((t, channel.pid, eE, dirx, diry, dirz))

    print "Generated %s particles (expected: %.2f particles)" % (sum(binned_nevt), sum(binned_nevt_th))
    if verbose:
        print "-> above threshold of %s MeV: %s particles (expected: %.2f)" % (thr_e, thr_nevt, sum(thr_binned_nevt_th))
        print "**************************************"

    return events


"""Helper functions."""
# double differential event rate
def ddEventRate(eE, eNu, time):
    return channel.dSigma_dE(eNu, eE) * dFlux_dE(eNu, time)

def dFlux_dE(eNu, time):
    if not cached_flux.has_key((eNu, time)):
        fiducial_distance = 1.563738e+33 # 10 kpc/(hbar * c) in MeV**(-1)
        emission = format.nu_emission(eNu, time)
        cached_flux[(eNu, time)] = emission / (4 * pi * fiducial_distance**2)
    return cached_flux[(eNu, time)]

# get a value from an arbitrary distribution dist
def rejection_sample(dist, min_val, max_val, n_bins=100):
    p_max = 0
    j_max = 0
    bin_width = float(max_val - min_val) / n_bins

    # Iterative approach to speed up finding the maximum of `dist`.
    # Assumes that `dist` does not oscillate very quickly.
    # First, use coarse binning to find the approximate maximum:
    for j in range(0, n_bins, 10):
        val = min_val + bin_width * (j + 0.5)
        p = dist(val)
        if p > p_max:
            p_max = p
            j_max = j
    # Then, use finer binning around the approximate maximum.
    for j in range(max(j_max-9, 0), min(j_max+10, n_bins)):
        val = min_val + bin_width * (j + 0.5)
        p = dist(val)
        if p > p_max:
            p_max = p

    while True:
        val = min_val + (max_val - min_val) * random.random()
        if p_max * random.random() < dist(val):
            break

    return val

# use rejection sampling to get the energy of an interacting neutrino
def get_eNu(time):
    dist = lambda _eNu: integrate.quad(ddEventRate, *channel.bounds_eE(_eNu), args=(_eNu, time))[0]
    eNu = rejection_sample(dist, *channel.bounds_eNu, n_bins=200)
    return eNu

# get direction of outgoing particle (incoming neutrino moves in z direction)
def get_direction(eNu):
    dist = lambda _cosT: channel.dSigma_dCosT(eNu, _cosT)
    cosT = rejection_sample(dist, -1, 1, 200)
    sinT = sin(acos(cosT))
    phi = 2 * pi * random.random() # randomly distributed in [0, 2 pi)
    return (sinT*cos(phi), sinT*sin(phi), cosT)
