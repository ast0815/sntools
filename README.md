# sntools
Scripts for simulating a supernova neutrino burst in Hyper-Kamiokande.

### Required Input
Text file(s) containing information about neutrino fluxes.
Multiple input formats are supported; see the source files in the `formats/` directory for details.

#### Garching format:
Three separate text files (one each for nu_e, anti-nu_e and nu_x - where nu_x stands for nu_mu or nu_tau or their respective antineutrinos), each containing time, mean energy, mean squared energy and luminosity. See `sample-in.txt` for details.

#### Totani format:
Used by Totani et al. 1998, which is the baseline model in the [Hyper-Kamiokande Design Report](https://arxiv.org/abs/1805.04163).

#### Nakazato format:
Used by recent simulations by Nakazato et al., [available for download here](http://asphwww.ph.noda.tus.ac.jp/snn/index.html).

### Interaction Channels
Currently the four main interaction channels in water Cherenkov detectors are supported:
inverse beta decay, elastic scattering on electrons and charged current interactions of nu_e and anti-nu_e on oxygen-16 nuclei.
For details, see the files in `interaction_channels/`.

### Output:
A .kin file in the NUANCE format used by the /mygen/vecfile options in WCSim. See [the format documentation](http://neutrino.phy.duke.edu/nuance-format/) for details.

### Typical Usage:
```
python genevts.py infile --format=garching -o outfile.kin --hierarchy=normal --channel=ibd
```
This assumes the three input files (in Garching format) are named `infile_e.txt`, `infile_eb.txt` and `infile_x.txt`.

See
```
python genevts.py -h
```
for a full description of these and other options.
