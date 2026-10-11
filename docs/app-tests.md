# Eight-app creative workflow tests

Live tests on macOS, 2026-10-11, using ArtCraft Bridge 0.3.0. The 0.4.0 duplicate-launch safeguard was tested separately after these creative runs. These are representative workflows, not exhaustive feature coverage. The native projects were saved and reopened locally; public evidence contains selected previews, path-free reports and two short videos.

| App | Version | Tested operation and verification | Record |
| --- | --- | --- | --- |
| DesignCraft | 0.6.0 | A3 poster, 19 objects, eight editable text stories, zero overset; native save/reopen, PDF export, trim/bleed/font checks | [JSON](evidence/designcraft.json) |
| PhotoCraft | 0.7.0 | 1600 × 2000 collage, 18 layers, perspective transform and editable polygon mask; reopened layer structure and byte-identical PNG | [JSON](evidence/photocraft.json) |
| VectorCraft | 0.9.0 | SVG import, native ellipse and fill edit, 11 objects; save/reopen and PNG/SVG/PDF export | [JSON](evidence/vectorcraft.json) |
| LightCraft | 0.6.0 | Persistent library, photo import, exposure/color adjustments, PNG/JPEG export; restart retained identical develop settings | [JSON](evidence/lightcraft.json) |
| FilmCraft | 0.6.0 | Native graphics sequence with two dissolves; save/reopen, H.264 export and decode all 96 frames | [JSON](evidence/filmcraft.json) |
| EffectCraft | 0.8.0 | Native composition with three position keys; save/reopen, H.264 export and 96 distinct decoded frames | [JSON](evidence/effectcraft.json) |
| CADCraft | 0.5.0 | Profile → bridge convex extrusion → CADCraft DXF roundtrip → STL; independent watertightness, winding, dimensions and volume checks | [JSON](evidence/cadcraft.json) |
| PdfCraft | 0.6.0 | Open copied print PDF, rotate 90°, save/reopen, restore orientation and save; text retained, native screenshot, empty test session stopped | [JSON](evidence/pdfcraft.json) |

## Example operations

These are excerpts of the exercised command families, rather than complete recreations of the pictured artwork. Query the installed app catalog first. Configure one workspace and state directory, then reuse them. Each snippet assumes its app has already been started through `bridge.start(APP)` and creates or modifies a disposable test document.

```python
from pathlib import Path
from artcraft_bridge import bridge

workspace = Path('./creative-demo').resolve()
bridge.configure(workspace=workspace)

def execute(app, command, **params):
    return bridge.call(app, 'engine.execute', {'command': command, 'params': params})
```

### DesignCraft — print layout

```python
execute('designcraft', 'file.new', preset='A3', title='FORM / AFTER HOURS')
execute('designcraft', 'frame.create', rect=[48, 88, 794, 280],
        content='text', text='FORM')
bridge.call('designcraft', 'document.inspect')
bridge.call('designcraft', 'app.save', {'path': str(workspace/'outputs/poster.designcraft')})
execute('designcraft', 'file.exportPdf',
        path=str(workspace/'outputs/poster.pdf'), standard='x4', bleed=True,
        marks={'crop': True, 'bleed': True})
```

The live poster additionally configured native CMYK swatches, typography and 3 mm bleed. A3 TrimBox/BleedBox, three embedded fonts and an output intent were checked independently. PDF/X-4 was requested; formal PDF/X conformance validation was not run.

### PhotoCraft — layered photo editing

```python
execute('photocraft', 'shape.create', kind='ellipse',
        rect=[85, 520, 880, 880], fill='#ff612d', name='Tangerine sun')
execute('photocraft', 'type.create', text='AFTER HOURS',
        x=80, y=200, font='Inter', size=120, color='#1843e9')
execute('photocraft', 'select.lasso', points=[[480,440],[1470,330],[1460,1530],[750,1630]])
execute('photocraft', 'layer.layerMask.revealSelection')
execute('photocraft', 'select.deselect')
```

These editing calls assume an existing canvas/photo layer. Resolve target layer IDs from inspection before transforms or masking. The pictured collage used an original ImageGen architectural source, with the actual composition performed in PhotoCraft. Native `.pcraft` retains layers; PNG flattens them. The screen collage is 72 PPI, separate from the DesignCraft print design.

