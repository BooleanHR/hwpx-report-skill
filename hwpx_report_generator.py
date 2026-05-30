"""
hwpx_report_generator.py  v2.0
================================
실무 의사결정용 HWPX 표준 보고서 생성기 - 프리미엄 양식 버전

[손상 방지 5대 규칙]
1. mimetype → ZIP_STORED (압축 없음, 필수)
2. container.xml media-type → "application/hwpml-package+xml"
3. 네임스페이스 URI → 실제 한컴 표준 hwpml/2011/...
4. XML 특수문자 → xml_escape() 함수로 반드시 이스케이프
5. section 루트 태그 → <hs:sec> (hp:section 아님)

[v2.0 개선사항]
- 실제 한컴 파일 역공학 기반 정확한 XML 구조 사용 (hh:charPr, hh:paraPr)
- 전문 비즈니스 레이아웃: 타이틀 블록, KPI 카드, 섹션 헤더
- 14종 borderFill + 12종 charPr 정의로 풍부한 스타일 지원
- 비례 열 너비, 교대 행 음영, 합계 행 강조
- 가로 구분선, 메타 정보 행 추가
"""

import os
import zipfile
from datetime import date, datetime
from typing import Optional, List


# ─────────────────────────────────────────────────────────────
# 도메인 상수
# ─────────────────────────────────────────────────────────────
DOMAIN_RECRUIT  = "RECRUIT"
DOMAIN_TRAINING = "TRAINING"
DOMAIN_SALES    = "SALES"
DOMAIN_BUDGET   = "BUDGET"
DOMAIN_PROJECT  = "PROJECT"


# ─────────────────────────────────────────────────────────────
# 공통 HWPML 네임스페이스 (실제 한컴 표준)
# ─────────────────────────────────────────────────────────────
HWPML_NS = (
    'xmlns:ha="http://www.hancom.co.kr/hwpml/2011/app" '
    'xmlns:hp="http://www.hancom.co.kr/hwpml/2011/paragraph" '
    'xmlns:hp10="http://www.hancom.co.kr/hwpml/2016/paragraph" '
    'xmlns:hs="http://www.hancom.co.kr/hwpml/2011/section" '
    'xmlns:hc="http://www.hancom.co.kr/hwpml/2011/core" '
    'xmlns:hh="http://www.hancom.co.kr/hwpml/2011/head" '
    'xmlns:hhs="http://www.hancom.co.kr/hwpml/2011/history" '
    'xmlns:hm="http://www.hancom.co.kr/hwpml/2011/master-page" '
    'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf" '
    'xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:opf="http://www.idpf.org/2007/opf/" '
    'xmlns:ooxmlchart="http://www.hancom.co.kr/hwpml/2016/ooxmlchart" '
    'xmlns:hwpunitchar="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar" '
    'xmlns:epub="http://www.idpf.org/2007/ops" '
    'xmlns:config="urn:oasis:names:tc:opendocument:xmlns:config:1.0"'
)


# ─────────────────────────────────────────────────────────────
# XML 유틸리티
# ─────────────────────────────────────────────────────────────
def xe(text: str) -> str:
    """XML 특수문자 이스케이프"""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


_id_counter = [1000]

def nid() -> int:
    _id_counter[0] += 1
    return _id_counter[0]


# ─────────────────────────────────────────────────────────────
# 수치 검증 유틸리티
# ─────────────────────────────────────────────────────────────
def validate_sum(items: list, amount_key: str, declared_total: float) -> tuple:
    calculated = sum(
        float(str(item.get(amount_key, 0)).replace(',', '').replace('₩', '').strip())
        for item in items
    )
    return abs(calculated - declared_total) < 0.01, calculated

def format_number(n: float, unit: str = "원") -> str:
    return f"{int(n):,}{unit}"

def format_percentage(numerator: float, denominator: float, decimal: int = 1) -> str:
    if denominator == 0:
        return "N/A"
    return f"{(numerator / denominator * 100):.{decimal}f}%"


