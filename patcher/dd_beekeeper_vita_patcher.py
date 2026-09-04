from __future__ import annotations
import argparse, json, math, shutil, struct, subprocess, sys, tempfile, zipfile
from pathlib import Path

APP_NAME = "DD Beekeeper Class Vita Patcher"
VERSION = "0.1-dev"
TITLE_ID = "PCSE00919"
TRANSLATIONS_FILE = Path(__file__).with_name("translations.json")

def load_translations():
    if not TRANSLATIONS_FILE.exists():
        return {}
    return json.loads(TRANSLATIONS_FILE.read_text(encoding="utf-8"))


def log(msg): print(msg, flush=True)

def run(cmd, cwd=None):
    log("> " + " ".join(f'"{x}"' if " " in str(x) else str(x) for x in cmd))
    cp = subprocess.run([str(x) for x in cmd], cwd=cwd, text=True, capture_output=True)
    if cp.stdout.strip(): print(cp.stdout.rstrip())
    if cp.returncode != 0:
        if cp.stderr.strip(): print(cp.stderr.rstrip(), file=sys.stderr)
        raise RuntimeError(f"Command failed ({cp.returncode}): {cmd[0]}")
    return cp

def nearest_pow2_half(v:int)->int:
    x=max(1.0,v/2.0)
    return max(4,min(1024,int(2 ** round(math.log(x,2)))))

def compression_for(rel:Path)->str:
    s=rel.as_posix().lower()
    if ".ability." in s or "portrait_roster" in s or "/icons_equip/" in "/"+s or "/raid/camping/skill_icons/" in "/"+s:
        return "DXT1"
    return "DXT5"

def parse_gxt(path:Path):
    b=path.read_bytes()
    if len(b)<64 or b[:4]!=b"GXT\x00":
        raise RuntimeError(f"Invalid GXT: {path}")
    _,_,_,_,_,fmt,wh,_=struct.unpack_from("<IIiIIIII",b,32)
    return {"format":fmt,"width":wh & 0xffff,"height":(wh>>16)&0xffff}

def resolve_mod(source:Path, tmp:Path)->Path:
    if source.is_dir():
        candidates=[source, source/"beekeeper_class", source/"_class"]
        for c in candidates:
            if (c/"heroes"/"beekeeper").exists(): return c
        raise RuntimeError("Could not find heroes/beekeeper inside the selected mod folder.")
    if source.suffix.lower()==".zip":
        dst=tmp/"mod"
        with zipfile.ZipFile(source) as z: z.extractall(dst)
        hits=list(dst.rglob("heroes/beekeeper"))
        if not hits: raise RuntimeError("ZIP does not contain heroes/beekeeper.")
        return hits[0].parents[1]
    raise RuntimeError("Mod input must be a folder or ZIP.")

def loc2_to_loc(src:Path,dst:Path,text_map:dict[str,str]|None=None):
    b=src.read_bytes()
    if len(b)<4200: raise RuntimeError(f"LOC2 too small: {src.name}")
    h1,h2,h3=struct.unpack_from("<III",b,0)
    if not (4108<=h1<=h2<=h3<=len(b)):
        raise RuntimeError(f"Unsupported LOC2 layout: {src.name}")
    prefix=bytearray(b[4:4108])
    for off in range(0,len(prefix)-3,4):
        v=struct.unpack_from("<I",prefix,off)[0]
        if 4108<=v<=h1: struct.pack_into("<I",prefix,off,v-4)
    recsrc=b[4108:h1]
    if len(recsrc)%12: raise RuntimeError(f"Invalid LOC2 hash table: {src.name}")
    records=bytearray()
    for off in range(0,len(recsrc),12):
        h,idx,cnt=struct.unpack_from("<III",recsrc,off)
        records += struct.pack("<III",h,cnt,idx)

    descsrc=b[h2:h3]
    if len(descsrc)%12: raise RuntimeError(f"Invalid LOC2 descriptors: {src.name}")
    n=len(descsrc)//12
    for off in range(0,len(records),12):
        _,cnt,idx=struct.unpack_from("<III",records,off)
        if cnt and (idx>=n or idx+cnt>n): raise RuntimeError(f"Invalid LOC2 index: {src.name}")

    # Descriptors point to NUL-terminated UTF-8 strings. Rebuild the blob so
    # translations can change byte length without touching the hash/index table.
    old_blob=b[h3:]
    new_blob=bytearray()
    new_desc=bytearray()
    text_map=text_map or {}
    for i in range(n):
        old_off,old_len,flags=struct.unpack_from("<III",descsrc,i*12)
        raw=old_blob[old_off:old_off+old_len]
        if raw.endswith(b"\x00"): raw=raw[:-1]
        source=raw.decode("utf-8")
        translated=text_map.get(source,source)
        enc=translated.encode("utf-8")+b"\x00"
        new_desc += struct.pack("<III",len(new_blob),len(enc),flags)
        new_blob += enc

    pre=prefix+records
    struct.pack_into("<II",pre,0,len(pre),len(pre)+len(new_desc))
    dst.write_bytes(bytes(pre)+bytes(new_desc)+bytes(new_blob))

