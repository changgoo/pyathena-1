import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import astropy.units as au
import astropy.constants as ac

from ..load_sim import LoadSimAll

def load_sixray_test_all(models=None, cool=False):

    # CR var: CR rate scales with radiation
    # Unshld: no shielding
    # Jeans: shielding length = local Jeans length

    # Load data and compute abundances and cooling rates
    if models is None:
        models = dict(
            Unshld_CRvar_Z1='/tigress/jk11/SIXRAY-TEST-UNSHIELDED/Unshld.CRvar.Z1.0/',
            Unshld_CRvar_Z01='/tigress/jk11/SIXRAY-TEST-UNSHIELDED/Unshld.CRvar.Z0.1/',
            Unshld_CRvar_Z001='/tigress/jk11/SIXRAY-TEST-UNSHIELDED/Unshld.CRvar.Z0.01/',
            Unshld_CRvar_Z3='/tigress/jk11/SIXRAY-TEST-UNSHIELDED/Unshld.CRvar.Z3.0/',
            Unshld_CRvar_Z1_scaled='/tigress/jk11/SIXRAY-TEST-UNSHIELDED/Unshld.CRvar.Z1.0.scaled/',
            # Shld_CRvar_Z1='/perseus/scratch/gpfs/jk11/SIXRAY-TEST-LSHLD5/Lshld.CRvar.Z1.0',
            # Shld_CRvar_Z01='/perseus/scratch/gpfs/jk11/SIXRAY-TEST-LSHLD5/Lshld.CRvar.Z0.1',
            # Shld_CRvar_Z001='/perseus/scratch/gpfs/jk11/SIXRAY-TEST-LSHLD5/Lshld.CRvar.Z0.01',
            # Shld_CRvar_Z3='/perseus/scratch/gpfs/jk11/SIXRAY-TEST-LSHLD5/Lshld.CRvar.Z3.0',
            Shld_CRvar_Z1='/tigress/jk11/SIXRAY-TEST-SHIELDED-noCISHLD/Lshld.CRvar.Z1.0',
            Shld_CRvar_Z01='/tigress/jk11/SIXRAY-TEST-SHIELDED-noCISHLD/Lshld.CRvar.Z0.1',
            Shld_CRvar_Z001='/tigress/jk11/SIXRAY-TEST-SHIELDED-noCISHLD/Lshld.CRvar.Z0.01',
            Shld_CRvar_Z3='/tigress/jk11/SIXRAY-TEST-SHIELDED-noCISHLD/Lshld.CRvar.Z3.0',
        )
            
    sa = LoadSimAll(models)
    da = dict()
    print('[load_sixray_test_all] reading simulation data:', end=' ')
    for i, mdl in enumerate(sa.models):
        print(mdl, end=' ')
        s = sa.set_model(mdl)
        if 'BT94' in mdl:
            dust_model = 'BT94'
        elif 'W03' in mdl:
            dust_model = 'W03'
        else:
            dust_model = 'WD01'
        da[mdl] = get_cool_data(s, s.nums[-1],
                                sel_kwargs=dict(z=0, method='nearest'),
                                cool=cool, dust_model=dust_model)

    return sa, da

