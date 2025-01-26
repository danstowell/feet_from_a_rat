
import json, glob, os, urllib2, urllib
from time import sleep

from ffarcommon import *

clobber = False   ## IMPORTANT: no data will be overwritten if this is set to False -- i.e. data will never be updated

outpath = 'data_overpass'
overpass_api_url = 'http://overpass-api.de/api/interpreter'

with open('overpass_query_template.xml', 'rb') as fp:
	querytpl = ''.join(line for line in fp)

specs = loadspecs()
for lbl, spec in specs.items():
	print "=========================================================\nProcessing specfile: %s" % lbl
	outf = '%s/%s.json' % (outpath, lbl)
	if (not clobber) and os.path.isfile(outf):
		print("    skipping since data file exists")
		continue

	query = querytpl.replace("%s", spec[u'queryfragment'])

	queryasurl = "%s?%s" % (overpass_api_url, urllib.urlencode([('data', query)]).replace('+', '%20'))
	#print queryasurl
	gotquery = urllib2.urlopen(queryasurl)
	print gotquery.info()
	with open(outf, 'wb') as fp:
		for line in gotquery:
			fp.write(line)
	print("Finished %s" % lbl)

	sleep(3)

