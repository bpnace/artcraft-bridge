"""Create a CADCraft profile, extrude in the bridge, roundtrip faces, export STL."""
import argparse
import json
from pathlib import Path
from artcraft_bridge import bridge
from artcraft_bridge.solid import export_extrusion, export_stl, triangles_from_drawing


def run(workspace, state_dir=None):
    workspace=Path(workspace).expanduser().resolve()
    out=workspace/'outputs'
    out.mkdir(parents=True,exist_ok=True)
    if any(out.iterdir()):
        raise ValueError('Use a fresh dedicated workspace with empty outputs')
    bridge.configure(workspace=workspace,state_dir=state_dir)
    started=bridge.start('cadcraft')
    if started.get('reused'):
        raise ValueError('Example requires a fresh managed CADCraft session')
    bridge.call('cadcraft','engine.execute',{'command':'new','params':{'metric':True}})
    bridge.call('cadcraft','engine.execute',{'command':'pline','params':{
        'vertices':[[0,0],[40,0],[40,30],[0,30]],'closed':True}})
    bridge.call('cadcraft','app.save',{'path':str(out/'profile.dxf')})
    drawing=bridge.call('cadcraft','drawing.inspect',{'entities':True,'limit':100})
    extrusion=export_extrusion(drawing,20,out,'block-40x30x20')
    bridge.call('cadcraft','app.open',{'path':str(out/extrusion['files']['dxf'])})
    before=triangles_from_drawing(bridge.call('cadcraft','drawing.inspect',{'entities':True,'limit':100}))
    bridge.call('cadcraft','app.save',{'path':str(out/'block-cadcraft-saved.dxf')})
    bridge.call('cadcraft','app.open',{'path':str(out/'block-cadcraft-saved.dxf')})
    reopened=bridge.call('cadcraft','drawing.inspect',{'entities':True,'limit':100})
    if before!=triangles_from_drawing(reopened):
        raise ValueError('CADCraft changed the triangle mesh after save/reopen')
    report=export_stl(reopened,out,'block-cadcraft-reopened')
    report.update(app='CADCraft',native_brep=False,dxf_saved_and_reopened=True,
                  pipeline='CADCraft profile -> bridge extrusion -> CADCraft face roundtrip -> bridge STL')
    (out/'solid-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--state-dir',type=Path)
    args=parser.parse_args()
    print(json.dumps(run(args.workspace,args.state_dir),indent=2))
