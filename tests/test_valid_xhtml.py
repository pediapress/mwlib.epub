#! /usr/bin/env python
#! -*- coding:utf-8 -*-

# Copyright (c) 2012, PediaPress GmbH
# See README.txt for additional licensing information.

'''Test for valid xhtml 1.1 output

Since I have given up on producing valid xhtml 1.1 this is just a collection of
now disabled and non-functional tests/code.
'''

# def get_tidy_tree(html, dump=False):
#     html = etree.tostring(etree.HTML(html), encoding='utf-8')
#     html, errors = collection.tidy_xhtml(html)
#     if dump:
#         print '>'*40
#         print html
#         if errors:
#             print '!'*40
#             print errors
#     return etree.HTML(html)

# def test_bare_text_trivial():
#     html = '''\
# <blockquote>
#  unmotivated text
# </blockquote>
#     '''
#     tree = get_tidy_tree(html)
#     bq = tree.xpath('//blockquote')[0]
#     assert len(bq.text.strip()) == 0

# @pytest.mark.xfail
# def test_bare_text_simple():
#     html='''\
# <blockquote>
#  <ol>
#   <li>blub</li>
#  </ol>
#  unmotivated text
# </blockquote>
# '''
#     tree = get_tidy_tree(html)
#     ol = tree.xpath('//ol')[0]
#     dump_tree(tree)
#     assert ol.tail is None

# def test_convert_center():
#     html='''\
# <center>
# this is centered text
# </center>
# '''
#     tree = get_tidy_tree(html)
#     assert len(tree.xpath('//center')) == 0


# def test_tidy_old_tags(tmpdir):
#     frag = '''\
# <center>
# this is centered text
# </center>
# '''
#     xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'tidy_old_tags.epub')
#     assert ret == 0

# def test_tidy_ids(tmpdir):
#     frag = '''\
#     <p id="blub17:42">bla</p>
# '''

#     xhtml, ret, stdout, stderr = render_frag(frag, tmpdir, 'tidy_ids.epub')
#     assert ret == 0
