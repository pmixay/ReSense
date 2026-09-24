// ReSense optional native kernels (plain C ABI, loaded with ctypes by resense/_native.py).
//
// Every function here is a drop-in for a numpy expression in resense/ and must return
// bit-identical results: the same IEEE double operations in the same order (no FMA
// contraction: build with -ffp-contract=off, never -ffast-math / -march=native), and the
// same order statistics (a selection returns the element a stable sort would put at that
// rank). tests/test_native.py compares every kernel with the numpy code it replaces.
//
// Build (setup.py does it on `pip install`; for a source checkout):
//   python setup.py build_ext --inplace      or      scripts/build_native.sh
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <vector>

// Generic conjunction of range tests (np.flatnonzero of a numpy mask chain): per condition a
// float32 or float64 column (byte stride), optionally its absolute value, a lower test (0 none,
// 1 >, 2 >=) and an upper test (0 none, 1 <, 2 <=). float32 columns compare in float32.
struct RsCond {
    const void* data;
    int64_t stride;
    int32_t is_f64;
    int32_t absval;
    int32_t lo_op;
    int32_t hi_op;
    double lo;
    double hi;
};

namespace {

struct Item {
    double v;
    int64_t i;
};

// numpy's sort order for float64 (NaN after every number), ties by original index: the
// order of np.lexsort((values, bins)) within one bin.
inline bool item_less(const Item& a, const Item& b) {
    const bool an = std::isnan(a.v), bn = std::isnan(b.v);
    if (an || bn) {
        if (an && bn) return a.i < b.i;
        return bn;                       // a is a number, b is NaN
    }
    if (a.v < b.v) return true;
    if (b.v < a.v) return false;
    return a.i < b.i;
}

inline double load(const char* base, int64_t k, int64_t stride, int is_f64) {
    const char* p = base + k * stride;
    if (is_f64) {
        double d;
        std::memcpy(&d, p, sizeof d);
        return d;
    }
    float f;
    std::memcpy(&f, p, sizeof f);
    return static_cast<double>(f);
}

// TrackModel.floor_z for a quadratic: (a2 Xc + a1) Xc + a0 + (2 a2 Xc + a1) (X - Xc), Xc = clip(X, x0, x1)
inline double floor_z1(double x, double x0, double x1, double a2, double a1, double a0, double a2x2) {
    const double xc = std::min(std::max(x, x0), x1);   // np.clip = minimum(maximum(x, lo), hi)
    const double t = (a2 * xc + a1) * xc + a0;
    const double s = (a2x2 * xc + a1) * (x - xc);
    return t + s;
}

// TrackModel.center_y: center + tan(yaw) X + (0.5 curvature) X X
inline double center_y1(double x, double c, double t, double hk) {
    return (c + t * x) + (hk * x) * x;
}

// np.digitize(x, edges) - 1 for increasing edges (np.searchsorted(edges, x, "right") - 1)
inline int64_t bin_of(double x, const double* edges, int64_t ne) {
    return static_cast<int64_t>(std::upper_bound(edges, edges + ne, x) - edges) - 1;
}

template <typename T>
inline bool cond_ok(const RsCond& q, int64_t k) {
    T v;
    std::memcpy(&v, static_cast<const char*>(q.data) + k * q.stride, sizeof v);
    if (q.absval) v = std::fabs(v);
    const T lo = static_cast<T>(q.lo), hi = static_cast<T>(q.hi);
    if (q.lo_op == 1 && !(v > lo)) return false;
    if (q.lo_op == 2 && !(v >= lo)) return false;
    if (q.hi_op == 1 && !(v < hi)) return false;
    if (q.hi_op == 2 && !(v <= hi)) return false;
    return true;
}

}  // namespace

