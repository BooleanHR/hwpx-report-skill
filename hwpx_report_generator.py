"""
hwpx_report_generator.py
========================
실무 의사결정용 HWPX 표준 보고서 생성기

채용·교육·영업·예산·프로젝트 도메인에서 경영진 의사결정을 지원하는
구조화된 보고서를 HWPX 형식으로 직접 생성합니다.

HWPX 표준: OWPML (Open Word Processing Markup Language)
기반 구조: ZIP 컨테이너 + XML 내부 파일
참조: https://www.hancom.com/etc/hwpDownload.do

[손상 방지 핵심 규칙]
1. mimetype 파일은 반드시 ZIP_STORED (압축 없음)로 저장
2. container.xml의 media-type은 "application/hwpml-package+xml"
3. 모든 XML 네임스페이스는 실제 한컴 표준 URI를 정확히 사용
4. XML 특수문자(&, <, >, ", ')는 반드시 이스케이프 처리
"""

import os
import zipfile
from datetime import date, datetime
from typing import Optional


# ─────────────────────────────────────────────────────────────
# 도메인 상수 정의
# ─────────────────────────────────────────────────────────────
DOMAIN_RECRUIT  = "RECRUIT"   # 채용 기획·운영
DOMAIN_TRAINING = "TRAINING"  # 교육·훈련 운영
DOMAIN_SALES    = "SALES"     # 영업 실적·계획
DOMAIN_BUDGET   = "BUDGET"    # 예산·집행 현황
DOMAIN_PROJECT  = "PROJECT"   # 프로젝트 현황


# ─────────────────────────────────────────────────────────────
# 공통 XML 네임스페이스 선언 (실제 한컴 표준)
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
# 수치 검증 유틸리티
# ─────────────────────────────────────────────────────────────
def validate_sum(items: list, amount_key: str, declared_total: float) -> tuple:
    """세부 항목 합계와 선언된 합계를 비교 검증한다."""
    calculated = sum(
        float(str(item.get(amount_key, 0)).replace(',', '').replace('₩', '').strip())
        for item in items
    )
    return abs(calculated - declared_total) < 0.01, calculated


def format_number(n: float, unit: str = "원") -> str:
    """숫자를 천 단위 구분자(,)와 단위로 포맷한다."""
    return f"{int(n):,}{unit}"


def format_percentage(numerator: float, denominator: float, decimal: int = 1) -> str:
    """비율을 퍼센트 문자열로 반환한다. 분모가 0이면 'N/A' 반환."""
    if denominator == 0:
        return "N/A"
    return f"{(numerator / denominator * 100):.{decimal}f}%"


def xml_escape(text: str) -> str:
    """XML 특수문자를 이스케이프한다."""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


