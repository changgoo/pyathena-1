import numpy as np
import xarray as xr
from .tes import TES
from ..util.transform import to_spherical, groupby_bins


def radial_profile(ds, origin, rmax):
    """Calculates radial density velocity profiles at the selected position

    Args:
        ds: xarray.Dataset instance containing conserved variables.
        origin: tuple-like (x0, y0, z0) representing the origin of the spherical coords.
        rmax: maximum radius to bin.

    Returns:
        rprof: xarray.Dataset instance containing angular-averaged radial profiles of
               density, velocities, and velocity dispersions.
    """
    # Convert density and velocities to spherical coord.
    vel = {}
    for dim, axis in zip(['x','y','z'], [1,2,3]):
        vel_ = ds['mom{}'.format(axis)]/ds.dens
        vel[dim] = vel_ - vel_.sel(x=origin[0], y=origin[1], z=origin[2])
    ds_sph = {}
    ds_sph['vel1'], ds_sph['vel2'], ds_sph['vel3'] = to_spherical(vel.values(), origin)
    ds_sph['rho'] = ds.dens.assign_coords(dict(r=ds_sph['vel1'].r))

    # Radial binning
    edges = np.insert(np.arange(ds.dx/2, rmax, ds.dx), 0, 0)
    rprf = {}
    for key, value in ds_sph.items():
        rprf[key] = groupby_bins(value, 'r', edges)
    for key in ('vel1', 'vel2', 'vel3'):
        rprf[key+'_std'] = np.sqrt(groupby_bins(ds_sph[key]**2, 'r', edges))
    rprf = xr.Dataset(rprf)
    return rprf

class Tools:

    def get_tJeans(self, lmb, rho=None):
        """e-folding time of the fastest growing mode of the Jeans instability
        lmb = wavelength of the mode
        """
        if rho is None:
            rho = self.rho0
        tJeans = 1/np.sqrt(4*np.pi*self.G*rho)*lmb/np.sqrt(lmb**2 - 1)
        return tJeans

    def get_tcr(self, lscale, dv):
        """crossing time for a length scale lscale and velocity dv"""
        tcr = lscale/dv
        return tcr

    def get_Lbox(self, Mach):
        """Return box size at which t_cr = t_Jeans,
        where t_cr = (Lbox/2)/Mach
        """
        dv = Mach*self.cs
        Lbox = np.sqrt(1 + dv**2/(np.pi*self.G*self.rho0))
        return Lbox

    def get_sonic(self, Mach, p=0.5):
        """returns sonic scale for periodic box with Mach number Mach
        assume linewidth-size relation v ~ R^p
        """
        if Mach==0:
            return np.inf
        Lbox = self.get_Lbox(Mach)
        lambda_s = Lbox*Mach**(-1/p)
        return lambda_s

    def get_RLP(self, M):
        """Returns the LP radius enclosing  mass M"""
        RLP = self.G*M/8.86/self.cs**2
        return RLP

    def get_rhoLP(self, r):
        """Larson-Penston asymptotic solution in dimensionless units"""
        rhoLP = 8.86*self.cs**2/(4*np.pi*self.G*r**2)
        return rhoLP

    def get_critical_TES(self, rhoe, lmb_sonic, p=0.5):
        """
        Calculate critical turbulent equilibrium sphere

        Description
        -----------
        Critical mass of turbulent equilibrium sphere is given by
            M_crit = M_{J,e}m_crit(xi_s)
        where m_crit is the dimensionless critical mass and M_{J,e}
        is the Jeans mass at the edge density rho_e.
        This function assumes unit system:
            [L] = L_{J,0}, [M] = M_{J,0}

        Parameters
        ----------
        rhoe : edge density
        lmb_sonic : sonic radius
        p (optional) : power law index for the linewidth-size relation

        Returns
        -------
        rhoc : central density
        R : radius of the critical TES
        M : mass of the critical TES
        """
        LJ_e = 1.0*(rhoe/self.rho0)**-0.5
        MJ_e = 1.0*(rhoe/self.rho0)**-0.5
        xi_s = lmb_sonic / LJ_e
        tes = TES(p, xi_s)
        rat, xi0, m = tes.get_crit()
        rhoc = rat*rhoe
        R = LJ_e*xi0
        M = MJ_e*m
        return rhoc, R, M
