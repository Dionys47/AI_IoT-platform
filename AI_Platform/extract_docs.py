import docx
import os

def extract_doc(filepath):
    doc = docx.Document(filepath)
    paragraphs = []
    tables = []
    images = []

    img_count = 1
    body = doc.element.body

    for child in body:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'p':
            try:
                p_elem = docx.text.paragraph.Paragraph(child, doc)
                style_name = p_elem.style.name if p_elem.style else ''
                text = p_elem.text.strip()
                if text:
                    is_heading = 'Heading' in style_name or style_name.startswith('heading')
                    level = 0
                    if is_heading:
                        try:
                            level = int(style_name.replace('Heading ', '').replace('heading ', ''))
                        except:
                            level = 1
                    paragraphs.append({
                        'type': 'heading' if is_heading else 'paragraph',
                        'level': level,
                        'style': style_name,
                        'text': text
                    })
            except:
                texts = [t.text for t in child.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t') if t.text]
                text = ''.join(texts).strip()
                if text:
                    paragraphs.append({
                        'type': 'paragraph',
                        'level': 0,
                        'style': 'Unknown',
                        'text': text
                    })

        elif tag == 'tbl':
            try:
                table = docx.table.Table(child, doc)
                table_data = []
                for row in table.rows:
                    row_data = []
                    for cell in row.cells:
                        row_data.append(cell.text.strip())
                    table_data.append(row_data)
                if any(any(c for c in r) for r in table_data):
                    tables.append(table_data)
            except:
                pass

        blips = child.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
        for blip in blips:
            embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if embed:
                images.append({
                    'id': 'Image_' + str(img_count),
                    'rId': embed
                })
                img_count += 1

    return {'paragraphs': paragraphs, 'tables': tables, 'images': images}


def print_doc(name, data):
    sep = '=' * 80
    print(sep)
    print('  ' + name)
    print(sep)
    print('Total paragraphs: ' + str(len(data['paragraphs'])))
    print('Total tables: ' + str(len(data['tables'])))
    print('Total images: ' + str(len(data['images'])))
    print()

    for p in data['paragraphs']:
        if p['type'] == 'heading':
            lvl = p['level'] if p['level'] > 0 else 1
            prefix = '#' * lvl
            print()
            print(prefix + ' ' + p['text'])
            print()
        else:
            print(p['text'])

    if data['tables']:
        print()
        print('--- TABLES ---')
        for i, tbl in enumerate(data['tables']):
            print('[Table ' + str(i+1) + ']')
            for row in tbl:
                print(' | '.join(row))
            print()

    if data['images']:
        print('--- IMAGES ---')
        for img in data['images']:
            print(img['id'] + ' (rId: ' + img['rId'] + ')')
        print()


doc1_path = r'C:\Users\USER\Documents\AI_Platform\msIoT.docx'
doc2_path = r'C:\Users\USER\Documents\AI_Platform\msIoT_EN.docx'

print('Extracting: ' + doc1_path)
doc1 = extract_doc(doc1_path)
print('Extracting: ' + doc2_path)
doc2 = extract_doc(doc2_path)

print_doc('msIoT.docx (Arabic/Original)', doc1)
print_doc('msIoT_EN.docx (English Translation)', doc2)

print()
print('=' * 80)
print('  STRUCTURE COMPARISON')
print('=' * 80)
headings1 = [p for p in doc1['paragraphs'] if p['type'] == 'heading']
headings2 = [p for p in doc2['paragraphs'] if p['type'] == 'heading']
print('msIoT.docx headings: ' + str(len(headings1)))
for h in headings1:
    indent = '  ' * (h['level'] - 1)
    print(indent + 'H' + str(h['level']) + ': ' + h['text'])
print()
print('msIoT_EN.docx headings: ' + str(len(headings2)))
for h in headings2:
    indent = '  ' * (h['level'] - 1)
    print(indent + 'H' + str(h['level']) + ': ' + h['text'])
