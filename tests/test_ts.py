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

def section(table,version,event,hour,duration=1,unknown=False,current=True,sid=0x430,onid=1,detail=False):
    title=b'\x0eMATCH'
    desc=b'\x4d'+bytes([5+len(title)])+b'jpn'+bytes([len(title)])+title+b'\x00'
    if detail:
        heading=b'\x0eHEADING'; text=b'\x0eDETAIL'
        items=bytes([len(heading)])+heading+bytes([len(text)])+text
        extended=b'\x00jpn'+bytes([len(items)])+items+b'\x00'
        desc+=b'\x4e'+bytes([len(extended)])+extended
    data=bytearray([table,0xf0,0,sid>>8,sid&255,0xc0|version<<1|int(current),0,0,0,1,onid>>8,onid&255,0,table])
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

    # No SDT: EIT-created services must also be filtered. Both EIT orders and
    # p/f-only data are covered; ordinary subchannels and satellite SIDs survive.
    for reverse in (False, True):
        for table in (0x4e, 0x50):
            services=[(1024,0x7fe0),(1025,0x7fe0),(1408,0x7fe0),
                      (23992,0x7e87),(23993,0x7e87),(1408,4),(1408,6)]
            if reverse: services.reverse()
            source=root/'mixed.ts'; out=root/'mixed.xml'
            sections=[section(table,0,7,22,sid=sid,onid=onid,detail=True) for sid,onid in services]
            source.write_bytes(b''.join(packet(s,n) for n,s in enumerate(sections))
                               +b'\x47\x1f\xff\x10'+b'\xff'*184)
            result=subprocess.run([sys.argv[1],'27',str(source),str(out)],
                                  env=dict(os.environ,TZ='Asia/Tokyo',ASAN_OPTIONS='detect_leaks=0'),
                                  capture_output=True,timeout=5)
            assert result.returncode==0,result.stderr
            xml=ET.parse(out).getroot()
            expected=['GR_1024','GR_1025','27_1408','27_1408']
            assert sorted(c.get('id') for c in xml.findall('channel'))==sorted(expected),out.read_text()
            programmes=xml.findall('programme')
            assert sorted(p.get('channel') for p in programmes)==sorted(expected),out.read_text()
            for p in programmes:
                assert p.findtext('extdesc/item_description')=='ＨＥＡＤＩＮＧ',out.read_text()
                assert p.findtext('extdesc/item')=='ＤＥＴＡＩＬ',out.read_text()
            print('PASS epgdump TS: one-seg excluded, subchannels/satellites/details preserved',table,reverse)
