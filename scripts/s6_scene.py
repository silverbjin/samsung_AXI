#!/usr/bin/env python3
"""S6-00 standalone stack-of-plates Gazebo fixture, not part of S5 world/map."""
from pathlib import Path
from xml.etree import ElementTree as ET

TABLE3_WORLD_XY=(2.65,-3.20)
FIXTURE_WORLD_XY=(2.65,-2.91)
def fixture_sdf():
    sdf=ET.Element('sdf',{'version':'1.8'})
    model=ET.SubElement(sdf,'model',{'name':'s6_stacked_dishes'})
    ET.SubElement(model,'static').text='true'
    link=ET.SubElement(model,'link',{'name':'body'})
    for i in range(3):
        for kind,radius,height,z,color in (
            ('plate',.235,.029,.723+.036*i,'0.85 0.93 0.98 1'),
            ('blue_rim',.245,.007,.742+.036*i,'0.10 0.52 0.93 1')):
            name=f'{kind}_{i}'
            for typ in ('visual','collision'):
                element=ET.SubElement(link,typ,{'name':name})
                ET.SubElement(element,'pose').text=f'0 0 {z:.3f} 0 0 0'
                geom=ET.SubElement(element,'geometry')
                cylinder=ET.SubElement(geom,'cylinder')
                ET.SubElement(cylinder,'radius').text=str(radius)
                ET.SubElement(cylinder,'length').text=str(height)
                if typ=='visual':
                    material=ET.SubElement(element,'material')
                    ET.SubElement(material,'ambient').text=color
                    ET.SubElement(material,'diffuse').text=color
    return ET.tostring(sdf,encoding='unicode')

def write_fixture(dst):
    dst=Path(dst);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text('<?xml version="1.0"?>\n'+fixture_sdf()+'\n')
    ET.parse(dst)
    print('S6_00_DISH_STACK_FIXTURE_STATIC_OK '+str(dst),flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    write_fixture(p.parse_args().out)
