#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render ORVANTA's photorealistic artwork.

A small deterministic ray tracer (orthographic camera) for the ORVANTA motif:
a ringed ice giant with a cyan moon in front of a nebula and a star field.
Physically motivated shading: Lambert lighting with a soft terminator, limb
darkening, atmospheric rim scattering, ring shadow on the planet, planet
shadow on the rings, ring/planet depth order, star point-spread functions,
bloom, filmic tone mapping, vignette and grain.

Outputs (fixed seeds, so re-running gives the same images):
  config/includes.chroot/usr/share/wallpapers/Orvanta/contents/images/3840x2400.jpg
  config/includes.chroot/usr/share/wallpapers/Orvanta/contents/images/3840x2160.jpg
  config/bootloaders/grub-pc/splash.svg   (background embedded as JPEG)

Requires numpy and Pillow (Debian: python3-numpy python3-pil).
Usage: python3 scripts/render-artwork.py [--only wallpaper|splash]
"""
import argparse
import base64
import io
import math
import pathlib

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
F = np.float32


# --------------------------------------------------------------------------- noise
_GX = np.array([1, -1, 1, -1, 1, -1, 1, -1, 0, 0, 0, 0], F)
_GY = np.array([1, 1, -1, -1, 0, 0, 0, 0, 1, -1, 1, -1], F)
_GZ = np.array([0, 0, 0, 0, 1, 1, -1, -1, 1, 1, -1, -1], F)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


class Perlin:
    """Vectorised 3-D gradient noise (improved Perlin), range about [-1, 1]."""

    def __init__(self, seed):
        p = np.random.default_rng(seed).permutation(256).astype(np.int32)
        self.p = np.concatenate([p, p])

    def __call__(self, x, y, z):
        x = np.asarray(x, F); y = np.asarray(y, F); z = np.asarray(z, F)
        fx, fy, fz = np.floor(x), np.floor(y), np.floor(z)
        xf, yf, zf = x - fx, y - fy, z - fz
        xi = fx.astype(np.int64) & 255
        yi = fy.astype(np.int64) & 255
        zi = fz.astype(np.int64) & 255
        u, v, w = _fade(xf), _fade(yf), _fade(zf)
        p = self.p

        def grad(ix, iy, iz, dx, dy, dz):
            h = p[p[p[ix] + iy] + iz] % 12
            return _GX[h] * (xf - dx) + _GY[h] * (yf - dy) + _GZ[h] * (zf - dz)

        x1, y1, z1 = (xi + 1) & 255, (yi + 1) & 255, (zi + 1) & 255
        a = grad(xi, yi, zi, 0, 0, 0); b = grad(x1, yi, zi, 1, 0, 0)
        x00 = a + u * (b - a)
        a = grad(xi, y1, zi, 0, 1, 0); b = grad(x1, y1, zi, 1, 1, 0)
        x10 = a + u * (b - a)
        a = grad(xi, yi, z1, 0, 0, 1); b = grad(x1, yi, z1, 1, 0, 1)
        x01 = a + u * (b - a)
        a = grad(xi, y1, z1, 0, 1, 1); b = grad(x1, y1, z1, 1, 1, 1)
        x11 = a + u * (b - a)
        y0 = x00 + v * (x10 - x00)
        y1_ = x01 + v * (x11 - x01)
        return (y0 + w * (y1_ - y0)).astype(F)

    def fbm(self, x, y, z, octaves, lacunarity=2.03, gain=0.5, ridged=False):
        total = np.zeros(np.shape(x), F)
        amp, freq, norm = 1.0, 1.0, 0.0
        for o in range(octaves):
            n = self(x * freq + o * 31.7, y * freq - o * 17.3, z * freq + o * 11.9)
            if ridged:
                n = 1.0 - np.abs(n) * 1.6
            total += F(amp) * n
            norm += amp
            amp *= gain
            freq *= lacunarity
        return total / F(norm)


# --------------------------------------------------------------------------- helpers
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return (t * t * (3 - 2 * t)).astype(F)


def mix(a, b, t):
    return a + (b - a) * t


def normalize(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


def box_blur(img, r):
    """Separable box blur on an HxWxC array (edge-clamped)."""
    if r < 1:
        return img
    for axis in (0, 1):
        pad = [(0, 0)] * img.ndim
        pad[axis] = (r + 1, r)
        c = np.cumsum(np.pad(img, pad, mode="edge"), axis=axis, dtype=np.float64)
        n = img.shape[axis]
        hi = np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis)
        lo = np.take(c, np.arange(0, n), axis=axis)
        img = ((hi - lo) / (2 * r + 1)).astype(F)
    return img


def gauss_blur(img, sigma):
    r = max(1, int(round(sigma * 0.9)))
    for _ in range(3):
        img = box_blur(img, r)
    return img


def resize(img, w, h):
    chans = [Image.fromarray(np.ascontiguousarray(img[..., c])).resize((w, h), Image.BILINEAR)
             for c in range(img.shape[2])]
    return np.stack([np.asarray(c, F) for c in chans], axis=-1)


def aces(x):
    return np.clip((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0, 1)


def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


# --------------------------------------------------------------------------- scene
class Scene:
    """Geometry in planet radii; camera looks along -z, y up, x right."""

    def __init__(self, W, H, cx, cy, R, moon, seed=7):
        self.W, self.H, self.cx, self.cy, self.R = W, H, cx, cy, R
        self.moon = moon                      # (x px, y px, radius px)
        self.seed = seed
        self.L = normalize([-0.80, 0.30, 0.42])                 # sun direction
        e = math.asin(0.31)                                      # ring opening
        roll = math.radians(28)                                  # tilt up-right
        self.N = normalize([-math.sin(roll) * math.cos(e),
                            math.cos(roll) * math.cos(e), math.sin(e)])
        self.r_in, self.r_out = 1.38, 2.32
        self.noise = Perlin(seed)
        self.noise2 = Perlin(seed + 101)
        self._ring_lut()

    # ring radial structure: fine ringlets, two gaps, soft edges
    def _ring_lut(self):
        rho = np.linspace(self.r_in - 0.05, self.r_out + 0.05, 60000).astype(F)
        n = self.noise2
        fine = n.fbm(rho * 140, F(0.3), F(0.7), 7, gain=0.62) * 0.5 + 0.5
        broad = n.fbm(rho * 9, F(5.1), F(2.2), 4) * 0.5 + 0.5
        dens = 0.18 + 0.62 * broad + 0.7 * (fine - 0.5)
        dens *= smoothstep(self.r_in, self.r_in + 0.06, rho)
        dens *= 1 - smoothstep(self.r_out - 0.05, self.r_out, rho)
        dens *= 1 - 0.92 * (smoothstep(1.92, 1.935, rho) - smoothstep(1.995, 2.01, rho))
        dens *= 1 - 0.85 * (smoothstep(2.195, 2.2, rho) - smoothstep(2.212, 2.217, rho))
        dens *= 0.55 + 0.45 * smoothstep(1.38, 1.7, rho)          # faint inner C ring
        tint = n.fbm(rho * 4, F(9.0), F(1.0), 4) * 0.5 + 0.5
        bright = 0.6 + 0.55 * (n.fbm(rho * 90, F(3.3), F(7.1), 6) * 0.5 + 0.5) + 0.25 * (broad - 0.5)
        self.lut_rho, self.lut_d, self.lut_t = rho, np.clip(dens, 0, 1), tint
        self.lut_b = bright.astype(F)

    def ring_at(self, rho, with_brightness=False):
        d = np.interp(rho, self.lut_rho, self.lut_d).astype(F)
        t = np.interp(rho, self.lut_rho, self.lut_t).astype(F)
        if with_brightness:
            return d, t, np.interp(rho, self.lut_rho, self.lut_b).astype(F)
        return d, t

    # ------------------------------------------------------------------ background
    def background(self):
        W, H = self.W, self.H
        h2, w2 = H // 2, W // 2
        ys, xs = np.mgrid[0:h2, 0:w2].astype(F)
        sx, sy = xs * 2 / H, ys * 2 / H                      # height-normalised
        n = self.noise
        wx = n.fbm(sx * 1.3, sy * 1.3, F(1.7), 4)
        wy = n.fbm(sx * 1.3 + 5.2, sy * 1.3 + 1.3, F(4.1), 4)
        qx, qy = sx + 0.55 * wx, sy + 0.55 * wy
        gas = n.fbm(qx * 2.2, qy * 2.2, F(0.4), 7) * 0.5 + 0.5
        fil = n.fbm(qx * 5.0, qy * 5.0, F(8.4), 5, ridged=True)
        dust = smoothstep(0.52, 0.78, n.fbm(sx * 3.1 + 2.0, sy * 3.1, F(3.3), 6) * 0.5 + 0.5)
        # nebula lies in a diagonal band from lower left to upper right
        aspect = W / H
        d_line = (sx * 0.42 + sy * 0.91 - (0.42 * aspect * 0.55 + 0.91 * 0.62))
        band = np.exp(-(d_line / 0.42) ** 2).astype(F)
        dens = smoothstep(0.38, 0.85, gas) * band
        glow = dens ** 1.6 * (0.55 + 0.6 * smoothstep(0.2, 0.9, fil))
        deep = np.array([0.010, 0.030, 0.110], F)
        teal = np.array([0.030, 0.200, 0.320], F)
        cyan = np.array([0.250, 0.640, 0.850], F)
        violet = np.array([0.090, 0.060, 0.230], F)
        c = mix(deep, teal, smoothstep(0.05, 0.45, glow)[..., None])
        c = mix(c, cyan, smoothstep(0.45, 1.0, glow)[..., None])
        hue = (n.fbm(sx * 0.9, sy * 0.9, F(7.7), 3) * 0.5 + 0.5)[..., None]
        c = mix(c, c * 0.6 + violet * 0.8, smoothstep(0.55, 0.8, hue) * 0.6)
        neb = c * (glow * 1.45)[..., None]
        neb *= (1 - 0.75 * dust * band)[..., None]
        base = mix(np.array([0.002, 0.004, 0.012], F), np.array([0.006, 0.014, 0.036], F),
                   (sy / sy.max())[..., None])
        bg = resize((base + neb).astype(F), W, H)
        atten = resize(np.repeat((1 - 0.8 * dust * band)[..., None], 1, axis=2), W, H)[..., 0]
        return bg + self.stars(atten)

    def stars(self, atten):
        W, H = self.W, self.H
        rng = np.random.default_rng(self.seed + 5)
        img = np.zeros((H, W, 3), F)
        n = int(W * H / 260)
        x = rng.uniform(0, W - 1.001, n); y = rng.uniform(0, H - 1.001, n)
        b = np.clip(0.004 * rng.uniform(0.004, 1, n) ** -0.95, 0, 6).astype(F)
        temp = rng.uniform(0, 1, n)
        pal = np.array([[0.62, 0.76, 1.00], [0.85, 0.90, 1.00], [1.00, 1.00, 1.00],
                        [1.00, 0.92, 0.80], [1.00, 0.78, 0.56]], F)
        idx = np.clip((temp ** 1.3) * 4.0, 0, 3.999)
        col = pal[idx.astype(int)] * (1 - (idx % 1))[:, None] + pal[idx.astype(int) + 1] * (idx % 1)[:, None]
        faint = b < 0.9
        xi, yi = x[faint].astype(int), y[faint].astype(int)
        fx, fy = (x[faint] - xi).astype(F), (y[faint] - yi).astype(F)
        cb = col[faint] * b[faint][:, None]
        for dx, dy, wgt in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                            (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            np.add.at(img, (yi + dy, xi + dx), cb * wgt[:, None])
        k = np.arange(-6, 7, dtype=F)
        for i in np.nonzero(~faint)[0]:
            sig = 0.7 + 0.25 * math.log1p(b[i])
            cx, cy = int(x[i]), int(y[i])
            gx = np.exp(-((k + cx - x[i]) ** 2) / (2 * sig * sig))
            gy = np.exp(-((k + cy - y[i]) ** 2) / (2 * sig * sig))
            ker = (gy[:, None] * gx[None, :]) / (2 * math.pi * sig * sig)
            y0, x0 = cy - 6, cx - 6
            ys0, xs0 = max(0, -y0), max(0, -x0)
            ys1, xs1 = 13 - max(0, y0 + 13 - H), 13 - max(0, x0 + 13 - W)
            img[y0 + ys0:y0 + ys1, x0 + xs0:x0 + xs1] += (ker[ys0:ys1, xs0:xs1, None]
                                                          * col[i] * b[i] * 2.2)
        # a few bright stars with diffraction spikes
        hero = rng.uniform(0.04, 0.96, (4, 2)) * [W, H]
        for j, (hx, hy) in enumerate(hero):
            c = pal[[0, 1, 2, 1, 3, 0, 2][j]]
            length = (0.018 + 0.012 * rng.uniform()) * H
            for ang in (math.radians(17), math.radians(107)):
                # anti-aliased spike: samples spread bilinearly, 3 lines across
                # (about 1.5 px wide), fading quadratically towards the tips
                t = np.linspace(-length, length, int(6 * length))
                for off, wgt in ((-0.6, 0.25), (0.0, 0.5), (0.6, 0.25)):
                    px = hx + t * math.cos(ang) - off * math.sin(ang)
                    py = hy + t * math.sin(ang) + off * math.cos(ang)
                    inten = 0.10 * wgt * (1 - np.abs(t) / length) ** 2.2
                    ok = (px >= 0) & (px < W - 1) & (py >= 0) & (py < H - 1)
                    xi, yi = px[ok].astype(int), py[ok].astype(int)
                    fx, fy = (px[ok] - xi)[:, None], (py[ok] - yi)[:, None]
                    v = (inten[ok, None] * c).astype(F)
                    np.add.at(img, (yi, xi), v * (1 - fx) * (1 - fy))
                    np.add.at(img, (yi, xi + 1), v * fx * (1 - fy))
                    np.add.at(img, (yi + 1, xi), v * (1 - fx) * fy)
                    np.add.at(img, (yi + 1, xi + 1), v * fx * fy)
            sig = 1.6
            yy, xx = np.mgrid[-10:11, -10:11]
            ker = np.exp(-((xx + int(hx) - hx) ** 2 + (yy + int(hy) - hy) ** 2) / (2 * sig * sig))
            y0, x0 = int(hy) - 10, int(hx) - 10
            if 0 <= y0 and y0 + 21 <= H and 0 <= x0 and x0 + 21 <= W:
                img[y0:y0 + 21, x0:x0 + 21] += ker[..., None].astype(F) * c * 9.0
        return img * atten[..., None]

    # ------------------------------------------------------------------ bodies
    def planet_and_rings(self, img):
        W, H, R, cx, cy = self.W, self.H, self.R, self.cx, self.cy
        L, N = self.L.astype(F), self.N.astype(F)
        ext = int(self.r_out * R) + 4
        x0, x1 = max(0, int(cx - ext)), min(W, int(cx + ext))
        y0, y1 = max(0, int(cy - ext)), min(H, int(cy + ext))
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(F)
        x = (xs + 0.5 - cx) / R
        y = -(ys + 0.5 - cy) / R
        r2 = x * x + y * y
        r = np.sqrt(r2)
        out = img[y0:y1, x0:x1].copy()

        # atmosphere halo outside the limb (lit side brighter)
        side = np.clip((x * L[0] + y * L[1]) / np.maximum(r, 1e-6) / math.hypot(L[0], L[1]), -1, 1)
        lit_side = smoothstep(-0.6, 0.9, side)
        halo = (np.exp(-np.maximum(r - 1, 0) / 0.008) * 0.8 +
                np.exp(-np.maximum(r - 1, 0) / 0.07) * 0.12) * lit_side * (r >= 1)
        atm = np.array([0.30, 0.68, 1.00], F)
        out += halo[..., None] * atm

        # planet surface
        cov = np.clip((1 - r) * R + 0.5, 0, 1)
        inside = cov > 0
        zs = np.sqrt(np.clip(1 - r2, 0, 1))
        nx, ny, nz = x[inside], y[inside], zs[inside]
        ndl = nx * L[0] + ny * L[1] + nz * L[2]
        mu = nz
        alt = nx * N[0] + ny * N[1] + nz * N[2]                 # sin(latitude)
        n = self.noise
        lat = np.arcsin(np.clip(alt, -1, 1))
        # noise domain stretched along latitude -> zonal (east-west) flow
        s = 1.9
        qx, qy, qz = nx * s + N[0] * alt * 7, ny * s + N[1] * alt * 7, nz * s + N[2] * alt * 7
        warp = n.fbm(qx, qy, qz, 6, gain=0.55)
        turb = n.fbm(qx * 3.1 + warp, qy * 3.1 - warp, qz * 3.1, 7, gain=0.58)
        bands = lat * 6.3 + warp * 0.9 + turb * 0.35
        a = np.array([0.050, 0.170, 0.420], F); b = np.array([0.035, 0.090, 0.150], F)
        d = np.array([0.00, 0.05, 0.11], F)
        alb = a + b * np.cos(2 * np.pi * (bands[:, None] * 0.5 + d))
        # high bright cloud streaks and a darker storm band
        streak = smoothstep(0.18, 0.55, n.fbm(qx * 1.7 + 3, qy * 1.7, qz * 1.7 - 1, 6) + turb * 0.4)
        alb = mix(alb, np.array([0.55, 0.78, 0.92], F), (streak * 0.32)[:, None])
        alb *= (0.88 + 0.24 * (turb * 0.5 + 0.5))[:, None]
        polar = smoothstep(0.70, 0.97, np.abs(alt))
        alb = mix(alb, np.array([0.22, 0.45, 0.66], F), (polar * 0.45)[:, None])
        # ring shadow on the planet
        ndl_r = nx * N[0] + ny * N[1] + nz * N[2]
        LN = float(L @ N)
        t = -ndl_r / LN
        qx2, qy2, qz2 = nx + t * L[0], ny + t * L[1], nz + t * L[2]
        rho = np.sqrt(qx2 * qx2 + qy2 * qy2 + qz2 * qz2)
        rd, _ = self.ring_at(rho)
        trans = np.where(t > 0, 1 - 0.88 * rd, 1.0).astype(F)
        # soft terminator (atmospheric scattering wraps light slightly)
        diffuse = smoothstep(-0.10, 0.35, ndl) * np.clip(ndl * 0.75 + 0.25, 0, 1) * trans
        limb = 0.35 + 0.65 * mu ** 0.45
        sun = 1.75
        # aerial haze: the atmosphere veils detail towards the limb
        haze = ((1 - mu) ** 1.8 * 0.65)[:, None]
        alb = mix(alb, np.array([0.30, 0.55, 0.80], F), haze)
        col = alb * (diffuse * limb * sun)[:, None]
        rim = (1 - mu) ** 3.2 * smoothstep(-0.15, 0.6, ndl) * 1.1
        col += atm * rim[:, None]
        col += alb * 0.006                                        # ring-shine on night side
        planet = np.zeros_like(out)
        planet[inside] = col
        out = mix(out, planet, cov[..., None])

        # rings (depth-sorted against the planet)
        zr = -(N[0] * x + N[1] * y) / N[2]
        rho = np.sqrt(r2 + zr * zr)
        dens, tint, rb = self.ring_at(rho, with_brightness=True)
        in_front = (r >= 1) | (zr > zs)
        # optical depth along the slanted line of sight
        tau = dens * 1.15 / abs(N[2]) * 0.35
        alpha = (1 - np.exp(-tau)) * in_front
        # soft edge where the ring passes behind the limb
        alpha *= np.where(r < 1, smoothstep(0.0, 2.0 / R, zr - zs), 1.0)
        b_ = x * L[0] + y * L[1] + zr * L[2]
        c_ = rho * rho - 1
        disc = b_ * b_ - c_
        shadow = smoothstep(-0.004, 0.004, disc) * (-b_ + np.sqrt(np.maximum(disc, 0)) > 0)
        light = (0.10 + 0.62 * abs(LN)) * (1 - 0.97 * shadow)
        ice = mix(np.array([0.50, 0.56, 0.62], F), np.array([0.80, 0.86, 0.92], F), tint[..., None])
        ice = mix(ice, np.array([0.48, 0.66, 0.84], F), (1 - smoothstep(1.4, 1.9, rho))[..., None] * 0.45)
        ring_col = ice * (light * rb)[..., None]
        out = mix(out, ring_col, alpha[..., None])
        img[y0:y1, x0:x1] = out

    def moon_body(self, img):
        mx, my, mr = self.moon
        L = self.L.astype(F)
        e = int(mr * 1.6) + 3
        x0, x1 = max(0, int(mx - e)), min(self.W, int(mx + e))
        y0, y1 = max(0, int(my - e)), min(self.H, int(my + e))
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(F)
        x = (xs + 0.5 - mx) / mr; y = -(ys + 0.5 - my) / mr
        r2 = x * x + y * y; r = np.sqrt(r2)
        out = img[y0:y1, x0:x1].copy()
        side = np.clip((x * L[0] + y * L[1]) / np.maximum(r, 1e-6) / math.hypot(L[0], L[1]), -1, 1)
        out += (np.exp(-np.maximum(r - 1, 0) / 0.05) * 0.5 * smoothstep(-0.5, 1, side)
                * (r >= 1))[..., None] * np.array([0.30, 0.80, 1.00], F)
        cov = np.clip((1 - r) * mr + 0.5, 0, 1)
        z = np.sqrt(np.clip(1 - r2, 0, 1))
        ndl = x * L[0] + y * L[1] + z * L[2]
        n = self.noise2
        tex = n.fbm(x * 3 + 4, y * 3, z * 3, 6) * 0.5 + 0.5
        craters = smoothstep(0.55, 0.9, n.fbm(x * 7, y * 7 + 2, z * 7, 4, ridged=True))
        alb = (0.55 + 0.35 * tex - 0.12 * craters)[..., None] * np.array([0.62, 0.90, 1.00], F)
        lit = np.clip((ndl + 0.02) / 1.02, 0, 1) ** 1.1
        col = alb * (lit * 2.6)[..., None] + np.array([0.2, 0.55, 0.7], F) * ((1 - z) ** 3 * 0.6)[..., None]
        out = mix(out, col.astype(F), cov[..., None])
        img[y0:y1, x0:x1] = out

    # ------------------------------------------------------------------ output
    def render(self, exposure=1.0):
        img = self.background()
        self.planet_and_rings(img)
        self.moon_body(img)
        # bloom at quarter resolution
        h4, w4 = self.H // 4, self.W // 4
        small = img[:h4 * 4, :w4 * 4].reshape(h4, 4, w4, 4, 3).mean(axis=(1, 3))
        lum = small.max(axis=2)
        bright = small * smoothstep(0.9, 4.0, lum)[..., None]
        bloom = gauss_blur(bright, 2.0) * 0.16 + gauss_blur(bright, 8.0) * 0.10 + gauss_blur(bright, 24.0) * 0.07
        img = img + resize(bloom, self.W, self.H)
        # vignette, tone map, encode
        ys, xs = np.mgrid[0:self.H, 0:self.W].astype(F)
        v = ((xs / self.W - 0.5) ** 2 + (ys / self.H - 0.5) ** 2) / 0.5
        img *= (1 - 0.32 * v ** 1.1)[..., None]
        out = srgb(aces(img * exposure)) * 255
        out += np.random.default_rng(self.seed + 9).normal(0, 0.9, out.shape)  # grain / dither
        return Image.fromarray(np.clip(np.round(out), 0, 255).astype(np.uint8))


def save_jpeg(im, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG", quality=95, subsampling=0, optimize=True)
    print(f"wrote {path.relative_to(ROOT)} {im.size[0]}x{im.size[1]}")


def wallpaper():
    W, H = 3840, 2400
    R = 520
    s = Scene(W, H, cx=2520, cy=1290, R=R, moon=(3420, 470, 62))
    im = s.render(exposure=1.0)
    d = ROOT / "config/includes.chroot/usr/share/wallpapers/Orvanta/contents/images"
    save_jpeg(im, d / "3840x2400.jpg")
    save_jpeg(im.crop((0, 120, 3840, 2280)), d / "3840x2160.jpg")


SPLASH_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!-- ORVANTA GRUB background. Generated by scripts/render-artwork.py: the
     photorealistic background is embedded as a JPEG; the logo and text are
     vector. live-build fills the @...@ fields and renders it to
     boot/grub/splash.png (800x600). The menu is drawn over the lower half
     (live-theme/theme.txt), so the artwork keeps that area dark.
     SPDX-License-Identifier: MIT -->
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     width="640" height="480" viewBox="0 0 640 480">
  <defs>
    <linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#5ee7f5"/>
      <stop offset="1" stop-color="#1f8fd6"/>
    </linearGradient>
  </defs>
  <image x="0" y="0" width="640" height="480" preserveAspectRatio="none"
         xlink:href="data:image/jpeg;base64,{b64}"/>
  <g transform="translate(320 92)">
    <ellipse rx="66" ry="25" fill="none" stroke="#2bb5c8" stroke-opacity="0.45"
             stroke-width="4" transform="rotate(-28)"/>
    <circle r="39" fill="none" stroke="url(#ring)" stroke-width="15"/>
    <circle cx="51" cy="-27" r="8.5" fill="#5ee7f5"/>
  </g>
  <text x="320" y="182" text-anchor="middle" font-family="DejaVu Sans" font-weight="bold"
        font-size="38" letter-spacing="9" fill="#ffffff">ORVANTA</text>
  <text x="320" y="208" text-anchor="middle" font-family="DejaVu Sans" font-size="13"
        letter-spacing="3" fill="#8fb4d9">OS @VERSION@ · LIVE · DEBIAN 13 BASE</text>
  <rect x="200" y="226" width="240" height="1" fill="#2bb5c8" fill-opacity="0.5"/>
</svg>
"""


def splash():
    W, H = 1600, 1200                       # rendered at 2x, stored at 800x600
    s = Scene(W, H, cx=1540, cy=165, R=165, moon=(250, 150, 20), seed=11)
    im = s.render(exposure=0.95)
    a = np.asarray(im, F)
    ys = np.mgrid[0:H, 0:W][0].astype(F) / H
    # keep the logo area calm and the menu area (lower half) dark for legibility
    shade = 1 - 0.62 * smoothstep(0.38, 0.6, ys)
    a = a * shade[..., None]
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize((800, 600), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95, subsampling=0, optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    path = ROOT / "config/bootloaders/grub-pc/splash.svg"
    path.write_text(SPLASH_TEMPLATE.replace("{b64}", b64))
    print(f"wrote {path.relative_to(ROOT)} (background {len(buf.getvalue())} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["wallpaper", "splash"])
    args = ap.parse_args()
    if args.only in (None, "wallpaper"):
        wallpaper()
    if args.only in (None, "splash"):
        splash()
