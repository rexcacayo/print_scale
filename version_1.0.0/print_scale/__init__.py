bl_info = {'name': 'Print Scale', 'author': 'Ricardo Lugaresi', 'version': (1, 0, 0),
           'blender': (4, 2, 0), 'location': 'Vista 3D > N > Print Scale',
           'description': 'Elige el tamaño de impresión y ve qué zonas dejan de salir con tu boquilla',
           'category': 'Object'}
import bpy
from . import common, overlay, scaling

MODES = [('Z', 'Alto', 'Altura final (eje Z)'), ('MAX', 'Lado mayor', 'La medida más grande del modelo'),
         ('X', 'Largo X', 'Medida en X'), ('Y', 'Fondo Y', 'Medida en Y'),
         ('PCT', 'Porcentaje', 'Escala en %'), ('RATIO', 'Escala 1:N', 'Escala de modelismo a partir del tamaño real'),
         ('FIT', 'Que quepa', 'Lo más grande que quepa en tu impresora')]


def _printers(self, context):
    return [(k, v[0], f'{v[1][0]} × {v[1][1]} × {v[1][2]} mm') for k, v in scaling.PRINTERS.items()] + \
        [('CUSTOM', 'Personalizada', 'Escribe tú las medidas de la cama')]


def _stale(self, context):
    p = context.scene.print_scale_props
    p.checked = False
    overlay.clear()


class PrintScaleProps(bpy.types.PropertyGroup):
    model_unit: bpy.props.EnumProperty(name='Unidades', items=common.UNIT_ITEMS, default='AUTO', update=_stale)
    mode: bpy.props.EnumProperty(name='Cómo', items=MODES, default='Z', update=_stale)
    target_mm: bpy.props.FloatProperty(name='Medida (mm)', default=100, min=1, max=2000, precision=1, update=_stale)
    percent: bpy.props.FloatProperty(name='Porcentaje', default=100, min=1, max=5000, precision=1, subtype='PERCENTAGE', update=_stale)
    real_mm: bpy.props.FloatProperty(name='Tamaño real (mm)', description='Medida real del objeto en su lado mayor (p. ej. un coche de 4 m = 4000)', default=4000, min=1, max=1e6, update=_stale)
    ratio: bpy.props.EnumProperty(name='Escala', items=scaling.RATIOS, default='12', update=_stale)
    printer: bpy.props.EnumProperty(name='Impresora', items=_printers, update=_stale)
    bed_x: bpy.props.FloatProperty(name='X', default=220, min=10, update=_stale)
    bed_y: bpy.props.FloatProperty(name='Y', default=220, min=10, update=_stale)
    bed_z: bpy.props.FloatProperty(name='Z', default=220, min=10, update=_stale)
    margin: bpy.props.FloatProperty(name='Margen (mm)', default=5, min=0, max=50, update=_stale)
    nozzle: bpy.props.EnumProperty(name='Boquilla', items=[('0.2', '0.2', ''), ('0.25', '0.25', ''), ('0.4', '0.4', ''), ('0.6', '0.6', ''), ('0.8', '0.8', '')], default='0.4', update=_stale)
    checked: bpy.props.BoolProperty(default=False)
    r_factor: bpy.props.FloatProperty()
    r_new: bpy.props.FloatVectorProperty(size=3)
    r_red: bpy.props.FloatProperty()
    r_amber: bpy.props.FloatProperty()
    r_fits: bpy.props.BoolProperty()
    r_model: bpy.props.StringProperty()
    done: bpy.props.StringProperty()


def _model(context):
    try:
        return common.pick_model(context)
    except common.AddonError:
        return None


class OBJECT_OT_print_scale_check(bpy.types.Operator):
    """Calcula el tamaño nuevo y marca en el modelo lo que quedaría demasiado fino"""
    bl_idname = 'object.print_scale_check'; bl_label = 'Comprobar'; bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return common.poll_object_mode(cls, context)

    def execute(self, context):
        p = context.scene.print_scale_props
        try:
            obj = common.pick_model(context)
            r = scaling.check(context, obj, p)
        except common.AddonError as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}
        p.r_factor = r['factor']; p.r_new = r['new']; p.r_red = r['red_share']; p.r_amber = r['amber_share']
        p.r_fits = r['fits']; p.r_model = obj.name; p.checked = True; p.done = ''
        overlay.show(r['red_pts'], r['amber_pts'])
        self.report({'INFO'}, f"{r['new'][0]:.0f} × {r['new'][1]:.0f} × {r['new'][2]:.0f} mm")
        return {'FINISHED'}