# ─────────────────────────────────────────────────────────────
# HWPX XML 파일 빌더 (실제 한컴 표준 구조)
# ─────────────────────────────────────────────────────────────
class HwpxXmlBuilder:
    """HWPX 내부 XML 파일들을 한컴 표준에 맞게 생성하는 빌더 클래스."""

    @staticmethod
    def mimetype() -> bytes:
        """mimetype: 반드시 ZIP_STORED로 저장해야 함 (압축 없음)."""
        return b"application/hwp+zip"

    @staticmethod
    def version_xml() -> str:
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        return (f'<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
                f'<hpf:HCFVersion {HWPML_NS} '
                f'tagetApplication="Hancom Office Hangul" major="1" minor="31" micro="0" buildNumber="0"/>')

    @staticmethod
    def container_xml() -> str:
        """
        META-INF/container.xml
        핵심: media-type은 반드시 "application/hwpml-package+xml" (hwp+xml 아님)
        ocf: 접두사 사용
        """
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
        """META-INF/manifest.xml"""
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
        """
        Contents/content.hpf
        실제 한컴 파일과 동일한 네임스페이스 및 opf: 접두사 사용
        """
        now = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
        safe_title = xml_escape(title)
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<opf:package {HWPML_NS} version="" unique-identifier="" id="">'
            '<opf:metadata>'
            f'<opf:title>{safe_title}</opf:title>'
            '<opf:language>ko</opf:language>'
            f'<opf:meta name="CreatedDate" content="text">{now}</opf:meta>'
            f'<opf:meta name="ModifiedDate" content="text">{now}</opf:meta>'
            '</opf:metadata>'
            '<opf:manifest>'
            '<opf:item id="header" href="Contents/header.xml" media-type="application/xml"/>'
            '<opf:item id="section0" href="Contents/section0.xml" media-type="application/xml"/>'
            '<opf:item id="settings" href="settings.xml" media-type="application/xml"/>'
            '</opf:manifest>'
            '<opf:spine>'
            '<opf:itemref idref="section0"/>'
            '</opf:spine>'
            '</opf:package>'
        )

    @staticmethod
    def settings_xml() -> str:
        """settings.xml - 문서 설정"""
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<ha:HWPApplicationSetting {HWPML_NS}>'
            '<ha:CaretPosition section="0" para="0" pos="0"/>'
            '</ha:HWPApplicationSetting>'
        )

    @staticmethod
    def header_xml() -> str:
        """
        Contents/header.xml
        실제 한컴 표준 네임스페이스 + 최소한의 스타일 정의
        - 단락 스타일(paraPr), 글자 스타일(charPr) ID 참조 구조 포함
        - A4 세로 용지, 기본 여백
        """
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hh:head {HWPML_NS} version="1.5" secCnt="1">'

            # 번호 시작
            '<hh:beginNum page="1" footnote="1" endnote="1" pic="1" tbl="1" equation="1"/>'

            '<hh:refList>'

            # 폰트 정의 (한글: 맑은 고딕, 영문/기타: Arial)
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

            # 테두리/채우기 스타일 (ID=0: 기본, ID=1: 표 헤더용)
            '<hh:borderFills itemCnt="2">'
            # ID=0: 기본 (테두리 없음)
            '<hh:borderFill id="0" threeD="0" shadow="0" centerLine="0" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:rightBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:topBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:bottomBorder type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:diagonal type="NONE" width="0.1 mm" color="#000000"/>'
            '<hh:fillBrush><hh:noFill/></hh:fillBrush>'
            '</hh:borderFill>'
            # ID=1: 표 셀용 (얇은 실선)
            '<hh:borderFill id="1" threeD="0" shadow="0" centerLine="0" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="SOLID" width="0.12 mm" color="#888888"/>'
            '<hh:rightBorder type="SOLID" width="0.12 mm" color="#888888"/>'
            '<hh:topBorder type="SOLID" width="0.12 mm" color="#888888"/>'
            '<hh:bottomBorder type="SOLID" width="0.12 mm" color="#888888"/>'
            '<hh:diagonal type="NONE" width="0.12 mm" color="#888888"/>'
            '<hh:fillBrush><hh:noFill/></hh:fillBrush>'
            '</hh:borderFill>'
            # ID=2: 표 헤더 셀용 (진한 파란색 배경)
            '<hh:borderFill id="2" threeD="0" shadow="0" centerLine="0" breakCellSeparateLine="0">'
            '<hh:slash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:backSlash type="NONE" Crooked="0" isCounter="0"/>'
            '<hh:leftBorder type="SOLID" width="0.12 mm" color="#1565C0"/>'
            '<hh:rightBorder type="SOLID" width="0.12 mm" color="#1565C0"/>'
            '<hh:topBorder type="SOLID" width="0.12 mm" color="#1565C0"/>'
            '<hh:bottomBorder type="SOLID" width="0.12 mm" color="#1565C0"/>'
            '<hh:diagonal type="NONE" width="0.12 mm" color="#1565C0"/>'
            '<hh:fillBrush>'
            '<hh:winBrush faceColor="#1565C0" hatchColor="#ffffff" hatchStyle="SOLID"/>'
            '</hh:fillBrush>'
            '</hh:borderFill>'
            '</hh:borderFills>'

            # 글자 스타일 (charPr)
            # ID=0: 기본 본문 (검정, 10pt)
            # ID=1: 제목 (검정, 14pt, 굵게)
            # ID=2: 강조 (파란색, 10pt, 굵게)
            # ID=3: 표 헤더 (흰색, 10pt, 굵게)
            '<hh:charProperties itemCnt="4">'
            '<hh:charProperty id="0" height="1000" textColor="#1A1A1A" '
            'shadeColor="#ffffff" useFontSpace="0" useKerning="0" '
            'symMarkKind="0" borderFillIDRef="0">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charProperty>'
            '<hh:charProperty id="1" height="1400" textColor="#1A1A1A" bold="1" '
            'shadeColor="#ffffff" useFontSpace="0" useKerning="0" '
            'symMarkKind="0" borderFillIDRef="0">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charProperty>'
            '<hh:charProperty id="2" height="1000" textColor="#1565C0" bold="1" '
            'shadeColor="#ffffff" useFontSpace="0" useKerning="0" '
            'symMarkKind="0" borderFillIDRef="0">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charProperty>'
            '<hh:charProperty id="3" height="1000" textColor="#ffffff" bold="1" '
            'shadeColor="#1565C0" useFontSpace="0" useKerning="0" '
            'symMarkKind="0" borderFillIDRef="0">'
            '<hh:fontRef hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:ratio hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:spacing hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '<hh:relSz hangul="100" latin="100" hanja="100" japanese="100" other="100" symbol="100" user="100"/>'
            '<hh:offset hangul="0" latin="0" hanja="0" japanese="0" other="0" symbol="0" user="0"/>'
            '</hh:charProperty>'
            '</hh:charProperties>'

            # 단락 스타일 (paraPr)
            # ID=0: 기본 (왼쪽 정렬, 줄간격 160%)
            # ID=1: 가운데 정렬
            '<hh:paraProperties itemCnt="2">'
            '<hh:paraProperty id="0" tabStopRepeat="8000">'
            '<hh:justify align="JUSTIFY" lastAlign="LEFT"/>'
            '<hh:margins left="0" right="0" prev="0" next="0" indent="0"/>'
            '<hh:lineSpacing type="PERCENT" value="160"/>'
            '</hh:paraProperty>'
            '<hh:paraProperty id="1" tabStopRepeat="8000">'
            '<hh:justify align="CENTER" lastAlign="CENTER"/>'
            '<hh:margins left="0" right="0" prev="0" next="0" indent="0"/>'
            '<hh:lineSpacing type="PERCENT" value="160"/>'
            '</hh:paraProperty>'
            '</hh:paraProperties>'

            # 스타일 목록
            '<hh:styles itemCnt="1">'
            '<hh:style type="PARA" id="0" name="바탕글" engName="Normal" '
            'paraPrIDRef="0" charPrIDRef="0" nextStyleIDRef="0" langID="1042" lockForm="0"/>'
            '</hh:styles>'

            '</hh:refList>'

            # 구역(섹션) 페이지 정보를 head 아래 mappingTable로 선언
            '<hh:compatibleDocument targetProgram="HWP X 12.0.0.0">'
            '<hh:layoutCompatibility/>'
            '</hh:compatibleDocument>'

            '</hh:head>'
        )

    @staticmethod
    def section_xml(body_content: str) -> str:
        """
        Contents/section0.xml
        실제 한컴 표준: hs:sec 루트 태그 + 공통 네임스페이스
        첫 번째 단락에 섹션 속성(hp:secPr) 포함 - A4 세로, 표준 여백
        """
        # A4 세로: width=59528, height=84188 (HWPUNIT)
        # 여백: 상하좌우 각 4251, 머리말/꼬리말 4251
        sec_pr = (
            '<hp:secPr id="" textDirection="HORIZONTAL" spaceColumns="1134" '
            'tabStop="8000" tabStopVal="4000" tabStopUnit="HWPUNIT" '
            'outlineShapeIDRef="1" memoShapeIDRef="1" '
            'textVerticalWidthHead="0" masterPageCnt="0">'
            '<hp:grid lineGrid="0" charGrid="0" wonggojiFormat="0"/>'
            '<hp:startNum pageStartsOn="BOTH" page="0" pic="0" tbl="0" equation="0"/>'
            '<hp:visibility hideFirstHeader="0" hideFirstFooter="0" '
            'hideFirstMasterPage="0" border="SHOW_ALL" fill="SHOW_ALL" '
            'hideFirstPageNum="0" hideFirstEmptyLine="0" showLineNumber="0"/>'
            '<hp:lineNumberShape restartType="0" countBy="0" distance="0" startNumber="0"/>'
            '<hp:pagePr landscape="PORTRAIT" width="59528" height="84188" gutterType="LEFT_ONLY">'
            '<hp:margin header="4251" footer="4251" gutter="0" '
            'left="6236" right="6236" top="5669" bottom="4819"/>'
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

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
            f'<hs:sec {HWPML_NS}>'
            f'<hp:p id="1" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="0">{sec_pr}</hp:run>'
            '</hp:p>'
            f'{body_content}'
            '</hs:sec>'
        )


