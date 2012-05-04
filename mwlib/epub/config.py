#! /usr/bin/env python
#! -*- coding:utf-8 -*-

## epub container config
opf_fn = 'OPS/book.opf'
ncx_fn = 'OPS/book.ncx'
meta_inf_fn = 'META-INF/container.xml'

img_rel_path = 'images/'
img_abs_path = 'OPS/' + img_rel_path

## collection converter

# maximum number of items in a collection for which parsetrees are held in memory
max_parsetree_num = 50
