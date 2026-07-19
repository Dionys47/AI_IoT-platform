import sys
sys.stdout.reconfigure(encoding='utf-8')
print("=" * 120)
print("DOCX STRUCTURE COMPARISON SCRIPT")
print("=" * 120)
print()

import docx
from docx import Document
from docx.shared import Pt, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
import re

TEMPLATE_PATH = r"C:\Users\USER\Documents\AI_Platform\Diploma Template.docx"
MSIOT_PATH = r"C:\Users\USER\Documents\AI_Platform\msIoT.docx"

def get_paragraph_info(p, index):
    text = p.text
    bold = False
    italic = False
    font_sizes = []
    font_names = []
    for r in p.runs:
        if r.bold:
            bold = True
        if r.italic:
            italic = True
        if r.font.size:
            font_sizes.append(r.font.size)
        if r.font.name:
            font_names.append(r.font.name)
    style_name = p.style.name if p.style else ""
    font_size_pt = None
    if font_sizes:
        font_size_pt = font_sizes[0].pt
    elif p.style and p.style.font and p.style.font.size:
        font_size_pt = p.style.font.size.pt
    align = p.alignment
    align_str = ""
    if align == WD_ALIGN_PARAGRAPH.LEFT: align_str = "LEFT"
    elif align == WD_ALIGN_PARAGRAPH.CENTER: align_str = "CENTER"
    elif align == WD_ALIGN_PARAGRAPH.RIGHT: align_str = "RIGHT"
    elif align == WD_ALIGN_PARAGRAPH.JUSTIFY: align_str = "JUSTIFY"
    else: align_str = "INHERITED"

    is_heading = False
    heading_level = None
    if style_name and 'Heading' in style_name:
        is_heading = True
        m = re.search(r'Heading\s*(\d+)', style_name)
        if m: heading_level = int(m.group(1))
        else: heading_level = 0
    if not is_heading and bold and font_size_pt and font_size_pt >= 12:
        is_heading = True
        heading_level = -1

    numId = None
    ilvl = None
    try:
        ns = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
        pPr = p._p.find(ns + 'pPr')
        if pPr is not None:
            numPr = pPr.find(ns + 'numPr')
            if numPr is not None:
                numId_el = numPr.find(ns + 'numId')
                ilvl_el = numPr.find(ns + 'ilvl')
                if numId_el is not None: numId = numId_el.get(ns + 'val')
                if ilvl_el is not None: ilvl = ilvl_el.get(ns + 'val')
    except:
        pass

    return {
        'index': index, 'text': text, 'text_preview': text[:120] if len(text) > 120 else text,
        'style_name': style_name, 'bold': bold, 'italic': italic,
        'font_size_pt': font_size_pt, 'font_names': font_names,
        'alignment': align_str, 'is_heading': is_heading, 'heading_level': heading_level,
        'numId': numId, 'ilvl': ilvl, 'runs_count': len(p.runs),
    }

