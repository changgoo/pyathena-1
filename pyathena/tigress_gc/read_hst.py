# read_hst.py

import os
import numpy as np
import pandas as pd
from astropy import units as au
from scipy import integrate

from ..io.read_hst import read_hst
from ..load_sim import LoadSim
from .pot import vcirc


class ReadHst:

    @LoadSim.Decorators.check_pickle_hst
    def read_hst(self, savdir=None, force_override=False):
        """Function to read hst and convert quantities to convenient units
        """
    
        u = self.u
        domain = self.domain

        # volume of resolution element (code unit)
        dvol = domain['dx'].prod()
        # total volume of domain (code unit)
        vol = domain['Lx'].prod()
        # domain length (code unit)
        Lx = domain['Lx'][0]
        Ly = domain['Lx'][1]
        Lz = domain['Lx'][2]
        # area of domain
        area = [Lx*Ly, Lz*Lx, Ly*Lz]

        # Orbital time at the bulge scale length rb
        rb = 120
        time_orb = ((2*np.pi*rb*au.pc)/(vcirc(rb)*au.km/au.s)).to('Myr').value

        hst = read_hst(self.files['hst'], force_override=force_override)

        h = pd.DataFrame()

        # Time in code unit
        h['time_code'] = hst['time']
        # Time in Myr
        h['time'] = hst['time']*u.Myr
        # Time in orbital time
        h['time_orb'] = h['time']/time_orb

        # Total gas mass in Msun
        h['mass'] = hst['mass']*vol*u.Msun
        h['Mh2'] = hst['Mh2']*vol*u.Msun
        h['Mh1'] = hst['Mh1']*vol*u.Msun
        h['Mw'] = hst['Mw']*vol*u.Msun
        h['Mu'] = hst['Mu']*vol*u.Msun
        h['Mc'] = hst['Mc']*vol*u.Msun
        h['msp'] = hst['msp']*vol*u.Msun
        h['msp_left'] = hst['msp_left']*vol*u.Msun

        # Total outflow mass
        for i, direction in enumerate(['F3','F2','F1']):
            flux = (hst[direction+'_upper'] - hst[direction+'_lower'])\
                    *area[i]*u.mass_flux*u.length**2
            h['mass_out'] = integrate.cumtrapz(flux, h['time'], initial=0.0)

        # Calculate (cumulative) SN ejecta mass
        # JKIM: only from clustered type II(?)
        try:
            sn = read_hst(self.files['sn'], force_override=force_override)
            t_ = np.array(hst['time'])
            Nsn, snbin = np.histogram(sn.time, bins=np.concatenate(([t_[0]], t_)))
            h['mass_snej'] = Nsn.cumsum()*self.par['feedback']['MejII'] # Mass of SN ejecta [Msun]
        except:
            pass

        # star formation rates [Msun/yr]
        h['sfr1'] = hst['sfr1']*(Lx*Ly/1e6)
        h['sfr5'] = hst['sfr5']*(Lx*Ly/1e6)
        h['sfr10'] = hst['sfr10']*(Lx*Ly/1e6)
        h['sfr40'] = hst['sfr40']*(Lx*Ly/1e6)
        h['sfr100'] = hst['sfr100']*(Lx*Ly/1e6)

        h.index = h['time_code']
        
        self.hst = h

        return h

    @LoadSim.Decorators.check_pickle_hst
    def read_sn(self, savdir=None, force_override=False):
        """Function to read sn dump and convert quantities to convenient units
        """
        # TODO
        pass
