import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

def plt_joint_pdf(x, y, hexbin_args, weights=None):
    fig = plt.figure(figsize=(6, 6))
    gs = GridSpec(4, 4)
    ax = fig.add_subplot(gs[1:4,0:3])
    
    # Axes for marginalized quantities
    axx = fig.add_subplot(gs[0,0:3])
    axy = fig.add_subplot(gs[1:4,3])

    _hexbin_args = dict()
    _hexbin_args['xscale'] = 'linear'
    _hexbin_args['yscale'] = 'linear'
    _hexbin_args.update(**hexbin_args)
    
    if weights is not None:
        _hexbin_args['C'] = weights
        _hexbin_args['reduce_C_function'] = np.sum
        
    # joint pdfs
    ax.hexbin(x, y, **_hexbin_args)
    
    # plot marginalized pdfs
    bins = 30
    if _hexbin_args['xscale'] == 'log':
        h, bine = np.histogram(np.log10(x),weights=weights, bins=bins, density=True)
        axx.step(10.0**bine[1:], h, 'k-')
        axx.set_xscale('log')
    else:
        h, bine = np.histogram(x, weights=weights, bins=bins, density=True)
        axx.step(bine[1:], h, 'k-')
        
    if _hexbin_args['yscale'] == 'log':
        h, bine = np.histogram(np.log10(y), weights=weights, bins=bins, density=True)
        axy.step(h, 10.0**bine[1:], 'k-')
        axy.set_yscale('log')
    else:
        h, bine = np.histogram(y, weights=weights, bins=bins, density=True)
        axy.step(h, bine[1:], 'k-')
    
    # Turn off tick labels on marginals
    plt.setp(axx.get_xticklabels(), visible=False)
    plt.setp(axy.get_yticklabels(), visible=False)

    # Set labels on marginals
    axx.set_ylabel('pdf')
    axy.set_xlabel('pdf')

    return ax, axx, axy
