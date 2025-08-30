# Fusion 360 Add-in: Rotella da Carrello completa
# Generato da ChatGPT
# Parametri: ruota Ø63 × 24 mm, piastra 68 × 55 mm, fori 6 mm (interassi 59 × 40)

import adsk.core, adsk.fusion, traceback

def run(context):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Passa al workspace Design prima di eseguire questo add-in.')
            return

        root = design.rootComponent
        occs = root.occurrences
        occ = occs.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = 'Rotella da Carrello'

        # Parametri principali
        wheel_diam = 63.0
        wheel_width = 24.0
        axle_diam = 6.0
        plate_len = 68.0
        plate_wid = 55.0
        plate_thk = 3.0
        hole_diam = 6.0
        hole_spacing_x = 59.0
        hole_spacing_y = 40.0

        sketches = comp.sketches
        extrudes = comp.features.extrudeFeatures

        # --- Ruota ---
        sk_wheel = sketches.add(comp.xYConstructionPlane)
        sk_wheel.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), wheel_diam/2)
        prof = sk_wheel.profiles.item(0)
        wheel = extrudes.addSimple(prof, adsk.core.ValueInput.createByReal(wheel_width),
                                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        wheel.name = 'Ruota'

        # Foro asse
        sk_axle = sketches.add(comp.zXConstructionPlane)
        sk_axle.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), axle_diam/2)
        prof_axle = sk_axle.profiles.item(0)
        extrudes.addSimple(prof_axle, adsk.core.ValueInput.createByReal(wheel_width*2),
                           adsk.fusion.FeatureOperations.CutFeatureOperation)

        # --- Piastra superiore ---
        sk_plate = sketches.add(comp.xYConstructionPlane)
        lines = sk_plate.sketchCurves.sketchLines
        lines.addTwoPointRectangle(adsk.core.Point3D.create(-plate_len/2,-plate_wid/2,0),
                                   adsk.core.Point3D.create( plate_len/2, plate_wid/2,0))
        prof_plate = sk_plate.profiles.item(0)
        plate = extrudes.addSimple(prof_plate, adsk.core.ValueInput.createByReal(plate_thk),
                                   adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        plate.name = 'Piastra'

        # Fori piastra
        sk_holes = sketches.add(comp.xYConstructionPlane)
        for sx in (-1,1):
            for sy in (-1,1):
                sk_holes.sketchCurves.sketchCircles.addByCenterRadius(
                    adsk.core.Point3D.create(sx*hole_spacing_x/2, sy*hole_spacing_y/2, 0), hole_diam/2)
        for i in range(sk_holes.profiles.count):
            extrudes.addSimple(sk_holes.profiles.item(i), adsk.core.ValueInput.createByReal(plate_thk*2),
                               adsk.fusion.FeatureOperations.CutFeatureOperation)

        ui.messageBox('Rotella da carrello generata con successo!')

    except:
        if ui:
            ui.messageBox('Errore:\n{}'.format(traceback.format_exc()))

def stop(context):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    ui.messageBox('Add-in Rotella da Carrello disattivato.')
