# -*- coding: utf-8 -*-
# pylint: disable=logging-fstring-interpolation
"""
Plot visualizations with parsed Apple Health Data
"""

from math import floor, ceil
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import get_cmap


def plot_map(data, heartrate=None):
    """Plot the elevation profile with heart rate annotations."""

    fig = plt.figure()
    ax1 = fig.add_subplot(111)
    ax1.axis('off')

    xdata = data['latitude']
    ydata = data['lonitude']
    zdata = heartrate
    cmap = get_cmap('viridis')

    if zdata is not None:
        norm = Normalize(vmin=floor(min(zdata)), vmax=ceil(max(zdata)))
        colors = [cmap(norm(i)) for i in zdata]
    else:
        colors = ['k' for i in xdata]

    for i in range(0, len(xdata)-1):
        ax1.plot(
            [xdata[i], xdata[i+1]],
            [ydata[i], ydata[i+1]],
            color=colors[i],
            lw=2
        )

    fig.tight_layout()

    return fig
