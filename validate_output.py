# -*- coding: utf-8 -*-
import zipfile
import xml.etree.ElementTree as ET
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

generated_files = [
    r'c:\Users\user\Desktop\Claude skills\hwpx-report-skill\docs\recruit_sample.hwpx',
    r'c:\Users\user\Desktop\Claude skills\hwpx-report-skill\docs\training_sample.hwpx'
]

for file_path in generated_files:
    print(f"\n--- Validating: {file_path} ---")
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            # 1. Check mimetype compression (must be stored, i.e., compression method = 0)
            mimetype_info = z.getinfo('mimetype')
            if mimetype_info.compress_type != zipfile.ZIP_STORED:
                print(f"  [ERROR] mimetype is compressed (type={mimetype_info.compress_type}). Must be ZIP_STORED (0).")
            else:
                print("  [OK] mimetype is ZIP_STORED.")
                
            # 2. Check XML well-formedness of section0.xml
            sec_data = z.read('Contents/section0.xml')
            try:
                ET.fromstring(sec_data)
                print("  [OK] Contents/section0.xml is well-formed XML.")
            except ET.ParseError as pe:
                print(f"  [ERROR] Contents/section0.xml parsing failed: {pe}")
                
            # 3. Check XML well-formedness of content.hpf
            hpf_data = z.read('Contents/content.hpf')
            try:
                ET.fromstring(hpf_data)
                print("  [OK] Contents/content.hpf is well-formed XML.")
            except ET.ParseError as pe:
                print(f"  [ERROR] Contents/content.hpf parsing failed: {pe}")
                
            # 4. Check that all template files exist
            template_files = ['mimetype', 'version.xml', 'Contents/header.xml', 'BinData/image1.png', 'settings.xml', 'META-INF/container.xml']
            missing = [f for f in template_files if f not in z.namelist()]
            if missing:
                print(f"  [ERROR] Missing files in archive: {missing}")
            else:
                print("  [OK] All template resource files are copied.")
                
    except Exception as e:
        print(f"  [ERROR] Failed to validate file: {e}")