# ─────────────────────────────────────────────────────────────
# HWPX XML 파일 빌더
# ─────────────────────────────────────────────────────────────
class HwpxXmlBuilder:

    @staticmethod
    def mimetype() -> bytes:
        return b"application/hwp+zip"

    @staticmethod
    def container_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<ocf:container '
            'xmlns:ocf="urn:oasis:names:tc:opendocument:xmlns:container" '
            'xmlns:hpf="http://www.hancom.co.kr/schema/2011/hpf">'
            '<ocf:rootfiles>'
            '<ocf:rootfile full-path="Contents/content.hpf" '
            'media-type="application/hwpml-package+xml"/>'
            '</ocf:rootfiles>'
            '</ocf:container>'
        )

    @staticmethod
    def manifest_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            '<manifest:manifest '
            'xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0">'
            '<manifest:file-entry manifest:full-path="/" '
            'manifest:media-type="application/hwp+zip"/>'
            '</manifest:manifest>'
        )

    @staticmethod
    def content_hpf(title: str) -> str:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<opf:package {HWPML_NS} version="" unique-identifier="" id="">'
            '<opf:metadata>'
            f'<opf:title>{xe(title)}</opf:title>'
            '<opf:language>ko</opf:language>'
            f'<opf:meta name="CreatedDate" content="text">{now}</opf:meta>'
            f'<opf:meta name="ModifiedDate" content="text">{now}</opf:meta>'
            '</opf:metadata>'
            '<opf:manifest>'
            '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
            '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
            '<opf:item id="settings" href="settings.xml" media-type="application/xml"/>'
            '</opf:manifest>'
            '<opf:spine><opf:itemref idref="section0"/></opf:spine>'
            '</opf:package>'
        )

    @staticmethod
    def settings_xml() -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<ha:HWPApplicationSetting {HWPML_NS}>'
            '<ha:CaretPosition section="0" para="0" pos="0"/>'
            '</ha:HWPApplicationSetting>'
        )

    @staticmethod
    def header_xml() -> str:
        """
        실제 한컴 파일 역공학 기반 header.xml
        - hh:charPr / hh:paraPr (실제 태그명)
        - hc:fillBrush (실제 네임스페이스)

        borderFill ID 체계:
          0: 테두리없음, 투명 (단락 기본)
          1: 회색 얇은 테두리, 흰 배경 (기본 데이터 셀)
          2: 파란 테두리, 진한 파란 배경 (#1565C0) (표 헤더)
          3: 회색 테두리, 연회색 배경 #F5F5F5 (교대행)
          4: 파란 테두리, 연파란 배경 #E3F2FD (강조 셀/BLUF)
          5: 테두리없음, 진한 파란 배경 #0D47A1 (타이틀 블록)
          6: 회색 테두리, 연보라 배경 #E8EAF6 (합계행)
          7: 테두리없음, 파란 배경 #1565C0 (KPI 카드)
          8: 두꺼운 LEFT 파란 테두리, 아래 회색 선, 연회색 배경 (섹션 헤더)
          9: 사방 파란 테두리 0.5mm, 흰 배경 (메타 정보)

        charPr ID 체계:
          0: 본문 10pt 검정 (#212121)
          1: 제목 18pt 흰색 굵게
          2: 섹션 제목 11pt 파란색 (#1565C0) 굵게
          3: 표 헤더 9pt 흰색 굵게
          4: KPI 값 16pt 흰색 굵게
          5: KPI 레이블 8pt 연파랑 (#B3D4F5)
          6: 메타/보조 9pt 회색 (#757575)
          7: 합계행 10pt 검정 굵게
          8: 강조 10pt 파란색 굵게
          9: 주석 8pt 회색
          10: 타이틀 부제 10pt 연파랑 (#B3D4F5)
          11: BLUF 레이블 9pt 파란색 굵게

        paraPr ID 체계:
          0: 왼쪽 정렬 160%
          1: 가운데 정렬 160%
          2: 왼쪽 정렬 130% (표 셀 내부)
          3: 가운데 정렬 130% (표 셀 내부 가운데)
        """

        def bf(id, l_type, l_w, l_c, r_type, r_w, r_c,
               t_type, t_w, t_c, b_type, b_w, b_c, fill_color=None):
            fc = f'<hc:fillBrush><hc:winBrush faceColor="{fill_color}" hatchColor="#000000" alpha="0"/></hc:fillBrush>' if fill_color else '<hc:fillBrush><hc:noFill/></hc:fillBrush>'
            return (
                f'<hh:borderFill id="{id}" threeD="0" shadow="0" centerLine="NONE" breakCellSeparateLine="0">'
                '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
                '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
                f'<hh:leftBorder type="{l_type}" width="{l_w}" color="{l_c}"/>'
                f'<hh:rightBorder type="{r_type}" width="{r_w}" color="{r_c}"/>'
                f'<hh:topBorder type="{t_type}" width="{t_w}" color="{t_c}"/>'
                f'<hh:bottomBorder type="{b_type}" width="{b_w}" color="{b_c}"/>'
                f'{fc}'
                '</hh:borderFill>'
            )

        N = 'NONE'; S = 'SOLID'; g = '#BDBDBD'; bl = '#1565C0'; db = '#0D47A1'

        border_fills = (
            '<hh:borderFills itemCnt="10">'
            # 0: 투명 (기본)
            + bf(0, N,'0.1 mm','#000000', N,'0.1 mm','#000000', N,'0.1 mm','#000000', N,'0.1 mm','#000000')
            # 1: 얇은 회색 테두리, 흰 배경
            + bf(1, S,'0.12 mm',g, S,'0.12 mm',g, S,'0.12 mm',g, S,'0.12 mm',g, '#FFFFFF')
            # 2: 파란 테두리, 진한 파란 배경 (표 헤더)
            + bf(2, S,'0.12 mm',bl, S,'0.12 mm',bl, S,'0.12 mm',bl, S,'0.12 mm',bl, '#1565C0')
            # 3: 회색 테두리, 연회색 배경 (교대행)
            + bf(3, S,'0.12 mm',g, S,'0.12 mm',g, S,'0.12 mm',g, S,'0.12 mm',g, '#F5F5F5')
            # 4: 파란 테두리, 연파란 배경 (강조 셀)
            + bf(4, S,'0.12 mm',bl, S,'0.12 mm',bl, S,'0.12 mm',bl, S,'0.12 mm',bl, '#E3F2FD')
            # 5: 테두리없음, 아주 진한 파란 배경 (타이틀)
            + bf(5, N,'0.1 mm',db, N,'0.1 mm',db, N,'0.1 mm',db, N,'0.1 mm',db, '#0D47A1')
            # 6: 회색 테두리, 연보라 배경 (합계행)
            + bf(6, S,'0.12 mm',g, S,'0.12 mm',g, S,'0.5 mm',g, S,'0.12 mm',g, '#E8EAF6')
            # 7: 테두리없음, 파란 배경 (KPI카드)
            + bf(7, N,'0.1 mm',bl, N,'0.1 mm',bl, N,'0.1 mm',bl, N,'0.1 mm',bl, '#1565C0')
            # 8: 두꺼운 LEFT파란, 아래 회색 얇은, 연회색 배경 (섹션헤더)
            + bf(8, S,'2 mm',bl, N,'0.1 mm',g, N,'0.1 mm',g, S,'0.12 mm',g, '#F8F9FA')
            # 9: 사방 회색 0.5mm, 흰 배경 (메타 정보)
            + bf(9, S,'0.5 mm',g, S,'0.5 mm',g, S,'0.5 mm',g, S,'0.5 mm',g, '#FFFFFF')
            + '</hh:borderFills>'
        )

        def font_ref(h=0, l=0):
            return (f'<hh:fontRef hangul="{h}" latin="{l}" hanja="{h}" japanese="{h}" other="{l}" symbol="{l}" user="{l}"/>'
                    '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
                    '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
                    '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
                    '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>')

        def cp(id, height, color, bf_ref=0, bold=0, italic=0):
            b = f' bold="{bold}"' if bold else ''
            it = f' italic="{italic}"' if italic else ''
            return (
                f'<hh:charPr id="{id}" height="{height}" textColor="{color}" '
                f'shadeColor="none" useFontSpace="0" useKerning="0" '
                f'symMark="NONE" borderFillIDRef="{bf_ref}"{b}{it}>'
                + font_ref()
                + '</hh:charPr>'
            )

        char_props = (
            '<hh:charProperties itemCnt="12">'
            + cp(0, 1000, '#212121', 0)           # 0: 본문 10pt
            + cp(1, 1800, '#FFFFFF', 0, bold=1)   # 1: 문서 제목 18pt 흰색 굵게
            + cp(2, 1100, '#1565C0', 0, bold=1)   # 2: 섹션 헤더 11pt 파란 굵게
            + cp(3, 900,  '#FFFFFF', 0, bold=1)   # 3: 표 헤더 9pt 흰색 굵게
            + cp(4, 1600, '#FFFFFF', 0, bold=1)   # 4: KPI 값 16pt 흰색 굵게
            + cp(5, 800,  '#B3D4F5', 0)           # 5: KPI 레이블 8pt 연파랑
            + cp(6, 900,  '#757575', 0)           # 6: 메타/보조 9pt 회색
            + cp(7, 1000, '#212121', 0, bold=1)   # 7: 합계행 10pt 검정 굵게
            + cp(8, 1000, '#1565C0', 0, bold=1)   # 8: 강조 10pt 파랑 굵게
            + cp(9, 800,  '#9E9E9E', 0)           # 9: 주석 8pt 회색
            + cp(10, 1000,'#B3D4F5', 0)           # 10: 타이틀 부제 10pt 연파랑
            + cp(11, 900, '#1565C0', 0, bold=1)   # 11: BLUF 레이블 9pt 파랑 굵게
            + '</hh:charProperties>'
        )

        def pp(id, align='JUSTIFY', ls_val=160, margin_top=0, margin_bot=0, indent=0):
            return (
                f'<hh:paraPr id="{id}" tabPrIDRef="0" condense="0" fontLineHeight="0" '
                f'snapToGrid="1" suppressLineNumbers="0" checked="0">'
                f'<hh:align horizontal="{align}" vertical="BASELINE"/>'
                '<hh:heading type="NONE" idRef="0" level="0"/>'
                '<hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD" '
                'widowOrphan="0" keepWithNext="0" keepLines="0" pageBreakBefore="0" lineWrap="BREAK"/>'
                '<hh:autoSpacing eAsianEng="0" eAsianNum="0"/>'
                '<hh:margin>'
                f'<hc:intent value="{indent}" unit="HWPUNIT"/>'
                '<hc:left value="0" unit="HWPUNIT"/>'
                '<hc:right value="0" unit="HWPUNIT"/>'
                f'<hc:prev value="{margin_top}" unit="HWPUNIT"/>'
                f'<hc:next value="{margin_bot}" unit="HWPUNIT"/>'
                '</hh:margin>'
                f'<hh:lineSpacing type="PERCENT" value="{ls_val}" unit="HWPUNIT"/>'
                '<hh:border><hh:left type="NONE" width="0.1 mm" color="#000000"/>'
                '<hh:right type="NONE" width="0.1 mm" color="#000000"/>'
                '<hh:top type="NONE" width="0.1 mm" color="#000000"/>'
                '<hh:bottom type="NONE" width="0.1 mm" color="#000000"/>'
                '</hh:border>'
                '<hh:tabPr><hh:tabStop pos="8000" type="LEFT" leader="NONE"/></hh:tabPr>'
                '</hh:paraPr>'
            )

        para_props = (
            '<hh:paraProperties itemCnt="4">'
            + pp(0, 'JUSTIFY', 160)       # 0: 기본 왼쪽 160%
            + pp(1, 'CENTER', 160)        # 1: 가운데 160%
            + pp(2, 'LEFT', 130)          # 2: 왼쪽 130% (표 내부)
            + pp(3, 'CENTER', 130)        # 3: 가운데 130% (표 내부)
            + '</hh:paraProperties>'
        )

        font_faces = (
            '<hh:fontfaces itemCnt="2">'
            '<hh:fontface lang="HANGUL" fontCnt="1">'
            '<hh:font id="0" face="맑은 고딕" type="TTF" isEmbedded="0">'
            '<hh:typeInfo familyType="FCAT_GOTHIC" weight="6" proportion="4" '
            'contrast="0" strokeVariation="1" armStyle="1" letterform="1" midline="1" xHeight="1"/>'
            '</hh:font>'
            '</hh:fontface>'
            '<hh:fontface lang="LATIN" fontCnt="1">'
            '<hh:font id="0" face="Arial" type="TTF" isEmbedded="0">'
            '<hh:typeInfo familyType="FCAT_GOTHIC" weight="6" proportion="4" '
            'contrast="0" strokeVariation="1" armStyle="1" letterform="1" midline="1" xHeight="1"/>'
            '</hh:font>'
            '</hh:fontface>'
            '</hh:fontfaces>'
        )

        styles = (
            '<hh:styles itemCnt="1">'
            '<hh:style type="PARA" id="0" name="바탕글" engName="Normal" '
            'paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/>'
            '</hh:styles>'
        )

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hh:head {HWPML_NS} version="1.5" secCnt="1">'
            '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'
            '<hh:refList>'
            + font_faces + border_fills + char_props + para_props + styles +
            '</hh:refList>'
            '<hh:compatibleDocument targetProgram="HWP X 12.0.0.0">'
            '<hh:layoutCompatibility/>'
            '</hh:compatibleDocument>'
            '</hh:head>'
        )

    @staticmethod
    def section_xml(body_content: str) -> str:
        """A4 세로(Portrait), 표준 여백, 섹션 속성 포함"""
        sec_pr = (
            '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" '
            'tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
            'outlineShapeIDRef="0" memoShapeIDRef="0" '
            'textVerticalWidthHead="0" masterPageCnt="0">'
            '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
            '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" '
            'hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
            'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
            '<hp:pagePr landscape="PORTRAIT" width="59528" height="84188" gutterType="LEFT_ONLY">'
            '<hp:margin header="4251" footer="4251" gutter="0" '
            'left="5669" right="5669" top="5669" bottom="4819"/>'
            '</hp:pagePr>'
            '<hp:footNotePr>'
            '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
            '<hp:noteLine length="-1" type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hp:noteSpacing betweenNotes="283" belowLine="567" aboveLine="850"/>'
            '<hp:numbering type="CONTINUOUS" newNum="1"/>'
            '<hp:placement place="EACH_COLUMN" beneathText="0"/>'
            '</hp:footNotePr>'
            '<hp:endNotePr>'
            '<hp:autoNumFormat type="DIGIT" userChar="" prefixChar="" suffixChar=")" supscript="0"/>'
            '<hp:noteLine length="14692344" type="SOLID" width="0.12 mm" color="#000000"/>'
            '<hp:noteSpacing betweenNotes="0" belowLine="567" aboveLine="850"/>'
            '<hp:numbering type="CONTINUOUS" newNum="1"/>'
            '<hp:placement place="END_OF_DOCUMENT" beneathText="0"/>'
            '</hp:endNotePr>'
            '<hp:pageBorderFill type="BOTH" borderFillIDRef="0" textBorder="PAPER" '
            'headerInside="0" footerInside="0" fillArea="PAPER">'
            '<hp:offset left="1417" right="1417" top="1417" bottom="1417"/>'
            '</hp:pageBorderFill>'
            '</hp:secPr>'
        )

        first_para = (
            f'<hp:p id="{nid()}" paraPrIDRef="0" styleIDRef="0" '
            'pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="0">{sec_pr}</hp:run>'
            '</hp:p>'
        )

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hs:sec {HWPML_NS}>'
            + first_para
            + body_content
            + '</hs:sec>'
        )