# ─────────────────────────────────────────────────────────────
# 단락 및 표 XML 생성 헬퍼
# ─────────────────────────────────────────────────────────────
_para_id_counter = [100]  # 전역 ID 카운터 (리스트로 감싸서 mutable하게 사용)


def _next_id() -> int:
    _para_id_counter[0] += 1
    return _para_id_counter[0]


def make_paragraph(text: str, char_pr: int = 0, para_pr: int = 0) -> str:
    """
    단락(paragraph) XML 생성.
    char_pr: 0=기본, 1=제목(굵게14pt), 2=강조(파랑굵게), 3=표헤더(흰색굵게)
    """
    safe = xml_escape(text)
    pid = _next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="{para_pr}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        f'<hp:run charPrIDRef="{char_pr}">'
        f'<hp:t>{safe}</hp:t>'
        '</hp:run>'
        '</hp:p>'
    )


def make_empty_paragraph() -> str:
    """빈 단락(줄 간격용)"""
    pid = _next_id()
    return (
        f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">'
        '<hp:run charPrIDRef="0"><hp:t/></hp:run>'
        '</hp:p>'
    )


def make_table(headers: list, rows: list, note: Optional[str] = None) -> str:
    """
    표(table) XML 생성.
    - 헤더 행: 파란색 배경(borderFillIDRef=2), 흰색 굵은 텍스트(charPrIDRef=3)
    - 데이터 행: 기본 셀 테두리(borderFillIDRef=1)
    - 열 너비: 용지 폭에 균등 분배 (A4 내용폭 ≈ 47056 HWPUNIT)
    """
    col_count = len(headers)
    if col_count == 0:
        return ''

    # A4 표준 여백 기준 내용 너비: 59528 - 6236*2 = 47056 HWPUNIT
    content_width = 47056
    col_width = content_width // col_count
    row_height = 850   # 기본 행 높이 (HWPUNIT)
    header_height = 1000

    def cell(text: str, bf_id: int, cp_id: int, height: int) -> str:
        pid = _next_id()
        safe_text = xml_escape(text)
        return (
            f'<hp:tc name="" header="0" hasMargin="0" protect="0" editable="0" dirty="0" borderFillIDRef="{bf_id}">'
            f'<hp:cellAddr rowAddr="0" colAddr="0"/>'
            f'<hp:cellSpan rowSpan="1" colSpan="1"/>'
            f'<hp:cellSz width="{col_width}" height="{height}"/>'
            f'<hp:cellMargin left="141" right="141" top="0" bottom="0"/>'
            f'<hp:p id="{pid}" paraPrIDRef="0" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">'
            f'<hp:run charPrIDRef="{cp_id}"><hp:t>{safe_text}</hp:t></hp:run>'
            f'</hp:p>'
            f'</hp:tc>'
        )

    total_rows = len(rows) + 1  # 헤더 포함
    tbl = (
        f'<hp:tbl id="{_next_id()}" numRowAtRef="{total_rows}" numColAtRef="{col_count}" '
        f'cellSpacing="0" inMargin="0" protect="0" borderFillIDRef="1">'
        f'<hp:sz width="{content_width}" height="{header_height + row_height * len(rows)}"/>'
    )

    # 헤더 행
    tbl += f'<hp:tr height="{header_height}" outlineLevel="0" repeatHeader="1" pageBreak="1" mergeInfo="">'
    for h in headers:
        tbl += cell(str(h), 2, 3, header_height)  # 파란 배경, 흰색 굵은 글씨
    tbl += '</hp:tr>'

    # 데이터 행
    for row in rows:
        tbl += f'<hp:tr height="{row_height}" outlineLevel="0" repeatHeader="0" pageBreak="1" mergeInfo="">'
        for c_val in row:
            tbl += cell(str(c_val), 1, 0, row_height)  # 기본 셀 테두리, 기본 글씨
        tbl += '</hp:tr>'

    tbl += '</hp:tbl>'

    result = tbl
    if note:
        result += make_paragraph(f'※ {note}', char_pr=0)
    return result


