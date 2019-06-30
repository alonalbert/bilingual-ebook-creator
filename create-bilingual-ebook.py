#!/usr/bin/python
#

import argparse
import os
import shutil
import zipfile

from googletrans import Translator
from lxml import etree

XHTMLNS = {'x': 'http://www.w3.org/1999/xhtml'}

SPINE_ITEMS = '        <SPINE_ITEMS/>'

MANIFEST_ITEMS = '        <MANIFEST_ITEMS/>'

OPDNS = {'opf': 'http://www.idpf.org/2007/opf', 'dc': 'http://purl.org/dc/elements/1.1/'}
MANIFEST_COVER_IMG = '        <item id="cover-image" href="%s" media-type="image/%s"/>'
MANIFEST_CHAPTER = '        <item id="%s"   href="%s" media-type="application/xhtml+xml"/>'
SPINE_ITEM = '        <itemref idref="%s" linear="yes"/>'

CONTAINER_FILE = 'template/META-INF/container.xml'

COPY_FILES = [
  'template/mimetype',
  'template/view.css',
]

MAX_PARAGRAPH_SIZE = 400

def read_file(filename):
  global f
  with open(filename) as f:
    return f.read()

def chunks(l, n):
  """Yield successive n-sized chunks from l."""
  for i in xrange(0, len(l), n):
    yield l[i:i + n]


def split_paragraph(text, sentences_per_paragraph):
  parts = list(chunks(text.strip().split('. '), sentences_per_paragraph))
  result = []
  for part in parts[:-1]:
    result.append('. '.join(part) + '.')

  l = len(parts)
  if l > 0:
    result.append('. '.join(parts[l - 1]))
  return result

# def split_paragraph(text):
#   if len(text) <= MAX_PARAGRAPH_SIZE:
#     return [text]
#   split = text.split('. ')
#
#   result = []
#   current = []
#   n_ = 0
#   for part in split:
#     l = len(part)
#     if n_ + l > MAX_PARAGRAPH_SIZE:
#       result.append('. '.join(current) + '.')
#       current = []
#       n_ = 0
#     current.append(part)
#     n_ += l
#
#   if len(current) > 0:
#     result.append('. '.join(current))
#
#   return result

def zipdir(path, zip):
  for root, dirs, files in os.walk(path):
    for file in files:
      filename = os.path.join(root, file)
      arcname = filename[len(path) + 1:]
      zip.write(filename, arcname=arcname)