# ─────────────────────────────────────────────────────────────
# 레이아웃 상수
# ─────────────────────────────────────────────────────────────
# A4 Portrait, 좌우여백 5669 HWPUNIT (약 20mm)
# 내용 너비 = 59528 - 5669×2 = 48190
CONTENT_W = 48190
ROW_H_TITLE = 2000    # 타이틀 행 높이
ROW_H_HEADER = 1100   # 표 헤더 행
ROW_H_DATA = 900      # 데이터 행
ROW_H_KPI = 1800      # KPI 카드 (레이블+값 2줄)
ROW_H_META = 850      # 메타 행
ROW_H_BLUF = 1000     # BLUF 행 기본


# ─────────────────────────────────────────────────────────────
# 단락 생성 헬퍼
# ─────────────────────────────────────────────────────────────
def para(text: str, cp_id: int = 0, pp_id: int = 0) -> str:
    """일반 단락"""
    return (
        f'<hp:p id="{nid()}" paraPrIDRef="{pp_id}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{cp_id}"><hp:t>{xe(text)}</hp:t></hp:run>'
        '</hp:p>'
    )

def empty_para(pp_id: int = 0) -> str:
    """빈 단락 (간격용)"""
    return (
        f'<hp:p id="{nid()}" paraPrIDRef="{pp_id}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="0"><hp:t/></hp:run>'
        '</hp:p>'
    )