# ─────────────────────────────────────────────────────────────
# 보고서 본문 빌더
# ─────────────────────────────────────────────────────────────
class ReportBodyBuilder:
    """
    도메인별 보고서 본문 XML을 생성하는 빌더.

    report_data 스키마:
    {
        "domain": "RECRUIT|TRAINING|SALES|BUDGET|PROJECT",
        "summary": "보고 요지 한 줄",
        "decision_request": "의사결정 요청 사항",
        "kpis": [{"label": str, "value": str}],   # 4~6개 권장
        "tables": [
            {
                "title": str,
                "headers": [str, ...],
                "rows": [[str, ...], ...],
                "note": str  # optional
            }
        ],
        "notes": "특이사항 및 건의사항",
        "reporter": "작성자명 (optional)",
        "department": "부서명 (optional)"
    }
    """

    def __init__(self, title: str, report_data: dict):
        self.title = title
        self.data = report_data
        self.today = date.today().strftime('%Y년 %m월 %d일')
        # ID 카운터 초기화
        _para_id_counter[0] = 100

    def build(self) -> str:
        body = ''

        # ── 1. 문서 헤더 ──────────────────────────────────────────
        body += make_paragraph(f'■ {self.title}', char_pr=1, para_pr=1)  # 제목, 가운데

        reporter_parts = [f'보고일: {self.today}']
        if self.data.get('reporter'):
            reporter_parts.append(f'작성: {self.data["reporter"]}')
        if self.data.get('department'):
            reporter_parts.append(f'부서: {self.data["department"]}')
        body += make_paragraph('  |  '.join(reporter_parts), char_pr=0)
        body += make_empty_paragraph()

        # ── 2. BLUF 핵심 요약 블록 ───────────────────────────────
        body += make_paragraph('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', char_pr=2)
        body += make_paragraph(f'▶ 보고 요지: {self.data.get("summary", "")}', char_pr=0)
        body += make_paragraph(f'▶ 의사결정 요청: {self.data.get("decision_request", "")}', char_pr=2)
        body += make_paragraph('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', char_pr=2)
        body += make_empty_paragraph()

        # ── 3. KPI 요약표 ────────────────────────────────────────
        kpis = self.data.get('kpis', [])
        if kpis:
            body += make_paragraph('[핵심 지표 요약 (Key Performance Indicators)]', char_pr=1)
            body += make_table(
                [k['label'] for k in kpis],
                [[k['value'] for k in kpis]]
            )
            body += make_empty_paragraph()

        # ── 4. 도메인 표들 ───────────────────────────────────────
        for tbl in self.data.get('tables', []):
            body += make_paragraph(f'[{tbl["title"]}]', char_pr=1)
            body += make_table(tbl['headers'], tbl['rows'], tbl.get('note'))
            body += make_empty_paragraph()

        # ── 5. 특이사항 ──────────────────────────────────────────
        if self.data.get('notes'):
            body += make_paragraph('■ 특이사항 및 건의사항', char_pr=1)
            for line in self.data['notes'].split('\n'):
                if line.strip():
                    body += make_paragraph(f'  · {line.strip()}', char_pr=0)
            body += make_empty_paragraph()

        # ── 6. 문서 하단 ──────────────────────────────────────────
        body += make_paragraph('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━', char_pr=2)
        body += make_paragraph(f'※ 본 보고서는 {self.today} 기준으로 작성되었습니다.', char_pr=0)
        body += make_paragraph('※ 수치는 내부 데이터 기준이며, 외부 공개를 금합니다.', char_pr=0)

        return body


