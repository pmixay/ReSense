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

}  // namespace

extern "C" {

int rs_abi_version() { return 1; }

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
// k-th farthest forward return within ``band`` of the track axis (0 when there is none).
double rs_visibility(const float* xyz, int64_t n, double c, double t, double hk, double band, int64_t k) {
    std::vector<double> xs;
    xs.reserve(static_cast<size_t>(n / 4 + 16));
    for (int64_t j = 0; j < n; ++j) {
        const float* p = xyz + 3 * j;
        if (!(p[0] > 0.0f)) continue;
        const double x = static_cast<double>(p[0]);
        if (std::fabs(static_cast<double>(p[1]) - center_y1(x, c, t, hk)) < band) xs.push_back(x);
    }
    const int64_t m = static_cast<int64_t>(xs.size());
    if (m == 0) return 0.0;
    if (m <= k) return *std::min_element(xs.begin(), xs.end());
    std::nth_element(xs.begin(), xs.begin() + (m - k), xs.end());
    return xs[static_cast<size_t>(m - k)];
}

}  // extern "C"