def get_cool_data(s, num, sel_kwargs=dict(), cool=True, dust_model='WD01'):

    D0 = 5.7e-11 # Dissociation rate for unshielded ISRF [s^-1]
    dvdr = (s.par['problem']['dvdr']*(1.0*au.km/au.s/au.pc).to('s-1')).value

    ds = s.load_vtk(num)
    if not 'CR_ionization_rate' in ds.field_list:
        dd = ds.get_field(['nH','nH2','nHI','xH2','xHII','xe',
                           'xHI','xCII','chi_PE_ext',
                           'chi_LW_ext','chi_H2_ext','chi_CI_ext',
                           'T','pok','cool_rate','heat_rate'])
        dd = dd.assign(xi_CR=dd['z']*0.0 + s.par['problem']['xi_CR0'])
    else:
        dd = ds.get_field(['nH','nH2','nHI','xH2','xHII','xe',
                           'xHI','xCII','chi_PE_ext', 'xi_CR',
                           'chi_LW_ext','chi_H2_ext','chi_CI_ext',
                           'T','pok','cool_rate','heat_rate'])
    print('basename:',s.basename, end=' ')
    print('time:', ds.domain['time'])
    
    from pyathena.microphysics.cool import \
        get_xCO, get_xe_mol, heatPE, heatPE_BT94, heatPE_W03,\
        heatCR, heatH2form, heatH2pump, heatH2diss,\
        coolCII, coolOI, coolRec, coolRec_BT94, coolRec_W03,\
        coolLya, coolCI, coolCO

    Z_d = s.par['problem']['Z_dust']
    Z_g = s.par['problem']['Z_gas']
    xCstd = s.par['cooling']['xCstd']
    xOstd = s.par['cooling']['xOstd']
    
    xCO, ncrit = get_xCO(dd.nH, dd.xH2, dd.xCII, Z_d, Z_g,
                         dd['xi_CR'], dd['chi_LW_ext'], xCstd)
    dd['xCO'] = xCO
    dd['ncrit'] = ncrit
    dd['xOI'] = np.maximum(0.0, xOstd*Z_g - dd['xCO'])
    dd['xCI'] = np.maximum(0.0, xCstd*Z_g - dd.xCII - dd.xCO)
    dd['xe_mol'] = get_xe_mol(dd.nH, dd.xH2, dd.xe, dd.T, dd['xi_CR'], Z_g, Z_d)
    
    # Set nH and chi_PE as new dimensions
    log_nH = np.log10(dd.sel(z=0,y=0,method='nearest')['nH'].data)
    log_chi_PE = np.log10(dd.sel(z=0,x=0,method='nearest')['chi_PE_ext'].data)
    dd = dd.rename(dict(x='log_nH'))
    dd = dd.assign_coords(dict(log_nH=log_nH))

    dd = dd.rename(dict(y='log_chi_PE'))
    dd = dd.assign_coords(dict(log_chi_PE=log_chi_PE))

    #dd = dd.drop(['nH'])
    #dd = dd.drop(['y'])
    
    # dd = dd.rename(dict(y='log_chi_PE', chi_PE_ext='chi_PE'))
    # dd = dd.assign_coords(dict(log_chi_PE=log_chi_PE))

    # print(sel_kwargs)
    d = dd.sel(**sel_kwargs)

    # Calculate heat/cool rates
    if cool:
        if dust_model == 'BT94':
            d['heatPE'] = heatPE_BT94(d['nH'], d['T'], d['xe'], Z_d, d['chi_PE_ext'])
        elif dust_model == 'W03':
            d['heatPE'] = heatPE_W03(d['nH'], d['T'], d['xe'], Z_d, d['chi_PE_ext'])
        else:
            d['heatPE'] = heatPE(d['nH'], d['T'], d['xe'], Z_d, d['chi_PE_ext'])
        d['heatCR'] = heatCR(d['nH'], d['xe'], d['xHI'], d['xH2'], d['xi_CR'])
        d['heatH2pump'] = heatH2pump(d['nH'], d['T'], d['xHI'], d['xH2'], d['chi_H2_ext']*D0)
        d['heatH2form'] = heatH2form(d['nH'], d['T'], d['xHI'], d['xH2'], Z_d)
        d['heatH2diss'] = heatH2diss(d['xH2'], d['chi_H2_ext']*D0)
        d['coolCII'] = coolCII(d['nH'],d['T'],d['xe'],d['xHI'],d['xH2'],d['xCII'])
        d['coolOI'] = coolOI(d['nH'],d['T'],d['xe'],d['xHI'],d['xH2'],d['xOI'])
        if dust_model == 'BT94':
            d['coolRec'] = coolRec_BT94(d['nH'],d['T'],d['xe'],Z_d,d['chi_PE_ext'])
        elif dust_model == 'W03':
            d['coolRec'] = coolRec_W03(d['nH'],d['T'],d['xe'],Z_d,d['chi_PE_ext'])
        else:
            d['coolRec'] = coolRec(d['nH'],d['T'],d['xe'],Z_d,d['chi_PE_ext'])
        d['coolLya'] = coolLya(d['nH'],d['T'],d['xe'],d['xHI'])
        d['coolCI'] = coolCI(d['nH'],d['T'],d['xe'],d['xHI'],d['xH2'],d['xCI'])
        # d['coolCO'] = np.where(d['xCO'] < 1e-3*xCstd,
        #                        0.0,
        #                        d['cool_rate']/d['nH'] - d['coolCII'] -
        #                        d['coolOI'] - d['coolLya'] - d['coolCI'] - d['coolRec'])
        d['coolCO'] = coolCO(d['nH'],d['T'],d['xe'],d['xHI'],d['xH2'],d['xCO'],dvdr)
        d['cool'] = d['coolCI']+d['coolCII']+d['coolOI']+d['coolRec']+d['coolLya']+d['coolCO']
        d['heat'] = d['heatPE'] + d['heatCR'] + d['heatH2pump'] + d['heatH2form'] + d['heatH2diss']
        
        # Note that G_0 is in Habing units
        d['charging'] = 1.7*d['chi_PE_ext']*d['T']**0.5/(d['nH']*d['xe'])
        
    return d

