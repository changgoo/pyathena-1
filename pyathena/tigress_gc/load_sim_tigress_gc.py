import os
import os.path as osp
import pandas as pd
import numpy as np
import xarray as xr

from ..load_sim import LoadSim
from ..util.units import Units
from .hst import Hst
from .slc_prj import SliceProj

class LoadSimTIGRESSGC(LoadSim, Hst, SliceProj):
    """LoadSim class for analyzing TIGRESS-GC simulations.
    """

    def __init__(self, basedir, savdir=None, load_method='pyathena',
                 muH = 1.4271, verbose=False):
        """The constructor for LoadSimTIGRESSGC class

        Parameters
        ----------
        basedir : str
            Name of the directory where all data is stored
        savdir : str
            Name of the directory where pickled data and figures will be saved.
            Default value is basedir.
        load_method : str
            Load vtk using 'pyathena' or 'yt'. Default value is 'pyathena'.
            If None, savdir=basedir. Default value is None.
        verbose : bool or str or int
            Print verbose messages using logger. If True/False, set logger
            level to 'DEBUG'/'WARNING'. If string, it should be one of the string
            representation of python logging package:
            ('NOTSET', 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
            Numerical values from 0 ('NOTSET') to 50 ('CRITICAL') are also
            accepted.
        """

        super(LoadSimTIGRESSGC,self).__init__(basedir, savdir=savdir,
                                               load_method=load_method, verbose=verbose)

        # Set unit and domain
        try:
            muH = self.par['problem']['muH']
        except KeyError:
            pass
        self.muH = muH
        u = Units(muH=muH)
        self.u = u
        self.domain = self._get_domain_from_par(self.par)
        try:
            rprof = xr.open_dataset('{}/radial_profile.nc'.format(self.basedir), engine='netcdf4')
            Rring = self.par['problem']['Rring']
            rprof.coords['eta'] = np.sqrt((rprof.R - Rring)**2 + rprof.z**2)
            eta0 = 200
            for ax in (1,2,3):
                rprof['B'+str(ax)] *= u.muG
                rprof['B_squared'+str(ax)] *= u.muG**2
                rprof['mass_flux'+str(ax)] *= u.Msun/u.pc**2/u.Myr/1e6 # Msun / pc^2 / yr
            rprof['mdot_in'] *= u.Msun/u.Myr/1e6     # Msun / yr
            rprof['mdot_in_mid'] *= u.Msun/u.Myr/1e6
            rprof['mdot_Reynolds'] *= u.Msun/u.Myr/1e6
            rprof['mdot_Maxwell'] *= u.Msun/u.Myr/1e6
            rprof['mdot_dLdt'] *= u.Msun/u.Myr/1e6
            rprof['mdot_coriolis'] *= u.Msun/u.Myr/1e6
            rprof['surface_density'] *= u.Msun / u.pc**2
            rprof['pressure'] *= u.pok
            rprof['turbulent_pressure'] *= u.pok
            rprof['Breg1'] = (rprof.B1.where(rprof.eta<eta0)).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Btrb1'] = np.sqrt(rprof.B_squared1 - rprof.B1**2).where(rprof.eta<eta0).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Breg2'] = (rprof.B2.where(rprof.eta<eta0)).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Btrb2'] = np.sqrt(rprof.B_squared2 - rprof.B2**2).where(rprof.eta<eta0).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Breg3'] = (rprof.B3.where(rprof.eta<eta0)).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Btrb3'] = np.sqrt(rprof.B_squared3 - rprof.B3**2).where(rprof.eta<eta0).weighted(rprof.density).mean(dim=['R','z'])
            rprof['Breg'] = np.sqrt(rprof.Breg1**2 + rprof.Breg2**2 + rprof.Breg3**2)
            rprof['Btrb'] = np.sqrt(rprof.Btrb1**2 + rprof.Btrb2**2 + rprof.Btrb3**2)   
            self.rprof = rprof
        except:
            self.rprof = None

class LoadSimTIGRESSGCAll(object):
    """Class to load multiple simulations"""
    def __init__(self, models=None, muH=None):

        # Default models
        if models is None:
            models = dict()
        if muH is None:
            muH = dict()
            for mdl in models:
                muH[mdl] = 1.4271
        self.models = []
        self.basedirs = dict()
        self.muH = dict()
        self.simdict = dict()

        for mdl, basedir in models.items():
            if not osp.exists(basedir):
                print('[LoadSimTIGRESSGCAll]: Model {0:s} doesn\'t exist: {1:s}'.format(
                    mdl,basedir))
            else:
                self.models.append(mdl)
                self.basedirs[mdl] = basedir
                if mdl in muH:
                    self.muH[mdl] = muH[mdl]
                else:
                    print('[LoadSimTIGRESSGCAll]: muH for {0:s} has to be set'.format(
                          mdl))

    def set_model(self, model, savdir=None, load_method='pyathena', verbose=False):
        self.model = model
        try:
            self.sim = self.simdict[model]
        except KeyError:
            self.sim = LoadSimTIGRESSGC(self.basedirs[model], savdir=savdir,
                                         muH=self.muH[model],
                                         load_method=load_method, verbose=verbose)
            self.simdict[model] = self.sim

        return self.sim