def cell_para(text: str, cp_id: int = 0, pp_id: int = 2) -> str:
    """표 셀 내부 단락"""
    return (
        f'<hp:p id="{nid()}" paraPrIDRef="{pp_id}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{cp_id}"><hp:t>{xe(text)}</hp:t></hp:run>'
        '</hp:p>'
    )


# ─────────────────────────────────────────────────────────────
# 표 셀 생성 헬퍼
# ─────────────────────────────────────────────────────────────
def make_cell(
    content_xml: str,
    width: int,
    height: int,
    bf_id: int = 1,
    row_span: int = 1,
    col_span: int = 1,
    row_addr: int = 0,
    col_addr: int = 0,
    v_align: str = 'CENTER',
    margin_lr: int = 200,
    margin_tb: int = 50,
) -> str:
    """표 셀 XML 생성"""
    return (
        f'<hp:tc name="" header="0" hasMargin="0" protect="0" '
        f'editable="0" dirty="0" borderFillIDRef="{bf_id}">'
        f'<hp:subList id="" textDirection="HORIZONTAL" lineWrap="BREAK" '
        f'vertAlign="{v_align}" linkListIDRef="0" linkListNextIDRef="0" '
        'textWidth="0" textHeight="0" hasTextRef="0" hasNumRef="0">'
        + content_xml +
        '</hp:subList>'
        f'<hp:cellAddr colAddr="{col_addr}" rowAddr="{row_addr}"/>'
        f'<hp:cellSpan colSpan="{col_span}" rowSpan="{row_span}"/>'
        f'<hp:cellSz width="{width}" height="{height}"/>'
        f'<hp:cellMargin left="{margin_lr}" right="{margin_lr}" '
        f'top="{margin_tb}" bottom="{margin_tb}"/>'
        '</hp:tc>'
    )


