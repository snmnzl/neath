import re
import click
import pandas as pd
from io import StringIO
import os
import xml.etree.ElementTree as ET


@click.command()
@click.argument('tsv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('url-file', type=click.Path(exists=False), required=True, nargs=1)
def extract_document_links(tsv_file, url_file):

    parts = extract_doc_links(tsv_file)

    urls = [part['url'] for part in parts]

    urls = pd.DataFrame(urls, columns=['url'])

    urls.to_csv(url_file, sep="\t", quoting=3, index=False)


@click.command()
@click.argument('tsv-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('annotated-tsv-file', type=click.Path(exists=False), required=True, nargs=1)
def annotate_tsv(tsv_file, annotated_tsv_file):

    parts = extract_doc_links(tsv_file)

    annotated_parts = []

    for part in parts:

        part_data = StringIO(part['header'] + part['text'])

        df = pd.read_csv(part_data, sep="\t", comment='#', quoting=3)

        df['url_id'] = len(annotated_parts)

        annotated_parts.append(df)

    df = pd.concat(annotated_parts)

    df.to_csv(annotated_tsv_file, sep="\t", quoting=3, index=False)


def extract_doc_links(tsv_file):

    parts = []

    header = None

    with open(tsv_file, 'r') as f:
        
        text = []
        url = None

        for line in f:

            if header is None:
                header = "\t".join(line.split()) + '\n'
                continue

            urls = [url for url in
                    re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', line)]

            if len(urls) > 0:
                if url is not None:
                    parts.append({"url": url, 'header': header, 'text': "".join(text)})
                    text = []

                url = urls[-1]
            else:
                if url is None:
                    continue

                line = '\t'.join(line.split())

                if line.count('\t') == 2:

                    line = "\t" + line

                if line.count('\t') >= 3:

                    text.append(line + '\n')

                    continue

                if line.startswith('#'):
                    continue

                if len(line) == 0:
                    continue

                print('Line error: |', line, '|Number of Tabs: ', line.count('\t'))

        if url is not None:
            parts.append({"url": url, 'header': header, 'text': "".join(text)})

    return parts


@click.command()
@click.argument('page-xml-file', type=click.Path(exists=True), required=True, nargs=1)
@click.argument('tsv-out-file', type=click.Path(), required=True, nargs=1)
@click.option('--image-url', type=str, default='http://empty')
def page2tsv(page_xml_file, tsv_out_file, image_url):

    tree = ET.parse(page_xml_file)
    xmlns = tree.getroot().tag.split('}')[0].strip('{')

    urls = []
    if os.path.exists(tsv_out_file):
        parts = extract_doc_links(tsv_out_file)

        urls = [part['url'] for part in parts]
    else:
        pd.DataFrame([], columns=['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'GND-ID', 'url_id', 'left', 'right', 'top',
                                  'bottom']). to_csv(tsv_out_file, sep="\t", quoting=3, index=False)

    tsv = []
    for words in tree.findall('.//{%s}Word' % xmlns):
        for word in words.findall('.//{%s}Unicode' % xmlns):
            text = word.text
            for coords in words.findall('.//{%s}Coords' % xmlns):

                points = [int(pos) for p in coords.attrib['points'].split(' ') for pos in p.split(',')]

                x_points = [points[i] for i in range(0, len(points), 2)]
                y_points = [points[i] for i in range(1, len(points), 2)]

                left = min(x_points)
                right = max(x_points)
                top = min(y_points)
                bottom = max(y_points)

                tsv.append((0, text, 'O', 'O', '-', len(urls), left, right, top, bottom))

    with open(tsv_out_file, 'a') as f:

        f.write('# ' + image_url + '\n')

    tsv = pd.DataFrame(tsv, columns=['No.', 'TOKEN', 'NE-TAG', 'NE-EMB', 'GND-ID',
                                     'url_id', 'left', 'right', 'top', 'bottom'])

    tsv.to_csv(tsv_out_file, sep="\t", quoting=3, index=False, mode='a', header=False)
