#!/usr/bin/python
# coding=utf-8
#
import os

MAX_PARAGRAPH_SIZE = 400
SENTENCE_PER_PARAGRAPH = 2

import zipfile


def chunks(l, n):
  """Yield successive n-sized chunks from l."""
  for i in xrange(0, len(l), n):
    yield l[i:i + n]


def split_paragraph(text):
  parts = list(chunks(text.strip().split('. '), SENTENCE_PER_PARAGRAPH))
  result = []
  for part in parts[:-1]:
    result.append('. '.join(part) + '.')

  l = len(parts)
  if l > 0:
    result.append('. '.join(parts[l - 1]))
  return result


def zipdir(path, zip):
  for root, dirs, files in os.walk(path):
    for file in files:
      filename = os.path.join(root, file)
      arcname = filename[len(path) + 1:]
      print arcname
      zip.write(filename, arcname=arcname)


if __name__ == '__main__':
  text = 'A long paragraph containing many sentences. Second sentence. Third one. And another?'

  split = split_paragraph(text)
  for part in split:
    print '%d: %s' % (len(part), part)