# ─────────────────────────────────────────────────────────────
# 핵심 레이아웃 컴포넌트
# ─────────────────────────────────────────────────────────────
def make_title_block(title: str, subtitle: str = "") -> str:
    """
    전면 타이틀 블록: 진한 파란 배경 (#0D47A1), 흰색 제목, 연파란 부제
    """
    rows_xml = ''
    total_h = 0

    # 제목 행
    title_h = ROW_H_TITLE + (300 if subtitle else 0)
    content = cell_para(title, cp_id=1, pp_id=1)
    rows_xml += (
        f'<hp:tr height="{title_h}" outlineLevel="0" repeatHeader="0" '
        'pageBreak="0" mergeInfo="">'
        + make_cell(content, CONTENT_W, title_h, bf_id=5, margin_lr=300, margin_tb=150)
        + '</hp:tr>'
    )
    total_h += title_h

    # 부제 행 (있는 경우)
    if subtitle:
        sub_h = 700
        sub_content = cell_para(subtitle, cp_id=10, pp_id=1)
        rows_xml += (
            f'<hp:tr height="{sub_h}" outlineLevel="0" repeatHeader="0" '
            'pageBreak="0" mergeInfo="">'
            + make_cell(sub_content, CONTENT_W, sub_h, bf_id=7, margin_lr=300, margin_tb=50)
            + '</hp:tr>'
        )
        total_h += sub_h

    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="{"2" if subtitle else "1"}" colCnt="1" '
        f'cellSpacing="0" borderFillIDRef="0" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{total_h}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + rows_xml + '</hp:tbl>'
    )


def make_meta_table(today: str, reporter: str = "", department: str = "") -> str:
    """
    문서 메타 정보 테이블: 날짜 | 작성자 | 부서
    얇은 회색 테두리, 흰 배경
    """
    items = [f'보고일: {today}']
    if reporter:
        items.append(f'작성: {reporter}')
    if department:
        items.append(f'부서: {department}')
    items.append('[내부용]')

    n = len(items)
    col_w = CONTENT_W // n
    last_w = CONTENT_W - col_w * (n - 1)

    row_xml = f'<hp:tr height="{ROW_H_META}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
    for i, item in enumerate(items):
        w = last_w if i == n - 1 else col_w
        row_xml += make_cell(
            cell_para(item, cp_id=6, pp_id=3 if i == n-1 else 2),
            w, ROW_H_META, bf_id=9, margin_lr=150, margin_tb=30
        )
    row_xml += '</hp:tr>'

    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="1" colCnt="{n}" cellSpacing="0" borderFillIDRef="0" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{ROW_H_META}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )


def make_bluf_box(summary: str, decision: str) -> str:
    """
    핵심 요약 박스 (BLUF): 2행 구조
    레이블 열(연파란 강조) + 내용 열(흰 배경)
    """
    label_w = 5000
    content_w = CONTENT_W - label_w

    rows = [
        ('▶ 보고 요지', summary),
        ('▶ 의사결정 요청', decision),
    ]

    rows_xml = ''
    total_h = 0
    for label, content in rows:
        # 내용 길이에 따라 행 높이 조정
        h = ROW_H_BLUF + max(0, (len(content) // 40) * 400)
        h = min(h, ROW_H_BLUF * 3)  # 최대 3배
        rows_xml += (
            f'<hp:tr height="{h}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
            + make_cell(cell_para(label, cp_id=11, pp_id=2), label_w, h, bf_id=4, margin_lr=150)
            + make_cell(cell_para(content, cp_id=0, pp_id=0), content_w, h, bf_id=1, margin_lr=200)
            + '</hp:tr>'
        )
        total_h += h

    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="{len(rows)}" colCnt="2" cellSpacing="0" borderFillIDRef="4" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{total_h}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + rows_xml + '</hp:tbl>'
    )


def make_kpi_cards(kpis: list) -> str:
    """
    KPI 카드 행: 각 셀에 레이블(연파랑 작은 글씨) + 값(흰색 큰 굵은 글씨)
    파란색 (#1565C0) 배경
    """
    n = len(kpis)
    col_w = CONTENT_W // n
    last_w = CONTENT_W - col_w * (n - 1)

    row_xml = (
        f'<hp:tr height="{ROW_H_KPI}" outlineLevel="0" repeatHeader="0" '
        f'pageBreak="0" mergeInfo="">'
    )
    for i, kpi in enumerate(kpis):
        w = last_w if i == n - 1 else col_w
        # 두 줄: 레이블 + 값
        inner = (
            cell_para(kpi.get('label', ''), cp_id=5, pp_id=3)
            + cell_para(kpi.get('value', ''), cp_id=4, pp_id=3)
        )
        row_xml += make_cell(inner, w, ROW_H_KPI, bf_id=7, margin_lr=150, margin_tb=100)
    row_xml += '</hp:tr>'

    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="1" colCnt="{n}" cellSpacing="2" borderFillIDRef="7" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{ROW_H_KPI}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )


def make_section_header(title: str) -> str:
    """
    섹션 헤더: 두꺼운 파란 LEFT 테두리 + 연회색 배경
    """
    h = ROW_H_HEADER
    row_xml = (
        f'<hp:tr height="{h}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
        + make_cell(
            cell_para(title, cp_id=2, pp_id=0),
            CONTENT_W, h, bf_id=8, margin_lr=250, margin_tb=50
        )
        + '</hp:tr>'
    )
    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="8" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{h}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )


