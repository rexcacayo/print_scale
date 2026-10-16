# SPDX-FileCopyrightText: 2026 Ricardo Lugaresi
# SPDX-License-Identifier: GPL-3.0-or-later

"""Print Scale: elegir el tamaño de impresión y ver qué deja de salir con tu boquilla."""
import bpy
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


def _origin_chain(obj):
    """Original del que sale una copia (Mesh Doctor, Print Ready… guardan «taller_origen»)."""
    seen = set()
    while obj is not None and obj.get('taller_origen') and obj.name not in seen:
        seen.add(obj.name)
        src = bpy.data.objects.get(obj['taller_origen'])
        if src is None:
            break
        obj = src
    return obj


def _root(obj):
    while obj.parent is not None:
        obj = obj.parent
    return obj


def _usable(obj):
    return (obj is not None and obj.type == 'MESH' and not common.is_helper(obj) and not obj.get('showcase')
            and obj.visible_get())


def group(context, whole=True):
    """Piezas que se escalan juntas. Con varias seleccionadas: esas. Con una sola y «toda la
    figura»: todas las piezas de su familia (las de un 3MF importado cuelgan del mismo vacío),
    también las copias reparadas que ya no cuelgan de él."""
    sel = [o for o in [context.active_object] + list(context.selected_objects) if _usable(o)]
    sel = list(dict.fromkeys(sel))
    if not sel:
        obj = common.pick_model(context)       # da el mensaje de error de siempre
        sel = [obj]
    if len(sel) > 1 or not whole:
        return sel
    root = _root(_origin_chain(sel[0]))
    family = {root.name} | {c.name for c in root.children_recursive}
    if len(family) == 1:
        return sel
    out = []
    for o in context.view_layer.objects:
        if _usable(o) and (o.name in family or _origin_chain(o).name in family):
            out.append(o)
    return out or sel


def _read_group(context, objs, mm):
    Vs, Fs, Ms, off = [], [], [], 0
    for o in objs:
        V, F, mat = meshio.read_arrays(context, o, mm)
        Vs.append(V); Fs.append(F + off); Ms.append(mat); off += len(V)
    if not off:
        raise common.AddonError('Las piezas no tienen caras.')
    return np.vstack(Vs), np.vstack(Fs), Ms


def check(context, objs, p):
    """Calcula el tamaño nuevo y las zonas que quedan demasiado finas. Devuelve un dict."""
    context.view_layer.update()
    code, mm = common.resolve_unit(context.scene, p.model_unit, objs[0])
    V, F, _mat = _read_group(context, objs, mm)
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


def apply(context, objs, p):
    """Crea copias escaladas (los originales quedan ocultos), todas con el mismo factor y desde
    el centro de la base del conjunto: las piezas siguen encajando entre sí."""
    context.view_layer.update()
    code, mm = common.resolve_unit(context.scene, p.model_unit, objs[0])
    data = [meshio.read_arrays(context, o, 1.0) for o in objs]      # unidades de Blender, mundo
    allV = np.vstack([d[0] for d in data])
    lo, hi = allV.min(0), allV.max(0)
    f = scale_factor(p, (hi - lo) * mm)
    pivot = np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])
    newdims = (hi - lo) * mm * f
    outs = []
    for o, (V, F, mat) in zip(objs, data):
        out = meshio.new_object_like(context, o, f'{o.name}_{newdims[2]:.0f}mm', pivot + (V - pivot) * f, F, mat)
        out[common.UNIT_PROP] = code
        out['taller_origen'] = o.name
        out['print_scale_factor'] = f
        outs.append(out)
    for o in objs:
        o.hide_set(True); o.hide_render = True
    for o in context.selected_objects:
        o.select_set(False)
    for o in outs:
        o.select_set(True)
    context.view_layer.objects.active = outs[0]
    return outs, f, newdims
