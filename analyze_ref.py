"""참조 HWPX 파일 완전 분석 스크립트"""
import sys, io, zipfile, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

REF_PATH = r'c:\Users\user\Desktop\Claude skills\docs\ai_policy_report.hwpx'

with zipfile.ZipFile(REF_PATH, 'r') as z:
    print('=== 파일 목록 ===')
    for info in z.infolist():
        print(f'  {info.filename}  compress={info.compress_type}  size={info.file_size}B')

    header = z.read('Contents/header.xml').decode('utf-8', 'replace')
    sec    = z.read('Contents/section0.xml').decode('utf-8', 'replace')
    hpf    = z.read('Contents/content.hpf').decode('utf-8', 'replace')

    # ── charPr 목록 ──────────────────────────────────────────
    print('\n=== charPr 목록 ===')
    for m in re.finditer(r'<hh:charPr\s+id="(\d+)"[^>]*height="(\d+)"[^>]*textColor="([^"]*)"([^>]*)>', header):
        rest = m.group(4)
        bold = 'YES' if 'bold="1"' in rest else ''
        italic = 'YES' if 'italic="1"' in rest else ''
        bfref = re.search(r'borderFillIDRef="(\d+)"', rest)
        bf = bfref.group(1) if bfref else '?'
        print(f'  id={m.group(1):>3}  height={m.group(2):>5}  color={m.group(3):<12}  bold={bold:<4}  ital={italic:<4}  bfRef={bf}')

    # ── paraPr 목록 ──────────────────────────────────────────
    print('\n=== paraPr 목록 (align, lineSpacing) ===')
    pp_ids = re.findall(r'<hh:paraPr id="(\d+)"', header)
    pp_aligns = re.findall(r'<hh:align horizontal="([^"]+)"', header)
    pp_ls = re.findall(r'<hh:lineSpacing[^>]*value="(\d+)"', header)
    for i in range(min(len(pp_ids), len(pp_aligns), len(pp_ls))):
        print(f'  id={pp_ids[i]:>3}  align={pp_aligns[i]:<10}  lineSpacing={pp_ls[i]}%')

    # ── borderFill 목록 ──────────────────────────────────────
    print('\n=== borderFill 목록 ===')
    for m in re.finditer(r'<hh:borderFill id="(\d+)".*?(?:</hh:borderFill>)', header, re.DOTALL):
        bf_xml = m.group(0)
        bid = m.group(1)
        face = re.search(r'faceColor="([^"]*)"', bf_xml)
        fc = face.group(1) if face else 'none'
        l = re.search(r'<hh:leftBorder[^>]*type="([^"]+)"[^>]*color="([^"]*)"', bf_xml)
        b = re.search(r'<hh:bottomBorder[^>]*type="([^"]+)"[^>]*color="([^"]*)"', bf_xml)
        lt = f'{l.group(1)}/{l.group(2)}' if l else ''
        bt = f'{b.group(1)}/{b.group(2)}' if b else ''
        print(f'  id={bid:>3}  fill={fc:<12}  left={lt:<20}  bottom={bt}')

    # ── section0의 첫번째 표 구조 ────────────────────────────
    print('\n=== section0.xml 첫번째 tbl 구조 ===')
    m = re.search(r'<hp:tbl.*?</hp:tbl>', sec, re.DOTALL)
    if m:
        print(m.group(0)[:3000])

    # ── 단락 구조 샘플 ────────────────────────────────────────
    print('\n=== section0.xml 단락 샘플 (비표 영역) ===')
    paras = re.findall(r'<hp:p id="[^"]*" paraPrIDRef="(\d+)"[^>]*>.*?</hp:p>', sec, re.DOTALL)
    for p in paras[:5]:
        print(p[:400])
        print('---')

    # ── header.xml 전체 저장 ─────────────────────────────────
    out_header = r'c:\Users\user\Desktop\Claude skills\hwpx-report-skill\ref_header.xml'
    with open(out_header, 'w', encoding='utf-8') as f:
        f.write(header)
    print(f'\n[저장] ref_header.xml -> {out_header}')

    # ── section0.xml 전체 저장 ───────────────────────────────
    out_sec = r'c:\Users\user\Desktop\Claude skills\hwpx-report-skill\ref_section0.xml'
    with open(out_sec, 'w', encoding='utf-8') as f:
        f.write(sec)
    print(f'[저장] ref_section0.xml -> {out_sec}')

    # ── content.hpf 전체 저장 ────────────────────────────────
    out_hpf = r'c:\Users\user\Desktop\Claude skills\hwpx-report-skill\ref_content.hpf'
    with open(out_hpf, 'w', encoding='utf-8') as f:
        f.write(hpf)
    print(f'[저장] ref_content.hpf -> {out_hpf}')