def make_data_table(
    headers: List[str],
    rows: List[List[str]],
    note: Optional[str] = None,
    col_ratios: Optional[List[int]] = None,
) -> str:
    """
    데이터 표:
    - 헤더: 파란 배경, 흰색 굵은
    - 홀수 데이터행: 흰 배경
    - 짝수 데이터행: 연회색 (#F5F5F5)
    - 마지막 행이 '합계'/'계'/'total'로 시작하면: 연보라 배경 + 굵게
    - col_ratios: 열 너비 비율 (예: [3,1,1,1])
    """
    n_cols = len(headers)
    if n_cols == 0:
        return ''

    # 열 너비 계산
    if col_ratios and len(col_ratios) == n_cols:
        total_ratio = sum(col_ratios)
        col_widths = [int(CONTENT_W * r / total_ratio) for r in col_ratios]
        # 나머지 픽셀을 마지막 열에 추가
        col_widths[-1] += CONTENT_W - sum(col_widths)
    else:
        col_w = CONTENT_W // n_cols
        col_widths = [col_w] * (n_cols - 1) + [CONTENT_W - col_w * (n_cols - 1)]

    n_rows = len(rows) + 1  # 헤더 포함
    total_h = ROW_H_HEADER + ROW_H_DATA * len(rows)

    rows_xml = ''

    # 헤더 행
    rows_xml += (
        f'<hp:tr height="{ROW_H_HEADER}" outlineLevel="0" repeatHeader="1" '
        f'pageBreak="0" mergeInfo="">'
    )
    for col_i, (h, w) in enumerate(zip(headers, col_widths)):
        align = 3 if col_i > 0 else 2  # 첫 열 좌측, 나머지 가운데
        rows_xml += make_cell(
            cell_para(h, cp_id=3, pp_id=align),
            w, ROW_H_HEADER, bf_id=2, margin_lr=150, margin_tb=50
        )
    rows_xml += '</hp:tr>'

    # 데이터 행
    for row_i, row in enumerate(rows):
        # 합계 행 감지
        first_val = str(row[0]).strip() if row else ''
        is_total = any(first_val.startswith(kw) for kw in ['합계', '계', 'Total', 'total', '소계'])
        bf = 6 if is_total else (1 if row_i % 2 == 0 else 3)
        cp = 7 if is_total else 0

        rows_xml += (
            f'<hp:tr height="{ROW_H_DATA}" outlineLevel="0" repeatHeader="0" '
            f'pageBreak="0" mergeInfo="">'
        )
        for col_i, (cell_val, w) in enumerate(zip(row, col_widths)):
            align = 3 if col_i > 0 else 2
            rows_xml += make_cell(
                cell_para(str(cell_val), cp_id=cp, pp_id=align),
                w, ROW_H_DATA, bf_id=bf, margin_lr=150, margin_tb=30
            )
        rows_xml += '</hp:tr>'

    result = (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="1" '
        f'rowCnt="{n_rows}" colCnt="{n_cols}" cellSpacing="0" borderFillIDRef="1" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{total_h}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + rows_xml + '</hp:tbl>'
    )

    if note:
        result += para(f'  ※ {note}', cp_id=9, pp_id=0)

    return result


def make_divider() -> str:
    """
    섹션 구분선: 1px 높이의 파란 선 (표로 구현)
    """
    h = 20
    row_xml = (
        f'<hp:tr height="{h}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
        + make_cell(cell_para('', cp_id=0, pp_id=0), CONTENT_W, h, bf_id=2, margin_lr=0, margin_tb=0)
        + '</hp:tr>'
    )
    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="1" colCnt="1" cellSpacing="0" borderFillIDRef="2" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{h}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="200" bottom="200"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )


def make_footer_line(today: str) -> str:
    """
    문서 하단: 구분선 + 기준일 + 기밀 문구
    """
    label_w = 16000
    content_w = CONTENT_W - label_w * 2

    row_xml = (
        f'<hp:tr height="{ROW_H_META}" outlineLevel="0" repeatHeader="0" pageBreak="0" mergeInfo="">'
        + make_cell(cell_para(f'기준일: {today}', cp_id=9, pp_id=2), label_w, ROW_H_META, bf_id=0, margin_lr=0)
        + make_cell(cell_para('', cp_id=9, pp_id=3), content_w, ROW_H_META, bf_id=0, margin_lr=0)
        + make_cell(cell_para('※ 내부용 - 무단 배포 금지', cp_id=9, pp_id=2), label_w, ROW_H_META, bf_id=0, margin_lr=0)
        + '</hp:tr>'
    )
    return (
        f'<hp:tbl id="{nid()}" zOrder="0" numberingType="NONE" '
        f'textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" '
        f'dropcapstyle="None" pageBreak="NONE" repeatHeader="0" '
        f'rowCnt="1" colCnt="3" cellSpacing="0" borderFillIDRef="0" noAdjust="1">'
        f'<hp:sz width="{CONTENT_W}" widthRelTo="ABSOLUTE" height="{ROW_H_META}" '
        'heightRelTo="ABSOLUTE" protect="0"/>'
        '<hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="0" '
        'allowOverlap="0" holdAnchorAndSO="1" vertRelTo="PARA" horzRelTo="PARA" '
        'vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>'
        '<hp:outMargin left="0" right="0" top="0" bottom="0"/>'
        '<hp:inMargin left="0" right="0" top="0" bottom="0"/>'
        + row_xml + '</hp:tbl>'
    )