def get_PTn_at_Pminmax(d, jump=1, kernel_width=12):
    
    from scipy import interpolate
    from scipy.signal import find_peaks
    from astropy.convolution import Gaussian1DKernel, Box1DKernel, convolve

    x = np.linspace(np.log10(d['nH']).min(),np.log10(d['nH']).max(),1200)

    # Currently, cooling solver produces glitches (should be fixed),
    # so we need to smooth data
    gP = Gaussian1DKernel(kernel_width)
    gT = Gaussian1DKernel(kernel_width)
    #gT = Box1DKernel(15)
    
    Pmin = np.zeros_like(d['log_chi_PE'][::jump])
    Pmax = np.zeros_like(d['log_chi_PE'][::jump])
    Tmin = np.zeros_like(d['log_chi_PE'][::jump])
    Tmax = np.zeros_like(d['log_chi_PE'][::jump])
    nmin = np.zeros_like(d['log_chi_PE'][::jump])
    nmax = np.zeros_like(d['log_chi_PE'][::jump])
    for i, log_chi_PE in enumerate(d['log_chi_PE'].data[::jump]):
        dd = d.sel(log_chi_PE=float(log_chi_PE), method='nearest')

        fP = interpolate.interp1d(np.log10(dd['nH']), np.log10(dd['pok']), kind='cubic')
        fT = interpolate.interp1d(np.log10(dd['nH']), np.log10(dd['T']), kind='cubic')
        yP = convolve(fP(x), gP, boundary='fill', fill_value=np.nan)
        yT = convolve(fT(x), gT, boundary='fill', fill_value=np.nan)
        try:
            ind1 = find_peaks(-yP)[0]
            ind2 = find_peaks(yP)[0]
            # print(ind1,ind2)
            if len(ind1) > 1:
                print('Multiple local minimum log_chi,idx:',log_chi_PE,ind1)
                i1 = ind1[0]
            else:
                i1 = ind1[0]
            if len(ind2) > 1:
                print('Multiple local maximum log_chi,idx:',log_chi_PE,ind2)
                i2 = ind2[0]
            else:
                i2 = ind2[0]

            Pmin[i] = 10.0**float(yP[i1])
            Pmax[i] = 10.0**float(yP[i2])
            Tmin[i] = 10.0**float(yT[i1])
            Tmax[i] = 10.0**float(yT[i2])
            nmin[i] = 10.0**float(x[i1])
            nmax[i] = 10.0**float(x[i2])
        except IndexError:
            # print('Failed to find Pmin/Pmax, log_chi_PE:',log_chi_PE)
            pass
        # break
    r = dict()
    r['Pmin'] = Pmin
    r['Pmax'] = Pmax
    r['Tmin'] = Tmin
    r['Tmax'] = Tmax
    r['nmin'] = nmin
    r['nmax'] = nmax
    
    return r

def plt_nP_nT(axes, s, da, model, suptitle,
              log_chi=np.array([-1.0,0.0,1.0,2.0,3.0]),
              lw=[1.5,3,1.5,1.5,1.5],
              labels=[r'$\chi_0=0.1$',r'$\chi_0=1$',r'$\chi_0=10$',r'$\chi_0=10^2$',
                      '_no_legend_'],
              xlim=(1e-2,1e3),
              savefig=True):
    
    # Plot equilibrium density pressure and temperature relation
    cmap = mpl.cm.viridis
    norm = mpl.colors.Normalize(-1,3.7)

    axes = axes.flatten()
    dd = da[model]
    xCstd = dd['par']['cooling']['xCstd']

    for i,log_chi_PE_ in enumerate(log_chi):
        d_ = dd.sel(log_chi_PE=log_chi_PE_, method='nearest')
        plt.sca(axes[0])
        l, = plt.loglog(d_['nH'], d_['pok'], label=labels[i],
                        c=cmap(norm(log_chi_PE_)), lw=lw[i])
        plt.sca(axes[1])
        plt.loglog(d_['nH'],d_['T'], c=l.get_color(), lw=lw[i])

    plt.sca(axes[0])
    plt.ylim(1e2,1e8)
    plt.sca(axes[1])
    plt.ylim(1e1,3e4)

    for ax in axes:
        ax.set_xlim(1e-2,1e3)
        ax.xaxis.set_ticks_position('both')
        ax.yaxis.set_ticks_position('both')
        ax.grid()

    for ax in axes:
        ax.set_xlabel(r'$n\;[{\rm cm}^{-3}]$')
        
    axes[0].set_ylabel(r'$P/k_{\rm B}\;[{\rm K\,cm^{-3}}]$')
    axes[1].set_ylabel(r'$T\;[{\rm K}]$')
    
    for ax in axes:
        ax.set_xlim(*xlim)

    return axes