def extract_full_structure(filepath, label):
    print(f"\n{'#' * 120}")
    print(f"# EXTRACTING: {label}")
    print(f"# FILE: {filepath}")
    print(f"{'#' * 120}\n")
    doc = Document(filepath)
    all_paragraphs = []
    heading_paragraphs = []
    empty_count = 0
    nonempty_count = 0
    for i, p in enumerate(doc.paragraphs):
        info = get_paragraph_info(p, i)
        all_paragraphs.append(info)
        if info['is_heading'] and info['text'].strip():
            heading_paragraphs.append(info)
        if info['text'].strip(): nonempty_count += 1
        else: empty_count += 1

    print(f"Total paragraphs: {len(all_paragraphs)}")
    print(f"  Non-empty: {nonempty_count}")
    print(f"  Empty: {empty_count}")
    print(f"  Detected headings: {len(heading_paragraphs)}\n")

    print(f"{'─' * 120}")
    print(f"COMPLETE PARAGRAPH LISTING")
    print(f"{'─' * 120}\n")

    for info in all_paragraphs:
        marker = "  "
        if info['is_heading']:
            marker = f"H{info['heading_level']}" if info['heading_level'] and info['heading_level'] > 0 else "H?"
        elif info['style_name'] and 'List' in info['style_name']:
            marker = "L "
        bullet = ""
        if info['numId'] is not None:
            bullet = f"[numId={info['numId']},lv={info['ilvl']}]"
        size_str = f"{info['font_size_pt']:.1f}pt" if info['font_size_pt'] else "inherit"
        style_str = info['style_name'] if info['style_name'] else "None"
        idx_str = f"{info['index']:4d}"
        marker_str = f"{marker:3s}"
        sz_str = f"{size_str:>10s}"
        al_str = f"{info['alignment']:8s}"
        bold_str = "B" if info['bold'] else " "
        italic_str = "I" if info['italic'] else " "
        st_str = f"{style_str:25s}"
        text_display = info['text_preview'].replace('\n', '\\n')
        print(f"{idx_str} {marker_str} {bold_str}{italic_str} {sz_str} {al_str} {st_str} {bullet} {text_display}")

    print()
    print(f"{'─' * 120}")
    print(f"ALL HEADINGS / STRUCTURAL OUTLINE")
    print(f"{'─' * 120}\n")

    for info in heading_paragraphs:
        level = info['heading_level'] if info['heading_level'] else 0
        indent = "  " * max(0, level - 1) if level > 0 else ""
        if level == -1: indent = "[?] "
        size_str = f"{info['font_size_pt']:.1f}pt" if info['font_size_pt'] else "inherit"
        print(f"  {indent}{info['text'].strip()}  [{info['style_name']}, {size_str}]")

    print()
    print(f"{'─' * 120}")
    print(f"HIERARCHICAL OUTLINE")
    print(f"{'─' * 120}\n")

    outline_tree = []
    for info in all_paragraphs:
        if info['is_heading'] and info['text'].strip():
            level = info['heading_level'] if info['heading_level'] and info['heading_level'] > 0 else 1
            outline_tree.append((level, info['text'].strip(), info['style_name'], info['font_size_pt']))

    current_levels = {}
    for level, text, style, fsize in outline_tree:
        current_levels[level] = text
        for l in list(current_levels.keys()):
            if l > level: del current_levels[l]
        indent = "  " * (level - 1) if level > 1 else ""
        sz = f" ({fsize:.0f}pt)" if fsize else ""
        print(f"  {indent}{text}{sz}")

    print(f"\n{'-' * 120}")
    print(f"END OF {label}")
    print(f"{'-' * 120}\n")
    return all_paragraphs, heading_paragraphs, outline_tree

template_all, template_headings, template_outline = extract_full_structure(TEMPLATE_PATH, "TEMPLATE: Diploma Template.docx")
msiot_all, msiot_headings, msiot_outline = extract_full_structure(MSIOT_PATH, "THESIS: msIoT.docx")

print("\n" + "=" * 120)
print("=" * 120)
print("STRUCTURED COMPARISON")
print("=" * 120)
print("=" * 120)

print("\n" + "=" * 90)
print("A. TEMPLATE CHAPTER STRUCTURE (Complete Outline)")
print("=" * 90)
for level, text, style, fsize in template_outline:
    indent = "  " * (level - 1) if level > 1 else ""
    sz = f" ({fsize:.0f}pt)" if fsize else ""
    print(f"  {indent}{text}{sz}")

print("\n" + "=" * 90)
print("B. msIOT CHAPTER STRUCTURE (Complete Outline)")
print("=" * 90)
for level, text, style, fsize in msiot_outline:
    indent = "  " * (level - 1) if level > 1 else ""
    sz = f" ({fsize:.0f}pt)" if fsize else ""
    print(f"  {indent}{text}{sz}")

def norm(t):
    t = t.strip()
    t = re.sub(r'\s+', ' ', t)
    t = t.lower()
    t = re.sub(r'^(kapitulli\s+)?\d+(\.\d+)*\s*[\.\)\s]*\s*', '', t).strip()
    return t

msiot_norm_headings = set()
for _, text, _, _ in msiot_outline:
    msiot_norm_headings.add(norm(text))