# ─────────────────────────────────────────────────────────────
# 보고서 본문 빌더
# ─────────────────────────────────────────────────────────────
class ReportBodyBuilder:
    """
    report_data 스키마:
    {
        "domain": "RECRUIT|TRAINING|SALES|BUDGET|PROJECT",
        "summary": str,
        "decision_request": str,
        "kpis": [{"label": str, "value": str}],
        "tables": [
            {
                "title": str,
                "headers": [str, ...],
                "rows": [[str, ...], ...],
                "note": str,         # optional
                "col_ratios": [int], # optional - 열 너비 비율
            }
        ],
        "notes": str,
        "reporter": str,
        "department": str,
    }
    """

    def __init__(self, title: str, report_data: dict):
        self.title = title
        self.data = report_data
        self.today = date.today().strftime('%Y년 %m월 %d일')
        _id_counter[0] = 1000  # 카운터 초기화

    def build(self) -> str:
        b = ''

        # 1. 타이틀 블록
        domain_labels = {
            DOMAIN_RECRUIT: '채용 기획·운영',
            DOMAIN_TRAINING: '교육 훈련·운영',
            DOMAIN_SALES: '영업 실적·계획',
            DOMAIN_BUDGET: '예산 집행 현황',
            DOMAIN_PROJECT: '프로젝트 현황',
        }
        domain = self.data.get('domain', '')
        subtitle = domain_labels.get(domain, '') + f'  |  보고일: {self.today}'
        b += make_title_block(self.title, subtitle)
        b += empty_para()

        # 2. 메타 정보 행
        reporter = self.data.get('reporter', '')
        department = self.data.get('department', '')
        b += make_meta_table(self.today, reporter, department)
        b += empty_para()
        b += empty_para()

        # 3. BLUF 핵심 요약 박스
        b += make_section_header('■ 보고 요지 및 의사결정 요청')
        b += empty_para()
        b += make_bluf_box(
            self.data.get('summary', '[요지 입력 필요]'),
            self.data.get('decision_request', '[요청 사항 입력 필요]')
        )
        b += empty_para()
        b += empty_para()

        # 4. KPI 카드
        kpis = self.data.get('kpis', [])
        if kpis:
            b += make_section_header('■ 핵심 성과 지표 (KPI)')
            b += empty_para()
            b += make_kpi_cards(kpis)
            b += empty_para()
            b += empty_para()

        # 5. 도메인 데이터 표들
        tables = self.data.get('tables', [])
        if tables:
            b += make_section_header('■ 세부 현황')
            b += empty_para()
            for tbl in tables:
                b += para(f'▸ {tbl["title"]}', cp_id=8, pp_id=0)
                b += make_data_table(
                    tbl['headers'],
                    tbl['rows'],
                    tbl.get('note'),
                    tbl.get('col_ratios'),
                )
                b += empty_para()

        # 6. 특이사항 및 건의사항
        notes = self.data.get('notes', '')
        if notes:
            b += make_section_header('■ 특이사항 및 건의사항')
            b += empty_para()
            for line in notes.split('\n'):
                if line.strip():
                    b += para(f'  · {line.strip()}', cp_id=0, pp_id=0)
            b += empty_para()

        # 7. 구분선 + 하단 정보
        b += make_divider()
        b += empty_para()
        b += make_footer_line(self.today)

        return b


