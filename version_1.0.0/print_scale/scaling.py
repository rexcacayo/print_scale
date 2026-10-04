"""Print Scale: elegir el tamaño de impresión y ver qué deja de salir con tu boquilla."""
import numpy as np

from . import common, meshio, meshops as mo

PRINTERS = {
    'AD5M': ('Flashforge AD5M / AD5M Pro', (220, 220, 220)),
    'A1': ('Bambu Lab A1 / P1 / X1', (256, 256, 256)),
    'A1MINI': ('Bambu Lab A1 mini', (180, 180, 180)),
    'MK4': ('Prusa MK4', (250, 210, 220)),
    'ENDER3': ('Creality Ender 3', (220, 220, 250)),
    'K1': ('Creality K1', (220, 220, 250)),
}
RATIOS = [('10', '1:10', ''), ('12', '1:12', ''), ('18', '1:18', ''), ('24', '1:24', ''),
          ('32', '1:32', ''), ('35', '1:35', ''), ('43', '1:43', ''), ('64', '1:64', ''), ('72', '1:72', '')]


def bed_size(p):
    if p.printer == 'CUSTOM':
        return (p.bed_x, p.bed_y, p.bed_z)
    return PRINTERS[p.printer][1]


def scale_factor(p, dims):
    """Factor de escala según el modo elegido. `dims` en mm (x, y, z)."""
    x, y, z = dims
    if p.mode == 'Z':
        return p.target_mm / max(z, 1e-9)
    if p.mode == 'X':
        return p.target_mm / max(x, 1e-9)
    if p.mode == 'Y':
        return p.target_mm / max(y, 1e-9)
    if p.mode == 'MAX':
        return p.target_mm / max(max(dims), 1e-9)
    if p.mode == 'PCT':
        return p.percent / 100.0
    if p.mode == 'RATIO':
        return (p.real_mm / float(p.ratio)) / max(max(dims), 1e-9)
    if p.mode == 'FIT':
        bed = sorted(b - 2 * p.margin for b in bed_size(p))
        d = sorted(dims)
        return min(b / max(v, 1e-9) for b, v in zip(bed, d))
    return 1.0


def fits(dims, bed, margin):
    d = sorted(dims)
    b = sorted(v - 2 * margin for v in bed)
    return all(a <= c + 1e-6 for a, c in zip(d, b))


def check(context, obj, p):
    """Calcula el tamaño nuevo y las zonas que quedan demasiado finas. Devuelve un dict."""
    code, mm = common.resolve_unit(context.scene, p.model_unit, obj)
    V, F, _mat = meshio.read_arrays(context, obj, mm)
    lo, hi = V.min(0), V.max(0)
    dims = hi - lo
    f = scale_factor(p, dims)
    new = dims * f
    nozzle = float(p.nozzle)
    min_wall = 2 * nozzle
    # grosor medido a tamaño actual; solo interesan los menores de la pared mínima escalada
    idx, t = mo.sample_thickness(V, F, max_dist=min_wall / f * 1.05)
    ts = t * f
    red = ts < nozzle
    amber = (ts >= nozzle) & (ts < min_wall)
    pts = V[idx] / mm
    return {
        'unit': code, 'mm': mm, 'factor': f, 'dims': dims, 'new': new,
        'red_share': float(red.mean()) if len(ts) else 0.0,
        'amber_share': float(amber.mean()) if len(ts) else 0.0,
        'red_pts': pts[red], 'amber_pts': pts[amber],
        'fits': fits(new, bed_size(p), p.margin),
        'nozzle': nozzle, 'min_wall': min_wall,
    }


def apply(context, obj, p):
    """Crea una copia escalada (el original queda oculto). Escala desde el centro de la base."""
    code, mm = common.resolve_unit(context.scene, p.model_unit, obj)
    V, F, mat = meshio.read_arrays(context, obj, 1.0)        # unidades de Blender, mundo
    lo, hi = V.min(0), V.max(0)
    f = scale_factor(p, (hi - lo) * mm)
    pivot = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    V2 = pivot + (V - pivot) * f
    newdims = (hi - lo) * mm * f
    name = f'{obj.name}_{newdims[2]:.0f}mm'
    out = meshio.new_object_like(context, obj, name, V2, F, mat)
    out[common.UNIT_PROP] = code
    out['taller_origen'] = obj.name
    out['print_scale_factor'] = f
    obj.hide_set(True); obj.hide_render = True
    meshio.select_only(context, out)
    return out, f, newdims
