from math import pi, sqrt, log


targets_per_molecule = 2 # number of free protons per water molecule
pid = -11
possible_flavors = ["eb"]


'''
Particle physics section.
* cross section for neutrino-electron scattering
* directionality of scattered electron

Based on Strumia/Vissani (2003), arXiv:astro-ph/0302055.
'''
mN = 939.56563 # neutron mass (MeV)
mP = 938.27231 # proton mass (MeV)
mE = 0.5109907 # electron mass (MeV)
mPi = 139.56995 # pion mass (MeV)
delta = mN - mP
mAvg = (mP+mN) / 2
alpha = 1 / 137.035989 # fine structure constant
gF = 1.16639e-11 # Fermi coupling constant
sigma0 = 2 * mP * gF**2 * 0.9746**2 / (8 * pi * mP**2) # from eqs. (3), (11)

def dSigma_dE(eNu, eE): # eqs. (11), (3)
    if eNu < eThr or eE < bounds_eE(eNu)[0] or eE > bounds_eE(eNu)[1]:
        return 0
    # above eq. (11)
    s_minus_u = 2*mP*(eNu+eE) - mE**2
    t = mN**2 - mP**2 - 2*mP*(eNu-eE)

    # eq. (7)
    x = 0 + t / (4*mAvg**2)
    y = 1 - t / 710**2
    z = 1 - t / 1030**2
    f1 = (1 - 4.706 * x) / ((1-x) * y**2)
    f2 = 3.706 / ((1-x) * y**2)
    g1 = -1.27 / z**2
    g2 = 2 * g1 * mAvg**2 / (mPi**2 - t)

    A = 1./16 * (
            (t - mE**2) * (
                4 * f1**2 * (4*mAvg**2 + t + mE**2)
                + 4 * g1**2 * (-4*mAvg**2 + t + mE**2)
                + f2**2 * (t**2 / mAvg**2 + 4*t + 4*mE**2)
                + 4*mE**2 * t * g2**2 / mAvg**2
                + 8*f1*f2 * (2*t + mE**2)
                + 16*mE**2 * g1*g2)
            - delta**2 * (
                (4*f1**2 + t * f2**2 / mAvg**2) * (4*mAvg**2 + t - mE**2)
                + 4*g1**2 * (4*mAvg**2 - t + mE**2)
                + 4*mE**2 * g2**2 * (t - mE**2) / mAvg**2
                + 8*f1*f2 * (2*t - mE**2)
                + 16*mE**2 * g1*g2)
            - 32*mE**2 * mAvg * delta * g1*(f1 + f2))

    B = 1./16 * (16 * t * g1 * (f1 + f2)
                  + 4*mE**2 * delta * (f2**2 + f1*f2 + 2*g1*g2)/mAvg)

    C = 1./16 * (4*(f1**2 + g1**2) - t * f2**2 / mAvg**2)

    abs_M_squared = A - B * s_minus_u + C * s_minus_u**2 # eq. (5)
    rad_correction = alpha/pi * (6.00352 + 3./2 * log(mP/(2*eE)) + 1.2 * (mE/eE)**1.5) # eq. (14)

    result = sigma0 / eNu**2 * abs_M_squared * (1 + rad_correction)

    if result < 0:
        raise ValueError("Calculated negative cross section for E_nu=%f, E_e=%f. Aborting..." % (eNu, eE))

    return result


# probability distribution for the angle at which the positron is emitted
def dSigma_dCosT(eNu, cosT): # eq. (20)
    epsilon = eNu / mP
    eE = get_eE(eNu, cosT)
    pE = sqrt(eE**2 - mE**2)
    dE_dCosT = pE * epsilon / (1 + epsilon * (1 - cosT * eE / pE))
    return dE_dCosT * dSigma_dE(eNu, eE)


def get_eE(eNu, cosT): # eq. (21)
    epsilon = eNu / mP
    kappa = (1 + epsilon)**2 - (epsilon * cosT)**2
    return ((eNu - delta_cm) * (1 + epsilon) + epsilon * cosT * sqrt((eNu - delta_cm)**2 - mE**2 * kappa)) / kappa


# Bounds for integration over eE
delta_cm = (mN**2 - mP**2 - mE**2) / (2*mP)
def bounds_eE(eNu, *args): # ignore additional arguments handed over by scipy.integrate.nquad()
    s = 2*mP*eNu + mP**2
    pE_cm = sqrt((s-(mN-mE)**2) * (s-(mN+mE)**2)) / (2*sqrt(s))
    eE_cm = (s-mN**2+mE**2) / (2*sqrt(s))

    eE_min = eNu - delta_cm - eNu/sqrt(s) * (eE_cm + pE_cm)
    eE_max = eNu - delta_cm - eNu/sqrt(s) * (eE_cm - pE_cm)
    return [eE_min, eE_max]

# Bounds for integration over eNu
eThr = ((mN+mE)**2 - mP**2) / (2*mP) # threshold energy for IBD: ca. 1.8 MeV
bounds_eNu = [eThr, 100]


# minimum/maximum neutrino energy that can produce a given positron energy, eq. (19)
# Note: This is only an approximation to simplify numerical integration; the precise range has to be enforced separately.
def _bounds_eNu(eE):
    eNu_min = eE + delta_cm
    eNu_max = eNu_min / (1 - 2 * eNu_min/mP)
    return (eNu_min, eNu_max)