def update_manifest(stage:Path):
    mf=stage/"PSArcManifest.bin"
    if not mf.exists(): return
    files=sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file() and p.name!="PSArcManifest.bin")
    mf.write_text("\n".join(files)+"\n",encoding="utf-8",newline="\n")

def force_stagecoach(stage:Path):
    p=stage/"campaign"/"roster"/"base.roster.groups.json"
    data=json.loads(p.read_text(encoding="utf-8-sig"))
    changed=False
    def walk(o):
        nonlocal changed
        if isinstance(o,dict):
            for k,v in o.items():
                if k=="class_ids" and isinstance(v,list):
                    o[k]=["beekeeper"]; changed=True
                else: walk(v)
        elif isinstance(o,list):
            for v in o: walk(v)
    walk(data)
    if not changed: raise RuntimeError("Could not find class_ids in Stage Coach roster.")
    p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    log("Debug option enabled: Stage Coach pool forced to Beekeeper.")

def convert_textures(mod:Path, tool:Path):
    pngs=sorted(mod.rglob("*.png"))
    temp=Path(tempfile.mkdtemp(prefix="ddbeekeeper_gxt_"))
    try:
        shutil.copy2(tool,temp/"psp2gxt.exe")
        for i,png in enumerate(pngs,1):
            rel=png.relative_to(mod)
            from PIL import Image
            with Image.open(png) as im:
                ow,oh=im.size; tw,th=nearest_pow2_half(ow),nearest_pow2_half(oh)
                comp=compression_for(rel)
                img=im.convert("RGBA").resize((tw,th),Image.Resampling.LANCZOS)
                img.save(temp/"in.dds",format="DDS",pixel_format=comp)
            out=temp/"out.gxt"
            if out.exists(): out.unlink()
            run([temp/"psp2gxt.exe","-i","in.dds","-o","out.gxt"],cwd=temp)
            g=parse_gxt(out)
            expected=0x85000000 if comp=="DXT1" else 0x87000000
            if (g["width"],g["height"],g["format"])!=(tw,th,expected):
                raise RuntimeError(f"GXT validation failed: {rel}")
            shutil.copy2(out,png)
            png.with_suffix(".txt").write_text(f"DesignWidth={ow}\nDesignHeight={oh}\nColorMode=sRGB\n",encoding="ascii")
            log(f"[GXT {i}/{len(pngs)}] {rel} {ow}x{oh} -> {tw}x{th} {comp}")
    finally:
        shutil.rmtree(temp,ignore_errors=True)

def overlay_mod(stage:Path,mod:Path):
    # Vita loads a custom class from the content root, not dlc/<mod>.
    for item in mod.iterdir():
        if item.name.lower() in {"preview_icon.png","project.xml","modfiles.txt"}: continue
        dst=stage/item.name
        if item.is_dir(): shutil.copytree(item,dst,dirs_exist_ok=True)
        else: shutil.copy2(item,dst)
    # known typo in original distribution
    bad=stage/"upgrades"/"heores"/"beekeeper.upgrades.json"
    good=stage/"upgrades"/"heroes"/"beekeeper.upgrades.json"
    if bad.exists():
        good.parent.mkdir(parents=True,exist_ok=True); shutil.move(str(bad),str(good))
        try: bad.parent.rmdir()
        except OSError: pass

def prepare_localization(stage:Path,mod:Path):
    loc=stage/"localization"; loc.mkdir(exist_ok=True)
    # remove Beekeeper loc2 from active Vita content, replace with legacy .loc
    for p in loc.glob("*beekeeper*.loc2"): p.unlink()
    for p in loc.glob("2634437056_*.loc2"): p.unlink()
    srcdir=mod/"localization"
    translations=load_translations()
    for p in sorted(srcdir.glob("2634437056_*.loc2")):
        lang=p.stem.split("_",1)[1]
        text_map=translations.get(lang,{})
        loc2_to_loc(p,loc/f"beekeeper_{lang}.loc",text_map)
        if text_map:
            log(f"Localization [{lang}]: applied {len(text_map)} translated strings.")
    log(f"Localization: generated {len(list(loc.glob('beekeeper_*.loc')))} Vita .loc files.")

