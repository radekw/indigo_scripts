#!/usr/bin/env python

import sys
import os
import sqlite3
import urllib2
import urllib
import re
import json
import time

devices = {}
variables = {}

here = os.path.normpath(os.path.dirname(sys.argv[0]))
outfilename = os.path.join(here, 'indigo_export.json')
outfile = open(outfilename, 'a')

excluded_name = ['EventScripts App', 'Weather']

con = sqlite3.connect('indigo.sqlite')
con.row_factory = sqlite3.Row
cur = con.cursor()

# create last id table
sql = 'CREATE TABLE IF NOT EXISTS export_info (table_name TEXT PRIMARY KEY, last_id INTEGER)'
cur.execute(sql)

# collect device and variable tables names
tables_sql = 'SELECT name FROM sqlite_master WHERE type="table";'
cur.execute(tables_sql)
for t in cur.fetchall():
    t_name = t[0]
    m = re.match(r'(\w+)_history_(\d+)', t_name)
    if m is None:
        continue
    i_id = m.group(2)
    i_type = m.group(1)
    if i_type == 'device':
        devices[i_id] = {'table_name': t_name, 'type': 'device'}
    elif i_type == 'variable':
        devices[i_id] = {'table_name': t_name, 'type': 'variable'}

# init urllib
iurl = 'http://127.0.0.1:8176'
pass_man = urllib2.HTTPPasswordMgrWithDefaultRealm()
pass_man.add_password(None, iurl, 'YOURUSER', 'YOURPASSWORD')
auth_handler = urllib2.HTTPDigestAuthHandler(pass_man)
opener = urllib2.build_opener(auth_handler)
urllib2.install_opener(opener)

# collect device names
for t in ['devices', 'variables']:
    f = urllib2.urlopen('http://127.0.0.1:8176/%s.txt/' % t)
    urls = []
    for p in f.readlines():
        urls.append('%s%s' % (iurl, urllib.pathname2url(p.strip())))
    for u in urls:
        f = urllib2.urlopen(u)
        d = {}
        for l in f.readlines():
            ls = l.split(':')
            if len(ls) < 2:
                continue
            d[ls[0].strip()] = ls[1].strip()
        if len(d) == 0:
            continue
        if d.has_key('id') and d.has_key('name'):
            if devices.has_key(d['id']):
                devices[d['id']]['name'] = d['name']

# describe sqlite device tables
for d_id, d in devices.iteritems():
    pragma_sql = "pragma table_info('%s')" % d['table_name']
    cur.execute(pragma_sql)
    devices[d_id]['schema'] = {}
    for t in cur.fetchall():
        devices[d_id]['schema'][t[1]] = t[2]

def convert_value(v, vtype):
    if vtype == 'TIMESTAMP':
        return v
    if vtype == 'INTEGER':
        try:
            return float(v)
        except:
            pass
        return 0.0
    elif vtype == 'BOOL':
        if v == 'True':
            return 1
        elif v == 'False':
            return 0
        else:
            return 0
    elif vtype == 'REAL':
        try:
            return float(v)
        except:
            pass
        return 0.0
    elif vtype == 'TEXT':
        try:
            return float(v)
        except:
            pass
        if v is None:
            v = ''
        return v
    print 'do not know how to convert %s %s' % (v, vtype)
    return v

def save_last_id(table_name, last_id):
    sql = 'INSERT OR REPLACE INTO export_info (table_name, last_id) VALUES ("%s", %s)' % (table_name, last_id)
    cur.execute(sql)
    con.commit()

def get_last_id(table_name):
    last_id = 0
    sql = 'SELECT last_id from export_info where table_name="%s"' % table_name
    cur.execute(sql)
    r = cur.fetchone()
    if r is not None:
        last_id = r[0]
    return last_id

# get device data
for d_id, d in devices.iteritems():
    if not d.has_key('name'):
        continue
    if d['name'] in excluded_name:
        continue
    print '%s [%s] (reading)' % (d['name'], d_id)
    last_id = get_last_id(d['table_name'])
    sql = "SELECT * FROM %s WHERE id > %s ORDER BY id ASC" % (d['table_name'], last_id)
    cur.execute(sql)
    c = 1
    for r in cur.fetchall():
        kvj = {
            'name': d['name'],
            'type': d['type'],
            'item_id': str(d_id)
        }
        for k in r.keys():
            if k.endswith('_ui'):
                #v = r[k]
                continue
            else:
                vtype = d['schema'][k]
                v = convert_value(r[k], vtype)
            kvj[k] = v
        kvj['id'] = '%s.%s' % (d_id, r['id'])
        last_id = r['id']
        outfile.write(json.dumps(kvj) + '\n')
        #if (c % 50) == 0:
        #    time.sleep(0.5)
        c += 1
    print '%s [%s] (wrote %s records)' % (d['name'], d_id, c)
    save_last_id(d['table_name'], last_id)

outfile.close()