if __name__ == '__main__':
  parser = argparse.ArgumentParser(description='Create a bilingual ebook.')
  parser.add_argument('--translate_to', help='Language to translate to', default='en', type=str)
  parser.add_argument('--skip_section', help='Don''t translate the first N sections', type=int, default=1)
  parser.add_argument('--out', help='Output file name', type=str, default='/tmp')
  parser.add_argument('--tmp', help='Temp dir', type=str, default=None)
  parser.add_argument('--sentences_per_paragraph', help='Number of sentences in paragraph', type=int, default=2)
  parser.add_argument('--cover_image', help='Cover image file', type=str)
  parser.add_argument('ebook_file', help='Ebook to translate', type=str)

  args = parser.parse_args()

  tmp_dir = args.tmp
  meta_inf = os.path.join(tmp_dir, 'META-INF')
  if not os.path.exists(meta_inf):
    os.makedirs(meta_inf)

  shutil.copy(CONTAINER_FILE, meta_inf)
  for file in COPY_FILES:
    shutil.copy(file, tmp_dir)

  ebook_zip = zipfile.ZipFile(args.ebook_file)
  with ebook_zip.open('META-INF/container.xml') as f:
    container_xml = etree.parse(f)

  content_filename = container_xml.xpath('/c:container/c:rootfiles/c:rootfile/@full-path',
                                         namespaces={'c': 'urn:oasis:names:tc:opendocument:xmlns:container'})[0]

  with ebook_zip.open(content_filename) as f:
    content_xml = etree.parse(f)

  metadata = content_xml.xpath('/opf:package/opf:metadata', namespaces=OPDNS)[0]
  if args.cover_image is None:
    cover_image_filename = metadata.xpath('./opf:meta[@name="cover"]/@content', namespaces=OPDNS)[0]
    ebook_zip.extract(cover_image_filename, tmp_dir)
  else:
    shutil.copy(args.cover_image, tmp_dir)
    cover_image_filename = os.path.basename(args.cover_image)

  ebook_zip.extract('toc.ncx', tmp_dir)

  author = metadata.xpath('./dc:creator[@opf:role="aut"]/text()', namespaces=OPDNS)[0].encode('utf8')
  title = metadata.xpath('./dc:title/text()', namespaces=OPDNS)[0].encode('utf8')
  language = metadata.xpath('./dc:language/text()', namespaces=OPDNS)[0]

  chapters = content_xml.xpath('/opf:package/opf:manifest/opf:item[@media-type="application/xhtml+xml"]/@href',
                               namespaces=OPDNS)

  manifest_items = []
  spine_items = []
  manifest_items.append(MANIFEST_COVER_IMG % (cover_image_filename, os.path.splitext(cover_image_filename)[1]))

  for item in chapters:
    manifest_items.append(MANIFEST_CHAPTER % (os.path.splitext(item)[0], item))
    spine_items.append(SPINE_ITEM % os.path.splitext(item)[0])

  with open(os.path.join(tmp_dir, 'content.opf'), 'w+') as f:
    f.write(read_file('template/content.opf') \
            .replace(MANIFEST_ITEMS, str.join('\n', manifest_items)) \
            .replace(SPINE_ITEMS, str.join('\n', spine_items))
            .replace('TITLE', title)
            .replace('CREATOR', author))

  with open(os.path.join(tmp_dir, 'cover.xhtml'), 'w+') as f:
    f.write(read_file('template/cover.xhtml') \
            .replace('COVER', cover_image_filename) \
            .replace('TITLE', title))


  for chapter in chapters[0:args.skip_section]:
    ebook_zip.extract(chapter, tmp_dir)

  translator = Translator()
  parser = etree.XMLParser()

  for chapter in chapters[args.skip_section:]:
    print('Chapter %s' % chapter)
    with ebook_zip.open(chapter) as f:
      chapter_xml = etree.parse(f, parser)

    with open('template/chapter.xhtml') as f:
      output = etree.parse(f, parser)

    output.xpath('/x:html/x:head/x:title', namespaces=XHTMLNS)[0].text = title
    body = chapter_xml.xpath('/x:html/x:body', namespaces=XHTMLNS)[0]
    div = output.xpath('/x:html/x:body/x:div', namespaces=XHTMLNS)[0]
    n = 0
    for item in body:
      item.set('class', 'src')
      text = etree.tostring(item, method="text", encoding='utf-8').strip()
      if item.tag.endswith('}p') and text != '':
        for part in split_paragraph(text, args.sentences_per_paragraph):
          src = etree.Element('p')
          src.set('class', 'src')
          src.text = part.decode('utf-8')
          src.tail = '\n'
          div.append(src)

          trans = etree.Element('p')
          trans.set('class', 'trans')
          trans.text = translator.translate(part, src=language, dest=args.translate_to).text
          trans.tail = '\n'
          div.append(trans)

      else:
        div.append(item)

      n += 1
      if n % 10 == 0:
        print('  %d/%d' % (n, len(body)))

    with open(os.path.join(tmp_dir, chapter), 'w+') as f:
      f.write(etree.tostring(output, pretty_print=True, xml_declaration=True, encoding='utf-8'))

  if args.out is None:
    (name, ext) = os.path.splitext(args.ebook_file)
    output_filename = name + '_bilingual' + ext
  else:
    output_filename = args.out

  with zipfile.ZipFile(output_filename, 'w') as z:
    zipdir(tmp_dir, z)