template_headings_text = [(level, text, style, fsize) for level, text, style, fsize in template_outline]
missing_items = []
found_items = []
for level, text, style, fsize in template_headings_text:
    n = norm(text)
    found = False
    for mt in msiot_norm_headings:
        if n == mt or mt.startswith(n) or n.startswith(mt):
            if len(n) > 5 and len(mt) > 5:
                if n in mt or mt in n: found = True; break
            elif n == mt: found = True; break
        words_n = set(n.split())
        words_mt = set(mt.split())
        common = words_n & words_mt
        if len(common) >= 2 and len(common) >= min(len(words_n), len(words_mt)) * 0.5:
            found = True; break
    if found:
        found_items.append((level, text, style, fsize))
    else:
        missing_items.append((level, text, style, fsize))

print("\n" + "=" * 90)
print("C. MISSING ELEMENTS - Template headings NOT found in msIoT")
print("=" * 90)
if missing_items:
    print(f"\nTemplate has {len(template_headings_text)} structural elements, msIoT has {len(msiot_outline)}.")
    print(f"Elements FOUND in msIoT: {len(found_items)}")
    print(f"Elements MISSING in msIoT: {len(missing_items)}\n")
    current_chapter = "(Preamble)"
    for level, text, style, fsize in template_headings_text:
        if level == 1: current_chapter = text
        if (level, text, style, fsize) in missing_items:
            indent = "  " * (level - 1) if level > 1 else ""
            sz = f" ({fsize:.0f}pt)" if fsize else ""
            print(f"  [MISSING] {indent}{text}{sz}  [under chapter: {current_chapter}]")
else:
    print("\nAll template structural elements appear to be present in msIoT!")

print("\n" + "=" * 90)
print("D. EXTRA ELEMENTS in msIoT NOT found in Template")
print("=" * 90)
template_norm_headings = set()
for _, text, _, _ in template_outline:
    template_norm_headings.add(norm(text))
extra_items = []
for level, text, style, fsize in msiot_outline:
    n = norm(text)
    found = False
    for tt in template_norm_headings:
        if n == tt or tt.startswith(n) or n.startswith(tt):
            if len(n) > 5 and len(tt) > 5:
                if n in tt or tt in n: found = True; break
            elif n == tt: found = True; break
        words_n = set(n.split())
        words_tt = set(tt.split())
        common = words_n & words_tt
        if len(common) >= 2 and len(common) >= min(len(words_n), len(words_tt)) * 0.5:
            found = True; break
    if not found:
        extra_items.append((level, text, style, fsize))
if extra_items:
    print(f"\nExtra elements in msIoT: {len(extra_items)}")
    for level, text, style, fsize in msiot_outline:
        if (level, text, style, fsize) in extra_items:
            indent = "  " * (level - 1) if level > 1 else ""
            sz = f" ({fsize:.0f}pt)" if fsize else ""
            print(f"  [EXTRA] {indent}{text}{sz}")
else:
    print("\nNo extra structural elements found in msIoT (compared to template).")

print("\n" + "=" * 90)
print("E. DETAILED PARAGRAPH COMPARISON")
print("=" * 90)
print("\n--- Font/style comparison for matched headings ---\n")
matched = 0
for tlvl, ttext, tstyle, tfsize in template_headings_text:
    n = norm(ttext)
    for mlvl, mtext, mstyle, mfsize in msiot_outline:
        mn = norm(mtext)
        if n == mn or (len(n) > 5 and len(mn) > 5 and (n in mn or mn in n)):
            tsz = f"{tfsize:.0f}pt" if tfsize else "inherit"
            msz = f"{mfsize:.0f}pt" if mfsize else "inherit"
            if tfsize != mfsize or tstyle != mstyle:
                print(f"  [{ttext}]")
                print(f"    Template: style={tstyle}, size={tsz}")
                print(f"    msIoT:    style={mstyle}, size={msz}")
                matched += 1
            break
if matched == 0:
    print("  (All matched headings have consistent formatting)")

