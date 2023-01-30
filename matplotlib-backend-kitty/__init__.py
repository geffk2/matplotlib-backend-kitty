# SPDX-License-Identifier: CC0-1.0

import os
import sys

from io import BytesIO
from subprocess import run

from matplotlib import interactive, is_interactive
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import (_Backend, FigureManagerBase)
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import ColorConverter


import numpy as np

to_rgba = ColorConverter().to_rgba

# XXX heuristic for interactive repl
if sys.flags.interactive:
    interactive(True)

# Credit: daleroberts/itermplot
def revvideo(x):
    """Try to 'reverse video' the color. Otherwise,
    return the object unchanged if it can't."""

    def rev(c):
        if isinstance(c, str):
            c = to_rgba(c)

        if len(c) == 4:
            r, g, b, a = c
            return (1.0 - r, 1.0 - g, 1.0 - b, a)
        else:
            r, g, b = c
            return (1.0 - r, 1.0 - g, 1.0 - b, 1.0)

    try:
        if isinstance(x, str) and x == "none":
            return x
        if isinstance(x, np.ndarray):
            return np.array([rev(el) for el in x])
        return rev(x)
    except (ValueError, KeyError) as e:
        print("bad", x, e)
        return x

class FigureManagerICat(FigureManagerBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.reversed = False

    def reverse(self):
        if self.reversed: 
            return

        def modify(c):
            fcset = False

            try:
                ec = obj.get_edgecolor()
                obj.set_edgecolor(revvideo(ec))
            except AttributeError as e:
                pass

            try:
                fc = obj.get_facecolor()
                obj.set_facecolor(revvideo(fc))
                fcset = True
            except AttributeError as e:
                pass

            try:
                if not fcset:
                    c = obj.get_color()
                    obj.set_color(revvideo(c))
            except AttributeError as e:
                pass 

        seen = set()
        for obj in self.canvas.figure.findobj():
            if not obj in seen:
                modify(obj)
            seen.add(obj)
        self.reversed = True

    @classmethod
    def _run(cls, *cmd):
        def f(*args, output=True, **kwargs):
            if output:
                kwargs['capture_output'] = True
                kwargs['text'] = True
            r = run(cmd + args, **kwargs)
            if output:
                return r.stdout.rstrip()
        return f

    def show(self):

        icat = __class__._run('wezterm', 'imgcat')

        if os.environ.get('MPLBACKEND_KITTY_SIZING', 'automatic') != 'manual':

            tput = __class__._run('tput')

            # gather terminal dimensions
            rows = int(tput('lines'))
            px = icat('--print-window-size')
            px = list(map(int, px.split('x')))

            # account for post-display prompt scrolling
            # 3 line shift for [\n, <matplotlib.axes…, >>>] after the figure
            px[1] -= int(3*(px[1]/rows))

            # resize figure to terminal size & aspect ratio
            dpi = self.canvas.figure.dpi
            self.canvas.figure.set_size_inches((px[0] / dpi, px[1] / dpi))

        with BytesIO() as buf:
            self.reverse()
            self.canvas.figure.savefig(buf, format='png', transparent=True)
            icat(output=False, input=buf.getbuffer())


class FigureCanvasICat(FigureCanvasAgg):
    manager_class = FigureManagerICat


@_Backend.export
class _BackendICatAgg(_Backend):

    FigureCanvas = FigureCanvasICat
    FigureManager = FigureManagerICat

    # Noop function instead of None signals that
    # this is an "interactive" backend
    mainloop = lambda: None

    # XXX: `draw_if_interactive` isn't really intended for
    # on-shot rendering. We run the risk of being called
    # on a figure that isn't completely rendered yet, so
    # we skip draw calls for figures that we detect as
    # not being fully initialized yet. Our heuristic for
    # that is the presence of axes on the figure.
    @classmethod
    def draw_if_interactive(cls):
        manager = Gcf.get_active()
        if is_interactive() and manager.canvas.figure.get_axes():
            cls.show()

    @classmethod
    def show(cls, *args, **kwargs):
        _Backend.show(*args, **kwargs)
        Gcf.destroy_all()