### VectorCraft — vectors and export

The live sequence used `app.open` to import a workspace SVG, `paint.setFill` to change a native shape's color, `app.save` for the native document and `app.export` for PNG/SVG/PDF. Default background saves can return before a file exists: wait for the document to become clean and background jobs to finish before reopening.

### LightCraft — persistent library and grading

```python
execute('lightcraft', 'app.openLibrary', path=str(workspace/'outputs/library'))
execute('lightcraft', 'library.import', paths=[str(workspace/'source.png')],
        mode='copy', destination=str(workspace/'outputs/sources'))
# Resolve imported IDs from the result; the live test's photo ID was 1.
execute('lightcraft', 'library.select', ids=[1], active=1)
execute('lightcraft', 'develop.set', values={
    'light.exposure': -0.15, 'light.contrast': 12,
    'light.highlights': -20, 'light.shadows': 12, 'color.vibrance': 15})
execute('lightcraft', 'app.export', path=str(workspace/'outputs/graded.jpg'), format='jpeg')
```

The bridge starts LightCraft in memory mode; `app.openLibrary` switches to the persistent library. After quitting and restarting, reopen that library before checking `develop.get`.

### FilmCraft — sequence graphics

```python
execute('filmcraft', 'file.newProject', name='FORM / AFTER HOURS')
execute('filmcraft', 'file.newSequence', name='FORM / AFTER HOURS',
        width=1280, height=720, fps=24, video=3, audio=1)
execute('filmcraft', 'graphics.newText', text='FORM', position=[100,340],
        size=190, seconds=4, track=1, time=0)
execute('filmcraft', 'graphics.set', props={'fill_color':'#CEFF48','font_style':'Bold'})
```

[Actual exported FilmCraft video](media/filmcraft-after-hours.mp4): 1280 × 720, H.264, 24 fps, four seconds. Two native dissolves produced temporal changes; 24 unique decoded frames. No audio or long-form footage edit was tested.

### EffectCraft — keyframed motion

```python
execute('effectcraft', 'comp.new', name='FORM / AFTER HOURS', width=1280,
        height=720, frameRate=24, duration=4, background='#2347FF')
execute('effectcraft', 'layer.newShape', kind='ellipse', name='ORBIT',
        size=[170,170], position=[1040,340], fill='#FF7648')
for time, position in [(0,[930,160]), (2,[1080,550]), (4,[930,160])]:
    execute('effectcraft', 'prop.addKey', path='Transform.Position',
            time=time, value=position)
```

[Actual exported EffectCraft video](media/effectcraft-after-hours.mp4): the same dimensions/duration, with 96 distinct decoded frames. No audio.

### CADCraft — closed mesh and rocket

Run [the convex block example](../examples/cadcraft_solid.py) or [the rocket example](../examples/cadcraft_rocket.py). The latter constructs a nonconvex radial boundary, imports 2,560 triangular faces, saves/reopens them in CADCraft and writes STL from the readback. It is a separate example; the general `cad-export-stl` command still accepts convex meshes only.

### PdfCraft — PDF persistence

```python
bridge.call('pdfcraft', 'ui.open', {'path': str(workspace/'outputs/copied-print.pdf')})
bridge.call('pdfcraft', 'ui.command', {'id': 'page.rotate'})
bridge.call('pdfcraft', 'ui.command', {'id': 'file.save'})
bridge.call('pdfcraft', 'ui.command', {'id': 'file.close'})
```

Start with explicit `portable_copy=True`. The test reopened the file, verified rotation/text, then used `page.rotate_ccw` and saved the restored orientation. UI screenshots require a visible foreground window. The private portable bundle was removed after stopping the empty owned session; normal `stop` itself retains profiles and copies.

## Evidence boundaries

PNG integrity was checked with Pillow. Independent media inspection used ffprobe/ffmpeg; geometry verification used trimesh. These are optional verification tools, not bridge runtime dependencies. Native editable projects, app binaries, runtime profiles, tokens, logs and raw path-bearing inspection replies are not distributed here. The checked public previews are original test artwork; licensing/provenance is described in [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md).