print("\n" + "=" * 90)
print("F. STANDARD THESIS SECTION CHECKLIST")
print("=" * 90)
standard_sections = [
    ("Abstract (English)", ["abstract"]),
    ("Abstrakt (Albanian)", ["abstrakt", "permbledhje"]),
    ("Table of Contents", ["table of contents", "permbajtja", "contents"]),
    ("List of Figures", ["list of figures", "lista e figurave"]),
    ("List of Tables", ["list of tables", "lista e tabelave"]),
    ("List of Abbreviations", ["list of abbreviations", "shkurtesave", "abbreviations"]),
    ("Acknowledgements", ["acknowledgements", "falenderime", "mirenjohje"]),
    ("Introduction chapter", ["introduction", "hyrje"]),
    ("Literature Review / Related Work", ["literature review", "related work", "literatura"]),
    ("Methodology", ["methodology", "metodologjia"]),
    ("Implementation / System Design", ["implementation", "system design", "zbatimi", "dizajni"]),
    ("Results / Evaluation", ["results", "evaluation", "experimental", "rezultatet"]),
    ("Discussion", ["discussion", "diskutimi"]),
    ("Conclusion", ["conclusion", "perfundimi", "conclusions"]),
    ("Recommendations", ["recommendations", "rekomandimet"]),
    ("References / Bibliography", ["references", "bibliography", "bibliografi", "referencat"]),
    ("Appendices", ["appendices", "appendix", "shtojca", "shtojcat"]),
    ("Declaration / Statement", ["declaration", "statement", "deklarate", "deklarata"]),
]
print(f"\n  {'Section':42s} {'Template':12s} {'msIoT':12s}")
print(f"  {'-' * 66}")
for sec_name, keywords in standard_sections:
    in_template = any(any(kw in ht for kw in keywords) for ht in [t.lower() for _, t, _, _ in template_outline])
    in_msiot = any(any(kw in ht for kw in keywords) for ht in [t.lower() for _, t, _, _ in msiot_outline])
    t_status = "YES" if in_template else "no"
    m_status = "YES" if in_msiot else "no"
    if in_template and not in_msiot: m_status = ">> MISSING <<"
    t_display = f"[{t_status}]"
    m_display = f"[{m_status}]"
    print(f"  {sec_name:42s} {t_display:12s} {m_display:12s}")

print("\n" + "=" * 90)
print("G. SUMMARY OF GAPS")
print("=" * 90)
print(f"""
Files compared:
  Template: {TEMPLATE_PATH}
  Thesis:   {MSIOT_PATH}

Template total paragraphs: {len(template_all)}
msIoT total paragraphs:    {len(msiot_all)}

Template structural headings: {len(template_headings_text)}
msIoT structural headings:    {len(msiot_outline)}

Missing template headings: {len(missing_items)}
Extra msIoT headings:      {len(extra_items)}
""")

todo_items = []
for sec_name, keywords in standard_sections:
    in_template = any(any(kw in ht for kw in keywords) for ht in [t.lower() for _, t, _, _ in template_outline])
    in_msiot = any(any(kw in ht for kw in keywords) for ht in [t.lower() for _, t, _, _ in msiot_outline])
    if in_template and not in_msiot: todo_items.append(sec_name)
if todo_items:
    print("REQUIRED FIXES (must-add sections):")
    print()
    for item in todo_items:
        print(f"  [+] Add '{item}' section")
    print()
else:
    print("All standard template sections are present in msIoT.")
    print()

if missing_items:
    print("DETAILED LIST OF MISSING TEMPLATE ELEMENTS (by chapter):")
    print()
    current_chapter = "(Preamble)"
    for level, text, style, fsize in template_headings_text:
        if level == 1:
            current_chapter = text
            if (level, text, style, fsize) in missing_items:
                print(f"\n  CHAPTER MISSING: {text}")
        else:
            if (level, text, style, fsize) in missing_items:
                indent = "  " * (level - 1) if level > 1 else ""
                sz = f" ({fsize:.0f}pt)" if fsize else ""
                print(f"  {indent}Missing subsection: {text}{sz}  [in chapter: {current_chapter}]")
    print()

print("=" * 120)
print("END OF COMPARISON REPORT")
print("=" * 120)