def prepare_audio_output(mod:Path,outroot:Path,load_order:Path|None=None):
    bank=mod/"audio"/"secondary_banks"/"hero_beekeeper.bank"
    if not bank.exists():
        log("Audio bank not found in mod; skipping external bank.")
        return
    target=outroot/TITLE_ID/"audio"/"secondary_banks"
    target.mkdir(parents=True,exist_ok=True)
    shutil.copy2(bank,target/"hero_beekeeper.bank")
    log("Copied hero_beekeeper.bank to rePatch audio/secondary_banks.")
    if load_order and load_order.exists():
        data=json.loads(load_order.read_text(encoding="utf-8-sig"))
        heroes=data.setdefault("heroes",[])
        entry="audio/secondary_banks/hero_beekeeper.bank"
        if entry not in heroes: heroes.append(entry)
        out=outroot/TITLE_ID/"audio"/"load_order.json"
        out.parent.mkdir(parents=True,exist_ok=True)
        out.write_text(json.dumps(data,indent=4,ensure_ascii=False)+"\n",encoding="utf-8")
        log("Patched audio/load_order.json for hero_beekeeper.bank.")
    else:
        log("WARNING: no original audio/load_order.json supplied; custom Beekeeper audio will not be enabled.")

def main(argv=None):
    ap=argparse.ArgumentParser(description=APP_NAME)
    ap.add_argument("--psarc",required=True,type=Path,help="Original Vita content_patch_13.psarc")
    ap.add_argument("--mod",required=True,type=Path,help="Original Beekeeper mod ZIP or folder")
    ap.add_argument("--output",type=Path,default=Path("output"),help="Output directory")
    ap.add_argument("--tools",type=Path,default=Path("tools"),help="Folder containing psp2psarc.exe and psp2gxt.exe")
    ap.add_argument("--audio-load-order",type=Path,help="Optional original app/audio/load_order.json; enables Beekeeper custom audio")
    ap.add_argument("--force-stagecoach",action="store_true",help="DEBUG: force Beekeeper as the Stage Coach class pool (OFF by default)")
    ap.add_argument("--keep-work",action="store_true")
    args=ap.parse_args(argv)

    psarc=args.psarc.resolve(); modsrc=args.mod.resolve(); tools=args.tools.resolve(); output=args.output.resolve()
    psarc_tool=tools/"psp2psarc.exe"; gxt_tool=tools/"psp2gxt.exe"
    for p in (psarc,psarc_tool,gxt_tool):
        if not p.exists(): raise SystemExit(f"Missing required file: {p}")
    try:
        import PIL
    except ImportError:
        raise SystemExit("Pillow is required: py -m pip install Pillow")

    work=Path(tempfile.mkdtemp(prefix="ddbeekeepervita_"))
    try:
        mod=resolve_mod(modsrc,work)
        modwork=work/"beekeeper_class"
        shutil.copytree(mod,modwork)
        log(f"{APP_NAME} {VERSION}")
        log(f"Mod: {mod}")
        run([psarc_tool,"verify",psarc])
        stage=work/"content"
        stage.mkdir()
        run([psarc_tool,"extract","--input",psarc,"--to",stage,"-y"])
        convert_textures(modwork,gxt_tool)
        overlay_mod(stage,modwork)
        prepare_localization(stage,modwork)

        # Do not load the PC campaign load-order file inside PSARC.
        for p in [stage/"audio"/"beekeeper.campaign.load_order.json"]:
            if p.exists(): p.unlink()
        if args.force_stagecoach: force_stagecoach(stage)

        update_manifest(stage)
        filelist=work/"files.txt"
        filelist.write_text("\n".join(sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file()))+"\n",encoding="ascii")
        repatch=output/"rePatch"; target=repatch/TITLE_ID
        target.mkdir(parents=True,exist_ok=True)
        outpsarc=target/"content_patch_13.psarc"
        run([psarc_tool,"create","-y","-o",outpsarc,"-I",filelist],cwd=stage)
        run([psarc_tool,"verify",outpsarc])
        load_order=args.audio_load_order.resolve() if args.audio_load_order else None
        if load_order is None:
            auto=psarc.parent/"audio"/"load_order.json"
            if auto.exists(): load_order=auto
        prepare_audio_output(modwork,repatch,load_order)
        meta={
          "tool":APP_NAME,"version":VERSION,"title_id":TITLE_ID,
          "force_stagecoach":bool(args.force_stagecoach),
          "source_psarc":psarc.name,"source_mod":modsrc.name
        }
        (output/"patch_report.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
        log(f"\nDONE\nCopy this folder to ux0:/\n{repatch}")
    finally:
        if args.keep_work:
            log(f"Work directory kept: {work}")
        else:
            shutil.rmtree(work,ignore_errors=True)

if __name__=="__main__":
    main()
