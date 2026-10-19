"""Expected Falcon Prime returns on a flat target from the datasheet raster (single return, full fill):
n = (w / (r * d_az)) * (h / (r * d_el)); ROI 0.09 x 0.08 deg, non-ROI 0.18 x 0.24 deg (datasheet, checked in the PDF).
Validated against the reviewed person returns (raw_person_review/atlas_proposals.json: 5-8 returns at 240-248 m).
The reflectivity line is the square-root scaling for an extended Lambertian target: a heuristic, not a datasheet value.
"""
import math


def n(r, w, h, dh, dv):
    return (w / (r * math.radians(dh))) * (h / (r * math.radians(dv)))


print("range | non-ROI: person 0.5x1.7 / 1 m box / 0.3 m cube | ROI: person / 1 m box / 0.3 m cube")
for r in (100, 150, 200, 250, 300):
    a = [n(r, .5, 1.7, .18, .24), n(r, 1, 1, .18, .24), n(r, .3, .3, .18, .24)]
    b = [n(r, .5, 1.7, .09, .08), n(r, 1, 1, .09, .08), n(r, .3, .3, .09, .08)]
    print(f"{r:4d} m | " + " / ".join(f"{v:5.1f}" for v in a) + " | " + " / ".join(f"{v:5.1f}" for v in b))
for rho in (0.05, 0.10, 0.20, 0.30, 0.50):
    print(f"reflectivity {rho:.2f}: scaled 90 %-detection range {250 * math.sqrt(rho / 0.10):.0f} m (heuristic)")
