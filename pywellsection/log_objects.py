### Definition of log objects

import uuid


class BaseLog:
    """
    Base class for all log types.
    """

    def __init__(self, name: str, well_uid: str, log_type: str):
        self.id = str(uuid.uuid4())
        self.name = name
        self.well_uid = well_uid
        self.type = log_type  # continuous, discrete, bitmap, facies

    # ----------------------------------
    # Serialization
    # ----------------------------------
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "well_uid": self.well_uid,
            "type": self.type,
        }

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            name=data.get("name"),
            well_uid=data.get("well_uid"),
            log_type=data.get("type"),
        )
        obj.id = data.get("id", obj.id)
        return obj


class ContinuousLog(BaseLog):

    def __init__(self, name: str, well_uid: str, depth=None, data=None):
        super().__init__(name, well_uid, "continuous")

        self.depth = depth or []
        self.data = data or []

        # display settings
        self.color = "black"
        self.xscale = "linear"
        self.direction = "normal"
        self.xlim = None
        self.render = "line"      # line or points
        self.marker = "."
        self.markersize = 2.0
        self.alpha = 1.0

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "depth": self.depth,
            "data": self.data,
            "display": {
                "color": self.color,
                "xscale": self.xscale,
                "direction": self.direction,
                "xlim": self.xlim,
                "render": self.render,
                "marker": self.marker,
                "markersize": self.markersize,
                "alpha": self.alpha,
            }
        })
        return d

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            name=data.get("name"),
            well_uid=data.get("well_uid"),
            depth=data.get("depth", []),
            data=data.get("data", []),
        )
        obj.id = data.get("id", obj.id)

        disp = data.get("display", {})
        obj.color = disp.get("color", "black")
        obj.xscale = disp.get("xscale", "linear")
        obj.direction = disp.get("direction", "normal")
        obj.xlim = disp.get("xlim")
        obj.render = disp.get("render", "line")
        obj.marker = disp.get("marker", ".")
        obj.markersize = disp.get("markersize", 2.0)
        obj.alpha = disp.get("alpha", 1.0)

        return obj

class DiscreteLog(BaseLog):

    def __init__(self, name: str, well_uid: str, depth=None, values=None):
        super().__init__(name, well_uid, "discrete")

        self.depth = depth or []
        self.values = values or []
        self.missing = "-999"

        self.color_map = {}
        self.default_color = "#dddddd"

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "depth": self.depth,
            "values": self.values,
            "missing": self.missing,
            "color_map": self.color_map,
            "default_color": self.default_color,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            name=data.get("name"),
            well_uid=data.get("well_uid"),
            depth=data.get("depth", []),
            values=data.get("values", []),
        )
        obj.id = data.get("id", obj.id)
        obj.missing = data.get("missing", "-999")
        obj.color_map = data.get("color_map", {})
        obj.default_color = data.get("default_color", "#dddddd")
        return obj

class BitmapLog(BaseLog):

    def __init__(self, name: str, well_uid: str, path=None):
        super().__init__(name, well_uid, "bitmap")

        self.path = path
        self.top_depth = 0.0
        self.base_depth = 0.0

        self.alpha = 1.0
        self.cmap = None
        self.flip_vertical = False

    def to_dict(self):
        d = super().to_dict()
        d.update({
            "path": self.path,
            "top_depth": self.top_depth,
            "base_depth": self.base_depth,
            "alpha": self.alpha,
            "cmap": self.cmap,
            "flip_vertical": self.flip_vertical,
        })
        return d

    @classmethod
    def from_dict(cls, data: dict):
        obj = cls(
            name=data.get("name"),
            well_uid=data.get("well_uid"),
            path=data.get("path"),
        )
        obj.id = data.get("id", obj.id)
        obj.top_depth = data.get("top_depth", 0.0)
        obj.base_depth = data.get("base_depth", 0.0)
        obj.alpha = data.get("alpha", 1.0)
        obj.cmap = data.get("cmap")
        obj.flip_vertical = data.get("flip_vertical", False)
        return obj

