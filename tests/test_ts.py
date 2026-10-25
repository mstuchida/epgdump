#!/usr/bin/env python3
"""Run the actual epgdump command on CRC-valid TS, without tuners."""
import datetime
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

def crc(data):
    value=0xffffffff
    for byte in data:
        value ^= byte<<24
        for _ in range(8):
            value=((value<<1) ^ (0x04c11db7 if value&0x80000000 else 0)) & 0xffffffff
    return value

def bcd(n): return n//10*16+n%10

def section(table,version,event,hour,duration=1,unknown=False,current=True):
    title=b'\x0eMATCH'
    desc=b'\x4d'+bytes([5+len(title)])+b'jpn'+bytes([len(title)])+title+b'\x00'
    data=bytearray([table,0xf0,0,4,0x30,0xc0|version<<1|int(current),0,0,0,1,0,1,0,table])
    data+=struct.pack('>H',event)
    data+=b'\xff'*5 if unknown else bytes([0xed,0x8a,bcd(hour),0,0])
    data+=bytes([bcd(duration),0,0,0x80,len(desc)])+desc
    length=len(data)+1
    data[1]|=length>>8; data[2]=length&255
    return data+struct.pack('>I',crc(data))

def packet(data,cc):
    p=bytes([0x47,0x40,0x12,0x10|(cc&15),0])+data
    assert len(p)<=188
    return p+b'\xff'*(188-len(p))

with tempfile.TemporaryDirectory(prefix='epgdump-ts-test-') as name:
    root=Path(name)
    cases={
        'pf-only':[section(0x4e,0,0,22)],
        'schedule-before-pf':[section(0x50,0,7,21),section(0x4e,0,7,22,2)],
        'schedule-after-pf':[section(0x4e,0,7,22,2),section(0x50,1,7,21)],
        'unknown':[section(0x50,0,7,21),section(0x4e,0,7,22,unknown=True)],
        'replacement':[section(0x4e,0,7,22),section(0x4e,0,8,22)],
    }
    for case,sections in cases.items():
        source=root/(case+'.ts');out=root/(case+'.xml')
        source.write_bytes(b''.join(packet(s,n) for n,s in enumerate(sections))+b'\x47\x1f\xff\x10'+b'\xff'*184)
        result=subprocess.run([sys.argv[1],'27',str(source),str(out)],env=dict(os.environ,TZ='Asia/Tokyo',ASAN_OPTIONS='detect_leaks=0'),capture_output=True,timeout=5)
        assert result.returncode==0,(case,result.stderr)
        values=ET.parse(out).getroot().findall('programme')
        assert len(values)==(0 if case=='unknown' else 2 if case=='replacement' else 1),(case,out.read_text())
        if case in ('schedule-before-pf','schedule-after-pf'):
            assert values[0].get('start')[8:14]=='220000',out.read_text()
            assert values[0].get('stop')[8:14]=='000000',out.read_text()
        if case=='pf-only': assert values[0].get('event_id')=='0'
        print('PASS epgdump TS:',case)