class OBJECT_OT_print_scale_apply(bpy.types.Operator):
    """Crea una copia al tamaño elegido; el original queda oculto"""
    bl_idname = 'object.print_scale_apply'; bl_label = 'Aplicar tamaño'; bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return common.poll_object_mode(cls, context)

    def execute(self, context):
        p = context.scene.print_scale_props
        try:
            obj = common.pick_model(context)
            out, f, dims = scaling.apply(context, obj, p)
        except common.AddonError as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}
        overlay.clear(); p.checked = False
        p.done = f'{out.name}: {dims[0]:.1f} × {dims[1]:.1f} × {dims[2]:.1f} mm (×{f:.3f})'
        self.report({'INFO'}, p.done)
        return {'FINISHED'}


class OBJECT_OT_print_scale_clear(bpy.types.Operator):
    """Quita los puntos de colores del modelo"""
    bl_idname = 'object.print_scale_clear'; bl_label = 'Quitar marcas'

    def execute(self, context):
        overlay.clear(); context.scene.print_scale_props.checked = False
        return {'FINISHED'}


class VIEW3D_PT_print_scale(bpy.types.Panel):
    bl_label = 'Print Scale'; bl_idname = 'VIEW3D_PT_print_scale'; bl_space_type = 'VIEW_3D'; bl_region_type = 'UI'; bl_category = 'Print Scale'

    def draw(self, context):
        layout = self.layout; p = context.scene.print_scale_props
        if common.draw_mode_warning(layout, context):
            return
        model = _model(context)
        box = layout.box()
        box.label(text='1 · Modelo', icon='MESH_DATA')
        if model is None:
            r = box.row(); r.alert = True; r.label(text='Selecciona el modelo', icon='ERROR')
        else:
            code, mm = common.resolve_unit(context.scene, p.model_unit, model)
            d = [x * mm for x in model.dimensions]
            box.label(text=model.name, icon='OBJECT_DATA')
            box.label(text=f'Ahora: {d[0]:.1f} × {d[1]:.1f} × {d[2]:.1f} mm')
            box.prop(p, 'model_unit')

        box = layout.box()
        box.label(text='2 · Tamaño a imprimir', icon='FULLSCREEN_ENTER')
        box.prop(p, 'mode')
        if p.mode in {'Z', 'X', 'Y', 'MAX'}:
            box.prop(p, 'target_mm')
        elif p.mode == 'PCT':
            box.prop(p, 'percent')
        elif p.mode == 'RATIO':
            box.prop(p, 'real_mm'); box.prop(p, 'ratio')
        box.prop(p, 'printer')
        if p.printer == 'CUSTOM':
            r = box.row(align=True); r.prop(p, 'bed_x'); r.prop(p, 'bed_y'); r.prop(p, 'bed_z')
        box.prop(p, 'margin')
        r = box.row(align=True); r.label(text='Boquilla'); r.prop(p, 'nozzle', expand=True)
        col = box.column(); col.scale_y = 1.4
        col.operator('object.print_scale_check', icon='VIEWZOOM')

        if p.checked and model is not None and model.name == p.r_model:
            box = layout.box()
            n = p.r_new
            box.label(text=f'{n[0]:.1f} × {n[1]:.1f} × {n[2]:.1f} mm  (×{p.r_factor:.3f})', icon='CHECKMARK')
            r = box.row(); r.alert = not p.r_fits
            r.label(text='Cabe en la impresora' if p.r_fits else 'No cabe: pártelo con BigPrint',
                    icon='CHECKMARK' if p.r_fits else 'ERROR')
            r = box.row(); r.alert = p.r_red > 0.005
            r.label(text=f'Desaparece (< {float(p.nozzle):g} mm): {p.r_red * 100:.1f} %', icon='CANCEL' if p.r_red > 0.005 else 'CHECKMARK')
            box.label(text=f'Frágil (< {2 * float(p.nozzle):g} mm): {p.r_amber * 100:.1f} %', icon='ERROR' if p.r_amber > 0.01 else 'CHECKMARK')
            if p.r_red > 0.005 or p.r_amber > 0.01:
                t = box.column(align=True); t.scale_y = .8
                t.label(text='Rojo y ámbar marcados en el modelo.')
                t.label(text='Engrósalo con Thicken o elige más tamaño.')
            r = box.row(align=True)
            r.operator('object.print_scale_clear', icon='X')
            col = box.column(); col.scale_y = 1.4
            col.operator('object.print_scale_apply', icon='CHECKMARK')
        if p.done:
            layout.label(text=p.done, icon='CHECKMARK')


classes = (PrintScaleProps, OBJECT_OT_print_scale_check, OBJECT_OT_print_scale_apply, OBJECT_OT_print_scale_clear, VIEW3D_PT_print_scale)


def register():
    common.register_classes(classes, 'print_scale_props', PrintScaleProps)
    overlay.register()


def unregister():
    overlay.unregister()
    common.unregister_classes(classes, 'print_scale_props')