# ─────────────────────────────────────────────────────────────
# 메인 생성 함수 (공개 API)
# ─────────────────────────────────────────────────────────────
def create_hwpx_report(file_path: str, title: str, report_data: dict) -> str:
    """
    실무 의사결정용 HWPX 표준 보고서 생성 (v2.0 프리미엄 양식)

    [손상 방지 핵심]
    1. mimetype → ZIP_STORED (zipfile.ZipInfo 기본값)
    2. container.xml → media-type="application/hwpml-package+xml"
    3. 모든 네임스페이스 → 실제 한컴 hwpml/2011/... URI
    4. 텍스트 → xml_escape(xe) 함수로 이스케이프
    5. 섹션 루트 → <hs:sec>
    """
    try:
        file_path = os.path.abspath(file_path)
        parent = os.path.dirname(file_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        xml = HwpxXmlBuilder()
        body = ReportBodyBuilder(title, report_data).build()

        with zipfile.ZipFile(file_path, 'w') as zf:
            # ✅ mimetype: ZIP_STORED (압축 없음, 필수)
            zf.writestr(zipfile.ZipInfo("mimetype"), xml.mimetype())
            # 나머지: ZIP_DEFLATED
            for path, content in [
                ("META-INF/container.xml", xml.container_xml()),
                ("META-INF/manifest.xml",  xml.manifest_xml()),
                ("Contents/content.hpf",   xml.content_hpf(title)),
                ("settings.xml",           xml.settings_xml()),
                ("Contents/header.xml",    xml.header_xml()),
                ("Contents/section0.xml",  xml.section_xml(body)),
            ]:
                zf.writestr(
                    zipfile.ZipInfo(path),
                    content.encode('utf-8'),
                    compress_type=zipfile.ZIP_DEFLATED
                )

        size_kb = max(1, os.path.getsize(file_path) // 1024)
        return f"OK HWPX 보고서 생성 완료\n경로: {file_path}\n크기: {size_kb} KB"

    except Exception as e:
        import traceback
        return f"FAIL 생성 실패: {str(e)}\n{traceback.format_exc()}"


# ─────────────────────────────────────────────────────────────
# 도메인별 샘플 데이터 팩토리
# ─────────────────────────────────────────────────────────────
def make_recruit_sample() -> dict:
    return {
        "domain": DOMAIN_RECRUIT,
        "summary": "2026년 2분기 채용 목표 15명 중 8명 확정 (진행률 53.3%) — 영업직 재공고 필요, 7월 전원 합류 목표",
        "decision_request": "하반기 헤드헌터 추가 계약 및 예산 12,000,000원 추가 집행 승인 요청",
        "reporter": "인사팀 채용담당",
        "department": "인재개발본부",
        "kpis": [
            {"label": "채용 목표 인원",  "value": "15명"},
            {"label": "확정 인원",       "value": "8명"},
            {"label": "진행률",          "value": "53.3%"},
            {"label": "총 예산",         "value": "32,000,000원"},
            {"label": "집행액",          "value": "18,500,000원"},
            {"label": "예산 집행률",     "value": "57.8%"},
        ],
        "tables": [
            {
                "title": "포지션별 채용 현황",
                "headers": ["포지션", "목표", "서류", "면접", "확정", "달성률"],
                "col_ratios": [3, 1, 1, 1, 1, 1],
                "rows": [
                    ["개발 (백엔드)",  "5",  "32",  "8",  "3",  "60.0%"],
                    ["개발 (프론트)", "3",  "18",  "5",  "2",  "66.7%"],
                    ["영업",          "4",  "21",  "6",  "2",  "50.0%"],
                    ["기획·운영",     "3",  "14",  "4",  "1",  "33.3%"],
                    ["합계",          "15", "85", "23",  "8",  "53.3%"],
                ],
                "note": "기준일: 2026-05-30 / 달성률 = 최종확정 ÷ 목표",
            },
            {
                "title": "채용 예산 집행 현황",
                "headers": ["항목", "예산(원)", "집행액(원)", "잔액(원)", "집행률"],
                "col_ratios": [3, 2, 2, 2, 1],
                "rows": [
                    ["채용 플랫폼 광고비",  "8,000,000",  "6,200,000",  "1,800,000",  "77.5%"],
                    ["헤드헌터 수수료",    "15,000,000",  "9,300,000",  "5,700,000",  "62.0%"],
                    ["면접 운영비",         "5,000,000",  "2,100,000",  "2,900,000",  "42.0%"],
                    ["기타 부대비용",       "4,000,000",    "900,000",  "3,100,000",  "22.5%"],
                    ["합계",              "32,000,000", "18,500,000", "13,500,000",  "57.8%"],
                ],
                "note": "금액 단위: 원(KRW) / 집행률 = 집행액 ÷ 예산 × 100",
            },
            {
                "title": "향후 채용 추진 일정",
                "headers": ["단계", "기간", "대상 포지션", "담당", "비고"],
                "col_ratios": [2, 2, 2, 1, 2],
                "rows": [
                    ["서류 접수 마감",      "2026-06-07",    "기획·운영 3명",   "김채용",    "재공고 포함"],
                    ["1차 면접",           "2026-06-14~20", "전 포지션",       "부서장",    "화상·대면 병행"],
                    ["2차 면접 (임원)",    "2026-06-24~25", "최종 후보자",     "인사팀장",  ""],
                    ["처우 협의·합격 통보", "2026-06-28",   "전체",            "인사팀",    ""],
                    ["입사 예정",          "2026-07-01~",   "신규 합류자",     "인사팀",    "온보딩 준비"],
                ],
            },
        ],
        "notes": (
            "영업직 지원자 수 목표 대비 저조 → 재공고 및 헤드헌터 추가 위탁 검토 중\n"
            "하반기 개발 인력 충원 계획(+5명) 수요 조사 완료, 별도 보고 예정\n"
            "채용 리드타임 단축을 위해 서류 합격자 면접 일정 사전 확정 운영 예정"
        ),
    }


def make_training_sample() -> dict:
    return {
        "domain": DOMAIN_TRAINING,
        "summary": "2026년 상반기 필수교육 이수율 78.0% (목표 90% 대비 -12%p) — 법정 미이수자 집중 관리 필요",
        "decision_request": "미이수자 보완 교육 6월 추가 실시 승인 및 예산 750,000원 집행 승인 요청",
        "reporter": "HRD팀 교육담당",
        "department": "인재개발본부",
        "kpis": [
            {"label": "운영 과정 수",    "value": "5개"},
            {"label": "교육 대상",       "value": "127명"},
            {"label": "이수 인원",       "value": "99명"},
            {"label": "전체 이수율",     "value": "78.0%"},
            {"label": "법정 이수율",     "value": "87.9%"},
            {"label": "목표 이수율",     "value": "90.0%"},
        ],
        "tables": [
            {
                "title": "과정별 교육 이수 현황",
                "headers": ["과정명", "구분", "대상", "이수", "미이수", "이수율"],
                "col_ratios": [3, 1, 1, 1, 1, 1],
                "rows": [
                    ["개인정보 보호",        "법정 필수", "127", "118",  "9",  "92.9%"],
                    ["정보보안",             "법정 필수", "127", "115", "12",  "90.6%"],
                    ["직장 내 괴롭힘 방지",  "법정 필수", "127", "102", "25",  "80.3%"],
                    ["리더십 (팀장급)",      "직책 교육",  "23",  "19",  "4",  "82.6%"],
                    ["OA 활용 (엑셀)",       "선택",       "50",  "41",  "9",  "82.0%"],
                    ["합계",                 "",          "127",  "99", "28",  "78.0%"],
                ],
                "note": "기준일: 2026-05-30 / 법정 미이수 시 기업 과태료(최대 500만원) 발생 가능",
            },
            {
                "title": "교육 예산 집행 현황",
                "headers": ["항목", "배정 예산(원)", "집행액(원)", "잔액(원)", "집행률"],
                "col_ratios": [3, 2, 2, 2, 1],
                "rows": [
                    ["외부 강사비",       "3,500,000", "2,200,000", "1,300,000", "62.9%"],
                    ["교재·자료비",         "800,000",   "650,000",   "150,000", "81.3%"],
                    ["장소 임차비",       "1,200,000",   "900,000",   "300,000", "75.0%"],
                    ["온라인 플랫폼 이용료", "500,000",  "450,000",    "50,000", "90.0%"],
                    ["합계",             "6,000,000", "4,200,000", "1,800,000", "70.0%"],
                ],
                "note": "금액 단위: 원(KRW) / 보완 교육 추가 소요 예산: 750,000원",
            },
        ],
        "notes": (
            "직장 내 괴롭힘 방지 미이수 25명 중 18명은 출장·병가 불가피 사유 → 6월 보완 일정 별도 운영 필요\n"
            "법정 교육 이수율 100% 달성 목표: 7월 30일까지 완료 계획\n"
            "하반기 신규 입사자 온보딩 교육 프로그램 설계 진행 중 (7월 오픈 목표)"
        ),
    }


# ─────────────────────────────────────────────────────────────
# CLI 엔트리포인트
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="실무 의사결정용 HWPX 표준 보고서 생성기 v2.0")
    parser.add_argument("--domain", choices=["recruit", "training"], default="recruit")
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    today_str = date.today().strftime('%Y%m%d')
    MAP = {
        "recruit":  (make_recruit_sample,  f"recruit_report_{today_str}.hwpx",  "채용 현황 보고서"),
        "training": (make_training_sample, f"training_report_{today_str}.hwpx", "교육 운영 현황 보고서"),
    }
    factory, default_name, title = MAP[args.domain]
    result = create_hwpx_report(args.output or default_name, title, factory())
    print(result)