def plt_rates_abd(axes, s, da, model, log_chi0=0.0, xlim=(1e-2,1e3),
                  ylims=[(1e-29,8e-24),(1e-6,2e0),(1e0,1e5)], shielded=True):

    cmap = plt.get_cmap("tab10")
    
    dd = da[model]
    axes = axes.flatten()
    d = dd.sel(log_chi_PE=log_chi0, method='nearest')
    xCstd = s.par['cooling']['xCstd']
    Z_g = s.par['problem']['Z_gas']
    Z_d = s.par['problem']['Z_dust']

    plt.sca(axes[0])
    plt.loglog(d['nH'], d['heatPE'], ls='--', label=r'PE', c=cmap(0))
    plt.loglog(d['nH'], d['heatCR'], ls='--', label=r'CR', c=cmap(1))
    plt.loglog(d['nH'], d['heatH2form'], ls='--', label=r'${\rm H}_{2,\rm {form}}$', c=cmap(2))
    plt.loglog(d['nH'], d['heatH2diss'], ls='--', label=r'${\rm H}_{2,\rm {diss}}$', c=cmap(3))
    if shielded:
        plt.loglog(d['nH'], d['heatH2pump'], ls='--', label=r'${\rm H}_{2,\rm {pump}}$', c=cmap(4))
    lCp, = plt.loglog(d['nH'], d['coolCII'], label=r'${\rm C}^+$', c=cmap(5))
    lO, = plt.loglog(d['nH'], d['coolOI'], label=r'${\rm O}^0$', c=cmap(6))
    lHp, = plt.loglog(d['nH'], d['coolLya'], label=r'Ly$\alpha$', c=cmap(7))
    lC, = plt.loglog(d['nH'], d['coolCI'], label=r'${\rm C}^0$', c=cmap(8))
    plt.loglog(d['nH'], d['coolRec'], label=r'Rec', c='lightskyblue')
    if shielded:
        # pass
        # Cool CO
        # lCO, = plt.loglog(d['nH'], d['coolCO'], label=r'CO', c=cmap(9))
        #lCO, = plt.loglog(d['nH'], d['cool_rate']/d['nH'] - d['coolCII'] - d['coolOI'] -
        #                  d['coolLya'] - d['coolCI'] - d['coolRec'], label=r'CO', c='darkblue')
        lCO, = plt.loglog(d['nH'],
                          np.where(d['xCO'] < 1e-3*xCstd*Z_g,
                                   0.0,
                                   d['cool_rate']/d['nH'] - d['coolCII'] -
                                   d['coolOI'] - d['coolLya'] - d['coolCI'] - d['coolRec']), label=r'CO', c=cmap(9))

        
    plt.loglog(d['nH'], d['cool_rate']/d['nH'], label=r'Total', c='k', lw=2)

    plt.sca(axes[1])
    plt.loglog(d['nH'],d['xHII'], label=r'${\rm H}^+$', c=lHp.get_color())
    plt.loglog(d['nH'],d['xe'], label=r'e', c='k')
    plt.loglog(d['nH'],2.0*d['xH2'], label=r'${\rm H}_2$', c='deeppink')
    plt.loglog(d['nH'],d['xCI'], ls='-', label=r'${\rm C}^0$', c=lC.get_color())
    plt.loglog(d['nH'],d['xCII'], ls='-', label=r'${\rm C}^+$', c=lCp.get_color())
    plt.loglog(d['nH'],d['xOI'], ls='-', label=r'${\rm O}^0$', c=lO.get_color())
    if shielded:
        plt.loglog(d['nH'],d['xCO'], ls='-', label=r'${\rm CO}$', c=lCO.get_color())
        plt.loglog(d['nH'],d['xe_mol'], ls='-', label=r'$x_{\rm e,MH^+}$')

    plt.sca(axes[2])
    plt.loglog(d['nH'], d['T'], ls='-', c='k')
    plt.loglog(d['nH'], 1.7*d['chi_PE_ext']*d['T']**0.5/(d['nH']*d['xe'])+50.0,
               ls='--', c='k')

    c = 'r'
    axt = axes[2].twinx()
    axt.loglog(d['nH'],d['pok']*ac.k_B.cgs.value/d['cool_rate']/(1.0*au.yr.to('s')),
               c=c, ls='-.')
    axt.spines['right'].set_color(c)
    axt.yaxis.label.set_color(c)
    axt.tick_params(axis='y', colors=c)
    axt.set_ylim(1e2,1e7)
    
    for i,ax in enumerate(axes):
        ax.set_ylim(*ylims[i])
    
    for ax in axes:
        ax.set_xlim(*xlim)
        ax.xaxis.set_ticks_position('both')
        ax.yaxis.set_ticks_position('left')
        ax.grid()

    return d
