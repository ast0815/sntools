'''
Implementation of anti-nu_e + 16O -> X + e+

Based on arXiv:1807.02367 (calculations) and arXiv:1809.08398 (fit).

That paper only gives the total cross section sigma(eNu), not the differential
c.s. dSigma/dE (eNu, eE), but since we assume eE = eNu - eG MeV, we can write
the differential c.s. as sigma(eNu) * delta(eNu - eG - eE).
However, numpy doesn't implement a delta distribution and numpy's (numerical)
integration doesn't play nice with sympy's (symbolic) DiracDelta, see:
https://stackoverflow.com/questions/36755487/diracdelta-not-giving-correct-result#36755974
Instead, below we implement an approximation to DiracDelta: a function that's
2*epsilon wide and 1/(2*epsilon) high, so that the integral is 1.
'''

from math import log10
import random

epsilon = 0.001 # for approximating DiracDelta distribution below

# Excitation energy and parameters a, b and c (Table 4 of arXiv:1809.08398)
fit_parameters = {1: [11.23, -40.656, 4.528, 0.887],
                  2: [18.50, -40.026, 4.117, 0.895],
                  3: [21.54, -40.060, 3.743, 0.565],
                  4: [25.38, -39.862, 3.636, 0.846]}


'''
targets_per_molecule:
number of interaction targets per water molecule
(i.e. 2 free protons, 1 oxygen nucleus or 10 electrons)
'''
targets_per_molecule = 1


'''
pid:
ID of the outgoing (detected) particle, using Particle Data Group conventions
(e.g. electron = 11, positron = -11)
'''
pid = -11


'''
possible_flavors:
which neutrino flavors ("e", "eb", "x", "xb") interact in this channel
'''
possible_flavors = ["eb"]


'''
bounds_eNu
List with minimum & maximum energy of incoming neutrino. The minimum energy is
typically given by the threshold energy for the interaction, while the maximum
energy is given by the supernova neutrino flux.
'''
bounds_eNu = [fit_parameters[1][0] + 0.8, 100] # 0.8 MeV = Cherenkov threshold of electron


'''
bounds_eE(eNu, *args):
Kinematical bounds for integration over eE.
Input:
    eNu:  neutrino energy (MeV)
    args: [ignore this]
Output:
    list with minimum & maximum allowed energy of outgoing (detected) particle
'''
def bounds_eE(eNu, *args):
    # smallest eE is at largest (allowed) excitation energy
    for g in range(1,5):
        if eNu > fit_parameters[g][0] + epsilon:
            eMin = eNu - fit_parameters[g][0] - epsilon

    # largest eE is at smallest excitation energy
    eMax = eNu - fit_parameters[1][0] + epsilon

    return [eMin, eMax]


'''
get_eE(eNu, cosT):
Energy of outgoing (detected particle).
Input:
    eNu:  neutrino energy (MeV)
    cosT: cosine of the angle between neutrino and outgoing (detected) particle
Output:
    one floating point number
'''
def get_eE(eNu, cosT=0):
    # find allowed excitation energies
    allowed = []
    for g in range(1,5):
        if eNu > fit_parameters[g][0] + epsilon:
            eE = eNu - fit_parameters[g][0]
            sigma = partial_dSigma_dE(eNu, eE, g)
            allowed.append([eE, sigma])

    # choose from allowed eE with probability proportional to partial cross-section
    sigma_max = max([sigma for _, sigma in allowed])
    while True:
        eE, sigma = random.choice(allowed)
        if sigma > sigma_max * random.random():
            break
    return eE


'''
dSigma_dE(eNu, eE):
Differential cross section.
Input:
    eNu: neutrino energy
    eE:  energy of outgoing (detected) particle
Output:
    one floating point number
'''
def dSigma_dE(eNu, eE): # sum of partial cross-sections, see arXiv:1809.08398
    sigma = 0
    for g in range(1,5):
        sigma += partial_dSigma_dE(eNu, eE, g)

    sigma *= (5.067731E10)**2 # convert cm^2 to MeV^-2, see http://www.wolframalpha.com/input/?i=cm%2F(hbar+*+c)+in+MeV%5E(-1)
    return sigma / (2*epsilon) # Ensure that integration over eE yields sigma


def partial_dSigma_dE(eNu, eE, g): # eq. (4) of arXiv:1809.08398
    eG, a, b, c = fit_parameters[g]

    if abs(eNu - eE - eG) > epsilon:
        return 0

    d = log10(eNu**0.25 - eG**0.25)
    log_sigma = a + b * d + c * d**2
    return 10**log_sigma


'''
dSigma_dCosT(eNu, cosT):
Distribution of the angle at which the outgoing (detected) particle is emitted.
Input:
    eNu:  neutrino energy (MeV)
    cosT: cosine of the angle between neutrino and outgoing (detected) particle
Output:
    one floating point number
'''
def dSigma_dCosT(eNu, cosT):
    # Plots in PRD 36,2283 show this behaves roughly similar to the analogous
    # nu_e reaction, so we use the same approximation. (hep-ph/0307050, eq. B7)
    x = ((eNu-11.23) / 25)**4
    return 1 - cosT * (1+x)/(3+x)


# minimum/maximum neutrino energy that can produce a given positron energy
def _bounds_eNu(eE):
    return (eE + fit_parameters[1][0] - epsilon, eE + fit_parameters[4][0] + epsilon)

# set options for numerical integration with scipy.nquad
def _opts(eNu, *args):
    # values of eE where dSigma_dE(eNu, eE) has a discontinuity, to increase accuracy
    p = []
    for g in range(1,5):
        if eNu > fit_parameters[g][0] + epsilon:
            p.append(eNu - fit_parameters[g][0] - epsilon)
            p.append(eNu - fit_parameters[g][0] + epsilon)

    return {'points': p}
