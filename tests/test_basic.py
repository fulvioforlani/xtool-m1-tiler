import json
import os
import tempfile

from xtool_m1_tiler import Options, convert

HERE = os.path.dirname(__file__)
DEMO = os.path.join(HERE, "..", "examples", "demo.svg")


def test_demo_splits_and_writes_valid_xcs():
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "demo.xcs")
        r = convert(DEMO, out, Options(size_mm=100))
        assert r.groups >= 2
        assert r.minutes_split < r.minutes_single
        doc = json.load(open(out, encoding="utf8"))
        disp = doc["canvas"][0]["displays"]
        assert len(disp) == r.groups + 1          # gruppi + taglio
        params = {}
        for _, v in doc["device"]["data"]["value"]:
            for uid, dp in v["displays"]["value"]:
                kind = dp["processingType"]
                c = dp["data"][kind]["parameter"]["customize"]
                params[uid] = (kind, c["power"], c["speed"])
        fills = [p for p in params.values() if p[0] == "FILL_VECTOR_ENGRAVING"]
        # ogni gruppo deve avere parametri DIVERSI (altrimenti xTool li unisce)
        assert len({(p[1], p[2]) for p in fills}) == len(fills)
        assert doc["device"]["data"]["value"][0][1]["data"]["LASER_PLANE"]["thickness"] == 2.0


def test_cut_subpaths_preserved():
    with tempfile.TemporaryDirectory() as d:
        r = convert(DEMO, os.path.join(d, "a.xcs"), Options())
        assert len(r.cut_rings) == 2              # contorno + foro


def test_max_groups_one_means_no_split():
    with tempfile.TemporaryDirectory() as d:
        r = convert(DEMO, os.path.join(d, "a.xcs"), Options(max_groups=1))
        assert r.groups == 1