# ─────────────────────────────────────────────────────────────
# 메인 생성 함수 (공개 API)
# ─────────────────────────────────────────────────────────────
def create_hwpx_report(
    file_path: str,
    title: str,
    report_data: dict
) -> str:
    """
    실무 의사결정용 HWPX 표준 보고서를 생성한다.

    [핵심 손상 방지 규칙]
    1. mimetype → ZIP_STORED (압축 없음, 필수)
    2. 나머지 파일 → ZIP_DEFLATED (압축)
    3. container.xml media-type → "application/hwpml-package+xml"
    4. 모든 네임스페이스는 실제 한컴 표준 URI 사용
    5. XML 특수문자 반드시 이스케이프

    Args:
        file_path: 저장할 .hwpx 파일의 절대 경로
        title: 보고서 제목
        report_data: 보고서 데이터 딕셔너리 (ReportBodyBuilder 스키마 참조)

    Returns:
        str: 성공/실패 메시지
    """
    try:
        file_path = os.path.abspath(file_path)
        parent_dir = os.path.dirname(file_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

        xml = HwpxXmlBuilder()
        body = ReportBodyBuilder(title, report_data).build()

        with zipfile.ZipFile(file_path, 'w') as zf:
            # ✅ 규칙 1: mimetype은 반드시 ZIP_STORED (압축 없음)
            zf.writestr(
                zipfile.ZipInfo("mimetype"),  # compress_type 기본값 = STORED
                xml.mimetype()
            )
            # 나머지는 ZIP_DEFLATED (압축)
            zf.writestr(
                zipfile.ZipInfo("version.xml"),
                xml.version_xml().encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("META-INF/container.xml"),
                xml.container_xml().encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("META-INF/manifest.xml"),
                xml.manifest_xml().encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("Contents/content.hpf"),
                xml.content_hpf(title).encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("settings.xml"),
                xml.settings_xml().encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("Contents/header.xml"),
                xml.header_xml().encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )
            zf.writestr(
                zipfile.ZipInfo("Contents/section0.xml"),
                xml.section_xml(body).encode('utf-8'),
                compress_type=zipfile.ZIP_DEFLATED
            )

        size_kb = os.path.getsize(file_path) // 1024 or 1
        return f"OK HWPX 보고서 생성 완료\n경로: {file_path}\n크기: {size_kb} KB"

    except Exception as e:
        import traceback
        return f"FAIL HWPX 생성 실패: {str(e)}\n{traceback.format_exc()}"


# ─────────────────────────────────────────────────────────────
# 도메인별 샘플 데이터 팩토리
# ─────────────────────────────────────────────────────────────
def make_recruit_sample() -> dict:
    """채용 현황 보고서 샘플 데이터."""
    return {
        "domain": DOMAIN_RECRUIT,
        "summary": "2026년 2분기 채용 목표 15명 중 8명 확정, 진행률 53.3%",
        "decision_request": "하반기 추가 채용 예산 1,200만원 승인 요청",
        "reporter": "인사팀 채용담당",
        "kpis": [
            {"label": "채용 목표",  "value": "15명"},
            {"label": "확정 인원",  "value": "8명"},
            {"label": "진행률",     "value": "53.3%"},
            {"label": "총 예산",    "value": "32,000,000원"},
            {"label": "집행액",     "value": "18,500,000원"},
            {"label": "잔액",       "value": "13,500,000원"},
        ],
        "tables": [
            {
                "title": "포지션별 채용 현황",
                "headers": ["포지션", "목표", "서류", "면접", "확정", "달성률"],
                "rows": [
                    ["개발(백엔드)", "5", "32", "8", "3", "60.0%"],
                    ["개발(프론트)", "3", "18", "5", "2", "66.7%"],
                    ["영업",        "4", "21", "6", "2", "50.0%"],
                    ["기획/운영",   "3", "14", "4", "1", "33.3%"],
                    ["합계",        "15", "85", "23", "8", "53.3%"],
                ],
                "note": "기준일: 2026-05-30 / 달성률 = 최종확정 ÷ 목표"
            },
            {
                "title": "채용 비용 내역",
                "headers": ["항목", "예산(원)", "집행액(원)", "잔액(원)", "집행률"],
                "rows": [
                    ["채용 플랫폼 광고비", "8,000,000", "6,200,000", "1,800,000", "77.5%"],
                    ["헤드헌터 수수료",    "15,000,000", "9,300,000", "5,700,000", "62.0%"],
                    ["면접 운영비",        "5,000,000", "2,100,000", "2,900,000", "42.0%"],
                    ["기타 부대비용",      "4,000,000",   "900,000", "3,100,000", "22.5%"],
                    ["합계",             "32,000,000", "18,500,000", "13,500,000", "57.8%"],
                ],
                "note": "금액 단위: 원(KRW) / 집행률 = 집행액 ÷ 예산 x 100"
            },
            {
                "title": "향후 채용 일정",
                "headers": ["단계", "기간", "대상", "담당", "비고"],
                "rows": [
                    ["서류 접수 마감",   "2026-06-07", "기획/운영 3명", "김채용",   "재공고 포함"],
                    ["1차 면접",        "2026-06-14~20", "전 포지션", "부서장",   "화상/대면 병행"],
                    ["2차 면접(임원)",  "2026-06-24~25", "최종 후보자", "인사팀장", ""],
                    ["합격 통보",       "2026-06-28", "전체",       "인사팀",   ""],
                    ["입사 예정",       "2026-07-01~", "신규 합류자", "인사팀",   "온보딩 준비"],
                ],
            }
        ],
        "notes": (
            "영업직 지원자 수가 목표 대비 저조하여 재공고 및 헤드헌터 추가 위탁 검토 중\n"
            "하반기 개발 인력 충원 계획(+5명) 수요 조사 완료, 별도 보고 예정"
        )
    }


def make_training_sample() -> dict:
    """교육 운영 보고서 샘플 데이터."""
    return {
        "domain": DOMAIN_TRAINING,
        "summary": "상반기 필수교육 이수율 78.0%, 목표(90%) 대비 12%p 미달 - 보완 조치 필요",
        "decision_request": "미이수자 보완 교육 일정 승인 및 추가 예산 750,000원 승인 요청",
        "kpis": [
            {"label": "교육 과정 수", "value": "5개"},
            {"label": "대상 인원",   "value": "127명"},
            {"label": "이수 인원",   "value": "99명"},
            {"label": "이수율",      "value": "78.0%"},
            {"label": "예산 집행률", "value": "64.2%"},
            {"label": "목표 이수율", "value": "90.0%"},
        ],
        "tables": [
            {
                "title": "과정별 교육 이수 현황",
                "headers": ["과정명", "대상", "이수", "미이수", "이수율", "비고"],
                "rows": [
                    ["개인정보보호",     "127", "118", "9",  "92.9%", "법정 필수"],
                    ["정보보안",        "127", "115", "12", "90.6%", "법정 필수"],
                    ["직장내 괴롭힘 방지", "127", "102", "25", "80.3%", "법정 필수"],
                    ["리더십(팀장급)", "23",  "19",  "4",  "82.6%", "대상 한정"],
                    ["OA 활용(엑셀)", "50",  "41",  "9",  "82.0%", "선택"],
                    ["합계",           "127", "99",  "28", "78.0%", ""],
                ],
                "note": "기준일: 2026-05-30 / 법정 필수교육 미이수 시 과태료 발생 가능"
            }
        ],
        "notes": (
            "직장내 괴롭힘 방지 교육 미이수자 25명 중 18명은 출장·병가 사유 - 6월 보완 일정 필요\n"
            "법정 필수교육 이수율 100% 달성 목표, 7월 30일까지 완료 계획"
        )
    }


# ─────────────────────────────────────────────────────────────
# CLI 실행 엔트리포인트
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(
        description="실무 의사결정용 HWPX 표준 보고서 생성기"
    )
    parser.add_argument(
        "--domain",
        choices=["recruit", "training"],
        default="recruit",
        help="보고서 도메인 (기본값: recruit)"
    )
    parser.add_argument(
        "--output",
        default="",
        help="출력 파일 경로 (기본: 도메인_보고서_YYYYMMDD.hwpx)"
    )
    args = parser.parse_args()

    today_str = date.today().strftime('%Y%m%d')
    domain_map = {
        "recruit":  (make_recruit_sample,  f"recruit_report_{today_str}.hwpx",  "채용 현황 보고서"),
        "training": (make_training_sample, f"training_report_{today_str}.hwpx", "교육 운영 현황 보고서"),
    }

    factory, default_filename, title = domain_map[args.domain]
    output_path = args.output or default_filename
    result = create_hwpx_report(output_path, title, factory())
    print(result)
