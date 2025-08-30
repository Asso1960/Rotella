# Fusion 360 Add-in: Detailed Caster Wheel
# Author: Jules
# Creates a detailed caster wheel based on user-provided dimensions.

import adsk.core, adsk.fusion, traceback, math

# User-provided dimensions (converted to cm for Fusion 360 API)
plate_len_x = 5.8
plate_len_y = 5.3
plate_thk = 0.2
hole_diam = 0.6
hole_spacing_x = 5.3
hole_spacing_y = 4.3
wheel_diam = 6.3
wheel_width = 2.4
total_height = 8.5
axle_diam = 0.6

# Assumed dimensions (in cm)
plate_corner_radius = 0.5 # 5mm corner radius

def run(context):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    try:
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox('Please switch to the Design workspace before running this add-in.')
            return

        # Create a new component for the caster wheel
        root = design.rootComponent
        occ = root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
        comp = occ.component
        comp.name = 'Detailed Caster Wheel'

        # Get collections for creating features
        sketches = comp.sketches
        extrudes = comp.features.extrudeFeatures
        fillets = comp.features.filletFeatures

        # --- Part 1: Top Plate ---
        # Create a sketch for the plate on the XY plane.
        plate_sketch = sketches.add(comp.xYConstructionPlane)

        # Draw the centered rectangle for the plate body.
        lines = plate_sketch.sketchCurves.sketchLines
        p1 = adsk.core.Point3D.create(-plate_len_x / 2, -plate_len_y / 2, 0)
        p2 = adsk.core.Point3D.create(plate_len_x / 2, plate_len_y / 2, 0)
        rect_lines = lines.addTwoPointRectangle(p1, p2)

        # Add fillets to the corners of the rectangle.
        if plate_corner_radius > 0:
            if plate_corner_radius > min(plate_len_x, plate_len_y) / 2:
                ui.messageBox("Warning: Corner radius is too large for the plate dimensions. Skipping fillets.")
            else:
                fillets_col = plate_sketch.sketchFillets
                # The rectangle lines are connected, so we can fillet adjacent lines.
                fillets_col.add(rect_lines.item(0), rect_lines.item(1), plate_corner_radius)
                fillets_col.add(rect_lines.item(1), rect_lines.item(2), plate_corner_radius)
                fillets_col.add(rect_lines.item(2), rect_lines.item(3), plate_corner_radius)
                fillets_col.add(rect_lines.item(3), rect_lines.item(0), plate_corner_radius)

        # Extrude the plate profile to create the body.
        plate_prof = plate_sketch.profiles.item(0)
        plate_body = extrudes.addSimple(plate_prof, adsk.core.ValueInput.createByReal(plate_thk), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        plate_body.name = "Top Plate"

        # Create a new sketch on the top face of the plate for the mounting holes.
        # Find the top face by checking the normal vector of each face.
        top_face = None
        for face in plate_body.faces:
            _, normal = face.evaluator.getNormalAtPoint(face.pointOnFace)
            if normal.isParallelTo(adsk.core.Vector3D.create(0, 0, 1)):
                top_face = face
                break

        if not top_face:
            raise RuntimeError("Could not find the top face of the plate to create holes.")

        holes_sketch = sketches.add(top_face)

        # Draw the four mounting holes.
        circles = holes_sketch.sketchCurves.sketchCircles
        hole_points = [
            adsk.core.Point3D.create(hole_spacing_x / 2, hole_spacing_y / 2, 0),
            adsk.core.Point3D.create(-hole_spacing_x / 2, hole_spacing_y / 2, 0),
            adsk.core.Point3D.create(hole_spacing_x / 2, -hole_spacing_y / 2, 0),
            adsk.core.Point3D.create(-hole_spacing_x / 2, -hole_spacing_y / 2, 0)
        ]
        for point in hole_points:
            circles.addByCenterRadius(point, hole_diam / 2)

        # Extrude-cut the holes through the plate.
        for prof in holes_sketch.profiles:
            extrudes.addSimple(prof, adsk.core.ValueInput.createByReal(-plate_thk * 2), adsk.fusion.FeatureOperations.CutFeatureOperation)

        # --- Part 2: Wheel ---
        # Calculate the Z position for the center of the wheel.
        # The total height is from the top of the plate (z=plate_thk) to the bottom of the wheel.
        z_bottom_wheel = plate_thk - total_height
        wheel_center_z = z_bottom_wheel + (wheel_diam / 2)

        # Create a sketch for the wheel profile on the YZ plane.
        wheel_sketch = sketches.add(comp.yZConstructionPlane)

        # Draw the outer circle for the wheel and the inner circle for the axle hole.
        circles = wheel_sketch.sketchCurves.sketchCircles
        wheel_center_point = adsk.core.Point3D.create(0, 0, wheel_center_z)

        circles.addByCenterRadius(wheel_center_point, wheel_diam / 2)
        circles.addByCenterRadius(wheel_center_point, axle_diam / 2)

        # Extrude the wheel profile symmetrically along the X-axis to create the wheel body.
        # The profile is the area between the two circles.
        wheel_prof = wheel_sketch.profiles.item(0)

        extrude_input = extrudes.createInput(wheel_prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)

        # For symmetric extrusion, the distance is the extent on one side.
        distance = adsk.core.ValueInput.createByReal(wheel_width / 2)
        extrude_input.setDistanceExtent(True, distance)

        # Execute the extrude feature.
        wheel_feature = extrudes.add(extrude_input)
        wheel_body = wheel_feature.bodies.item(0)
        wheel_body.name = "Wheel"

        # --- Part 3: Fork and Swivel (Simplified Geometry) ---
        # NOTE: The fork geometry is simplified to be robustly generated from parameters.
        # It consists of a top cylinder, two rectangular arms, and a swivel pin.

        # Define assumed parameters for the fork
        fork_arm_width = 1.0  # Width of the rectangular arms
        fork_clearance = 0.1  # Gap between wheel and fork arm
        fork_top_plate_diam = 4.5
        fork_top_plate_thk = 0.6
        swivel_pin_diam = 2.5
        swivel_pin_height = plate_thk # Pin will be flush with top plate

        # Create the fork's top plate (a cylinder)
        fork_top_sketch = sketches.add(comp.xYConstructionPlane)
        fork_top_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), fork_top_plate_diam / 2)
        fork_top_prof = fork_top_sketch.profiles.item(0)

        # Extrude it down to form the main part of the fork's top. This will be the main body for the fork.
        fork_body = extrudes.addSimple(fork_top_prof, adsk.core.ValueInput.createByReal(-fork_top_plate_thk), adsk.fusion.FeatureOperations.NewBodyFeatureOperation).bodies.item(0)
        fork_body.name = "Fork"

        # Create one fork arm as a rectangular block and then mirror it.
        arm_x_position = (wheel_width / 2) + fork_clearance
        arm_z_top = -fork_top_plate_thk
        arm_z_bottom = wheel_center_z - (axle_diam / 2) - 0.2 # A bit of material below the axle hole

        # Create a construction plane for the arm sketch, on the inner side of the arm
        plane_input = comp.constructionPlanes.createInput()
        offset = adsk.core.ValueInput.createByReal(arm_x_position)
        plane_input.setByOffset(comp.yZConstructionPlane, offset)
        arm_plane = comp.constructionPlanes.add(plane_input)
        arm_sketch = sketches.add(arm_plane)

        # Sketch a rectangle for the arm's side profile
        arm_sketch.sketchCurves.sketchLines.addTwoPointRectangle(
            adsk.core.Point2D.create(-fork_top_plate_diam / 2, arm_z_top),
            adsk.core.Point2D.create(fork_top_plate_diam / 2, arm_z_bottom)
        )
        arm_prof = arm_sketch.profiles.item(0)

        # Extrude the arm and join it to the fork body.
        extrude_input = extrudes.createInput(arm_prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(fork_arm_width) # Extrude outward
        extrude_input.setDistanceExtent(False, distance)
        arm_feature = extrudes.add(extrude_input)

        # Mirror the arm feature to create the second arm
        mirror_features_collection = adsk.core.ObjectCollection.create()
        mirror_features_collection.add(arm_feature)
        mirror_input = comp.features.mirrorFeatures.createInput(mirror_features_collection, comp.yZConstructionPlane)
        comp.features.mirrorFeatures.add(mirror_input)

        # Create the axle hole through both arms
        axle_hole_sketch = sketches.add(comp.yZConstructionPlane)
        axle_hole_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, wheel_center_z), axle_diam / 2)
        axle_hole_prof = axle_hole_sketch.profiles.item(0)

        # Extrude cut symmetrically to ensure it goes through both arms
        cut_input = extrudes.createInput(axle_hole_prof, adsk.fusion.FeatureOperations.CutFeatureOperation)
        cut_distance = adsk.core.ValueInput.createByReal(arm_x_position + fork_arm_width)
        cut_input.setDistanceExtent(True, cut_distance)
        extrudes.add(cut_input)

        # Create the swivel pin and join it to the fork body
        swivel_sketch = sketches.add(comp.xYConstructionPlane)
        swivel_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0, 0, 0), swivel_pin_diam / 2)
        swivel_prof = swivel_sketch.profiles.item(swivel_sketch.profiles.count - 1)
        extrude_input = extrudes.createInput(swivel_prof, adsk.fusion.FeatureOperations.JoinFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(swivel_pin_height)
        extrude_input.setDistanceExtent(False, distance)
        extrudes.add(extrude_input)

        # Finally, create a hole in the top plate for the swivel pin
        hole_on_plate_sketch = sketches.add(top_face) # top_face is from Part 1
        hole_on_plate_sketch.sketchCurves.sketchCircles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), swivel_pin_diam/2 + 0.05) # with clearance
        hole_prof = hole_on_plate_sketch.profiles.item(0)
        extrudes.addSimple(hole_prof, adsk.core.ValueInput.createByReal(-plate_thk * 2), adsk.fusion.FeatureOperations.CutFeatureOperation)

        # --- Part 4: Wheel Axle ---
        # The axle is a simple cylinder that goes through the fork arms and the wheel.
        axle_length = 2 * ((wheel_width / 2) + fork_clearance + fork_arm_width)

        # Create a sketch on the YZ plane for the axle's circular profile.
        axle_sketch = sketches.add(comp.yZConstructionPlane)
        axle_sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(0, 0, wheel_center_z), axle_diam / 2
        )
        # Get the profile that was just created.
        axle_prof = axle_sketch.profiles.item(axle_sketch.profiles.count - 1)

        # Extrude it symmetrically to create the axle pin.
        extrude_input = extrudes.createInput(axle_prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
        distance = adsk.core.ValueInput.createByReal(axle_length / 2)
        extrude_input.setDistanceExtent(True, distance)
        axle_body = extrudes.add(extrude_input).bodies.item(0)
        axle_body.name = "Wheel Axle"

        ui.messageBox('Detailed caster wheel generated successfully!')

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def stop(context):
    app = adsk.core.Application.get()
    ui  = app.userInterface
    try:
        # Clean up UI elements if any
        ui.messageBox('Detailed Caster Wheel Add-in stopped.')
    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
