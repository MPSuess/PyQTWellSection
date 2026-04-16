# Source - https://stackoverflow.com/a/23940526
# Posted by GBy
# Retrieved 2026-03-28, License - CC BY-SA 3.0

import numpy as np
import matplotlib.hatch
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse, Polygon

from matplotlib.patches import PathPatch
from matplotlib.path import Path

vertices = []
codes = []

codes = [Path.MOVETO] + [Path.LINETO]*2 + [Path.CLOSEPOLY]
vertices = [(-0.3, 0.255), (0.3,0.255), (0.3, 0.2455), (-0.3, 0.2455)]

codes += [Path.MOVETO] + [Path.LINETO]*2 + [Path.CLOSEPOLY]
vertices += [(-0.3, -0.255), (0.3,-0.255), (0.3, -0.2455), (-0.3, -0.2455)]

shale_fine_path = Path(vertices, codes)

shale_coarse_path = Polygon(
    [[-0.3, -0.025], [0.3, -0.025], [0.3, 0.025], [-0.3, 0.025]],
    closed=True, fill=False).get_path()

class Shale_Coarse_Hatch(matplotlib.hatch.Shapes):
    """
    Custom hatches defined by a path drawn inside [-0.5, 0.5] square.
    Identifier 'c'.
    """
    filled = True
    size = 1
    path = shale_coarse_path

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('_')) * density
        self.shape_vertices = self.path.vertices
        self.shape_codes = self.path.codes
        matplotlib.hatch.Shapes.__init__(self, hatch, density)

class Shale_Fine_Hatch(matplotlib.hatch.Shapes):
    """
    Custom hatches defined by a path drawn inside [-0.5, 0.5] square.
    Identifier 'c'.
    """
    filled = True
    size = 1
    path = shale_fine_path

    def __init__(self, hatch, density):
        self.num_rows = (hatch.count('__')) * density
        self.shape_vertices = self.path.vertices
        self.shape_codes = self.path.codes
        matplotlib.hatch.Shapes.__init__(self, hatch, density)

matplotlib.hatch._hatch_types.append(Shale_Coarse_Hatch)
matplotlib.hatch._hatch_types.append(Shale_Fine_Hatch)