extern "C" {

int rs_abi_version() { return 2; }

// resense.track.bin_percentile: per-bin percentile of ``values`` (linear interpolation between
// the two order statistics around the rank, as np.percentile), bins with fewer than
// ``min_points`` values stay NaN; with ``payload`` the payload of the value at the nearest rank.
// ``prof`` / ``payload_out`` (nb) must be NaN-filled and ``counts`` (nb) zeroed by the caller.
// Bins >= nb are ignored (they sort after every real bin in the numpy code). Returns 0, or -1
// on a negative bin (the numpy code raises; the caller falls back to it).
int rs_bin_percentile(const double* values, const int64_t* bins, int64_t n, int64_t nb,
                      double percentile, int64_t min_points, const double* payload,
                      double* prof, int64_t* counts, double* payload_out) {
    for (int64_t k = 0; k < n; ++k) {
        const int64_t b = bins[k];
        if (b < 0) return -1;
        if (b < nb) ++counts[b];
    }
    if (n == 0) return 0;
    std::vector<int64_t> start(static_cast<size_t>(nb) + 1, 0);
    for (int64_t b = 0; b < nb; ++b) start[b + 1] = start[b] + counts[b];
    std::vector<Item> items(static_cast<size_t>(start[nb]));
    std::vector<int64_t> cur(start.begin(), start.end() - 1);
    for (int64_t k = 0; k < n; ++k) {
        const int64_t b = bins[k];
        if (b < nb) items[cur[b]++] = Item{values[k], k};
    }
    const int64_t mp = std::max<int64_t>(1, min_points);
    const double p = percentile / 100.0;
    for (int64_t b = 0; b < nb; ++b) {
        const int64_t c = counts[b];
        if (c < mp) continue;
        const double pos = p * static_cast<double>(c - 1);
        const int64_t lo = static_cast<int64_t>(std::floor(pos));
        const double frac = pos - static_cast<double>(lo);
        if (lo < 0 || lo >= c) return -1;       // a percentile outside [0, 100]: left to numpy
        const int64_t r1 = std::min(lo + 1, c - 1);
        Item* seg = items.data() + start[b];
        std::nth_element(seg, seg + lo, seg + c, item_less);
        const Item a = seg[lo];
        const Item z = (r1 == lo) ? a : *std::min_element(seg + lo + 1, seg + c, item_less);
        prof[b] = a.v * (1.0 - frac) + z.v * frac;
        if (payload != nullptr) payload_out[b] = payload[frac > 0.5 ? z.i : a.i];
    }
    return 0;
}

// TrackModel.floor_z(X) (quadratic coefficients) for float32 / float64 X with a byte stride.
void rs_floor_z(const void* X, int64_t n, int64_t stride, int is_f64, double x0, double x1,
                double a2, double a1, double a0, double* out) {
    const char* base = static_cast<const char*>(X);
    const double a2x2 = 2.0 * a2;
    for (int64_t k = 0; k < n; ++k)
        out[k] = floor_z1(load(base, k, stride, is_f64), x0, x1, a2, a1, a0, a2x2);
}

// TrackModel.center_y(X) for float32 / float64 X with a byte stride.
void rs_center_y(const void* X, int64_t n, int64_t stride, int is_f64, double c, double t, double hk,
                 double* out) {
    const char* base = static_cast<const char*>(X);
    for (int64_t k = 0; k < n; ++k) out[k] = center_y1(load(base, k, stride, is_f64), c, t, hk);
}

// resense.gauge.corridor_coordinates for a C-contiguous float32 (n, 3) cloud:
// dy = y - center_y(X), h = z - (floor_z(X) + rail_offset).
void rs_corridor_coordinates(const float* xyz, int64_t n, double x0, double x1, double a2, double a1,
                             double a0, double rail_offset, double c, double t, double hk,
                             double* dy, double* h) {
    const double a2x2 = 2.0 * a2;
    for (int64_t k = 0; k < n; ++k) {
        const float* p = xyz + 3 * k;
        const double x = static_cast<double>(p[0]);
        dy[k] = static_cast<double>(p[1]) - center_y1(x, c, t, hk);
        h[k] = static_cast<double>(p[2]) - (floor_z1(x, x0, x1, a2, a1, a0, a2x2) + rail_offset);
    }
}

// resense.health.visibility_along_track for a C-contiguous float32 (n, 3) cloud: X of the
// k-th farthest forward return within ``band`` of the track axis (0 when there is none; the
// nearest one when there are at most k). The k largest values are kept in a min-heap: its top is
// the value np.partition puts at rank m - k.
double rs_visibility(const float* xyz, int64_t n, double c, double t, double hk, double band, int64_t k) {
    if (k < 1) k = 1;
    std::vector<double> heap;
    heap.reserve(static_cast<size_t>(k));
    const auto gt = [](double a, double b) { return a > b; };
    int64_t m = 0;
    double lo = 0.0;
    for (int64_t j = 0; j < n; ++j) {
        const float* p = xyz + 3 * j;
        if (!(p[0] > 0.0f)) continue;
        const double x = static_cast<double>(p[0]);
        if (!(std::fabs(static_cast<double>(p[1]) - center_y1(x, c, t, hk)) < band)) continue;
        lo = (m == 0) ? x : std::min(lo, x);
        ++m;
        if (static_cast<int64_t>(heap.size()) < k) {
            heap.push_back(x);
            std::push_heap(heap.begin(), heap.end(), gt);
        } else if (x > heap.front()) {
            std::pop_heap(heap.begin(), heap.end(), gt);
            heap.back() = x;
            std::push_heap(heap.begin(), heap.end(), gt);
        }
    }
    if (m == 0) return 0.0;
    if (m <= k) return lo;
    return heap.front();
}

// ---------------------------------------------------------------------------------------------
// Selection prologues of the track stage (resense/track.py, lowobj.py, gauge.py): the masks and
// gathers over the whole cloud, fused into one pass each. A float32 coordinate is compared with
// a threshold in float32, as numpy does for a Python float threshold (resense/_native.py passes
// only Python floats here and falls back to numpy otherwise). Outputs keep the point order.
// ---------------------------------------------------------------------------------------------

// _fit_floor: band = (X >= x0) & (X < x1) & (|Y - center_y(X)| < halfwidth); for the band points in
// a bin: Z (float64) and the bin. Returns the band size (the numpy code's Xb.size).
int64_t rs_floor_band(const float* xyz, int64_t n, float x0, float x1, double c, double t, double hk,
                      double halfwidth, const double* edges, int64_t ne, double* zb, int64_t* bins,
                      int64_t* n_out) {
    int64_t nband = 0, m = 0;
    const int64_t nb = ne - 1;
    for (int64_t k = 0; k < n; ++k) {
        const float* p = xyz + 3 * k;
        if (!(p[0] >= x0 && p[0] < x1)) continue;
        const double x = static_cast<double>(p[0]);
        if (!(std::fabs(static_cast<double>(p[1]) - center_y1(x, c, t, hk)) < halfwidth)) continue;
        ++nband;
        const int64_t b = bin_of(x, edges, ne);
        if (b >= 0 && b < nb) {
            zb[m] = static_cast<double>(p[2]);
            bins[m] = b;
            ++m;
        }
    }
    *n_out = m;
    return nband;
}

// estimate_rails: near = (X > x0) & (X < x1); h = Z - zf; Yp = Y - (t X + hk X X) (Y without a prior);
// sel = (|Yp - center| < half) & (h > -0.4) & (h < 0.8). Writes X, Yp, h of the selection.
int64_t rs_rails_band(const float* xyz, const double* zf, int64_t n, float x0, float x1, int has_prior,
                      double t, double hk, double center, double half, double* xs, double* ys, double* hs) {
    int64_t m = 0;
    for (int64_t k = 0; k < n; ++k) {
        const float* p = xyz + 3 * k;
        if (!(p[0] > x0 && p[0] < x1)) continue;
        const double x = static_cast<double>(p[0]);
        const double h = static_cast<double>(p[2]) - zf[k];
        const double yn = static_cast<double>(p[1]);
        const double yp = has_prior ? yn - (t * x + (hk * x) * x) : yn;
        if (std::fabs(yp - center) < half && h > -0.4 && h < 0.8) {
            xs[m] = x;
            ys[m] = yp;
            hs[m] = h;
            ++m;
        }
    }
    return m;
}

// estimate_axis_from_walls: h = Z - (zf + rail_offset); band = (X > x0) & (X < x1) & (h > b0) & (h < b1).
// Writes X, Y (float32, as X[band], Y[band]) and dy = Y - center_y(X) of the band points.
int64_t rs_walls_band(const float* xyz, const double* zf, int64_t n, double rail_offset, float x0, float x1,
                      double b0, double b1, double c, double t, double hk, float* xb, float* yb, double* dy) {
    int64_t m = 0;
    for (int64_t k = 0; k < n; ++k) {
        const float* p = xyz + 3 * k;
        if (!(p[0] > x0 && p[0] < x1)) continue;
        const double h = static_cast<double>(p[2]) - (zf[k] + rail_offset);
        if (!(h > b0 && h < b1)) continue;
        xb[m] = p[0];
        yb[m] = p[1];
        dy[m] = static_cast<double>(p[1]) - center_y1(static_cast<double>(p[0]), c, t, hk);
        ++m;
    }
    return m;
}

// verify_floor_extrapolation: sel = (X > x0) & (X < x1); side = b0 < |Y - center_y(X)| < b1;
// hs = Z - zf, kept where hs > -1; per bin (clipped to the edges) the count and np.minimum.at of
// hs. counts must be zeroed and base inf-filled by the caller. n_sel / n_side: the sizes the
// numpy code tests before binning.
void rs_verify_profile(const float* xyz, const double* zf, int64_t n, float x0, float x1, double c, double t,
                       double hk, double b0, double b1, const double* edges, int64_t ne, int64_t* counts,
                       double* base, int64_t* n_sel, int64_t* n_side) {
    int64_t ns = 0, nd = 0;
    const int64_t nb = ne - 1;
    for (int64_t k = 0; k < n; ++k) {
        const float* p = xyz + 3 * k;
        if (!(p[0] > x0 && p[0] < x1)) continue;
        ++ns;
        const double x = static_cast<double>(p[0]);
        const double ady = std::fabs(static_cast<double>(p[1]) - center_y1(x, c, t, hk));
        if (!(ady > b0 && ady < b1)) continue;
        ++nd;
        const double h = static_cast<double>(p[2]) - zf[k];
        if (!(h > -1.0)) continue;
        const int64_t b = std::min(std::max(bin_of(x, edges, ne), int64_t(0)), nb - 1);
        ++counts[b];
        const double a = base[b];
        base[b] = (a < h || std::isnan(a)) ? a : h;          // numpy's minimum: NaN wins, ties take h
    }
    *n_sel = ns;
    *n_side = nd;
}

// np.flatnonzero of the conjunction of ``nc`` conditions (RsCond above).
int64_t rs_select(int64_t n, const RsCond* conds, int32_t nc, int64_t* out) {
    int64_t m = 0;
    for (int64_t k = 0; k < n; ++k) {
        bool ok = true;
        for (int32_t j = 0; j < nc && ok; ++j)
            ok = conds[j].is_f64 ? cond_ok<double>(conds[j], k) : cond_ok<float>(conds[j], k);
        if (ok) out[m++] = k;
    }
    return m;
}

}  // extern "C"
