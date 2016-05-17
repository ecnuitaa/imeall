import os
import sys
from flask  import Flask, request, session, g, redirect
from  flask import    url_for, abort, render_template, flash
from   quippy import Atoms
from   imeall import app
import imeall.slabmaker.slabmaker as slabmaker
import json
from imeall.models import GBAnalysis

class TestDB (object):
  '''
  Logic and consistency tests for the Grainboundary database.
  in particular routines to test all grain and subgrain json files
  are well formed (i.e.) contain logical keys, sigma indices are all
  integers, standard naming patterns for suffices.
  '''
  def __init(self):
    pass

  def extract_json(self, path, json_files):
    lst = os.listdir(path)
    for f in lst:
      f = os.path.join(path,f)
      if os.path.isdir(f):
        self.extract_json(f, json_files)
      else:
        if f.split(".")[-1] == 'json':
          json_files.append(f)
        else:
          pass

  def update_json(self, filename):
    ''' This function was originally written to update all keys in the
    json dictionaries in the grain boundary directories.
    The pattern is quite general and can be adapted to just add
    new keys delete old keys consider it a dictionary migration
    routine. '''
    new_json = {}
    with open(filename,'r') as json_old:
      old_json = json.load(json_old)
      new_json['zplanes'] = old_json['zplanes']
      new_json['orientation_axis'] = old_json['orientation axis']
      new_json['boundary_plane']   = old_json['boundary plane']
      new_json['coincident_sites'] = old_json['coincident sites']
      new_json['angle'] = old_json['angle']
      new_json['gbid']  = old_json['gbid']
      new_json['n_at']  = old_json['n_unit_cell']
      new_json['type']  = 'symmetric tilt boundary'
      dir_path = os.path.join('/'.join((filename.split('/'))[:-1]), old_json['gbid'])
      at = Atoms('{0}.xyz'.format(dir_path, old_json['gbid']))
      cell = at.get_cell()
      A    = cell[0,0]*cell[1,1]
      new_json['A']  = A
      json_path = filename
    with open(json_path,'w') as json_new_file:
      json.dump(new_json, json_new_file, indent=2)

if __name__ == '__main__':
  j_files = []
  db_test = TestDB()
  gb_extract = GBAnalysis()
  j_files    = []
  gb_extract.find_gb_json('./110', j_files,'subgb.json')
  for j_file in j_files:
    j_dict = json.load(open(j_file[1],'r'))
    if 'n_at' not in j_dict.keys():
      print j_file, 'POORLY FORMED'
      with open(j_file[1] ,'r') as f:
        json_file = json.load(f)
      print j_file
      gbid              = j_file[0].split('/')[-1]
      print j_file, gbid
      try:
        at = Atoms('{0}.xyz'.format(os.path.join(j_file[0],gbid.split('_')[0]+'_n12d2.0')))
      except:
        try:
          at = Atoms('{0}.xyz'.format(os.path.join(j_file[0],gbid.split('_')[0]+'_n0d2.0')))
        except:
          try:
            at = Atoms('{0}.xyz'.format(os.path.join(j_file[0],gbid.split('_')[0]+'_n16d2.0')))
          except:
            try:
              at = Atoms('{0}.xyz'.format(os.path.join(j_file[0],gbid.split('_')[0]+'_n16d2.0')))
            except:
              try:
                at = Atoms('{0}.xyz'.format(os.path.join(j_file[0],gbid.split('_')[0]+'_n8d2.0')))
              except:
                print 'FAILED'
                break
      json_file['n_at'] = len(at)
      json_file['gbid'] = gbid
      with open(j_file[1] ,'w') as f:
        json.dump(json_file, f)
    if 'n_unit_cell' in j_dict.keys():
      print j_file, 'HAS n_unit_cell'
      db_test.update_json(j_file)
