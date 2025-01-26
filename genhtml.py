from ffarcommon import *
from shutil import copyfile, copytree, rmtree
from datetime import datetime

with open('template_main.html', 'rb') as fp:
	template_main = ''.join(line for line in fp)
with open('template_index.html', 'rb') as fp:
	template_index = ''.join(line for line in fp)


def genhtml(specname, spec):
	spec['sentence'] = construct_html_sentence(spec)
	spec['lon'] = "%g" % spec['midpoint'][0]
	spec['lat'] = "%g" % spec['midpoint'][1]


	# the proximest_links would be clumsy to do with template syntax so we simply build it here
	# http://www.openstreetmap.org/?mlat={{lat}}&mlon={{lon}}#map=8/{{lat}}/{{lon}}

	proximest_links = []
	for lon, lat, idx in spec['proximest']:
		proximest_links.append("<a href='http://www.openstreetmap.org/node/%i#map=16/%g/%g'>this</a>" % (idx, lat, lon))
		#proximest_links.append("<a href='http://www.openstreetmap.org/?mlat=%g&mlon=%g#map=16/%g/%g'>here</a>" % (lat, lon, lat, lon))
	if len(proximest_links) == 1:
		spec['proximest_links'] = "%s"  % proximest_links[0]
	else:
		spec['proximest_links'] = "%s and %s"  % (', '.join(proximest_links[:-1]), proximest_links[-1])

	html = template_main
	for keyword in ['lbl', 'article', 'readable', 'lon', 'lat', 'sentence', 'proximest_links']:
		html = html.replace('{{%s}}' % keyword, spec[keyword])
	return html



###############################################
if __name__ == '__main__':
	specs = loadspecs(picklestoo=True)
	pathlist = []
	sentencelinks = '' # for the index page, links out to all
	txtdump = open('%s/data.csv' % htmloutfolder, 'wb')
	for specname, spec in sorted(specs.items()):
		outfname = "%s.html" % (specname)
		pathlist.append(outfname)
		print("Generating %s" % outfname)
		html = genhtml(specname, spec)
		with open("%s/%s" % (htmloutfolder, outfname), 'wb') as fp:
			fp.write(html)
		txtdump.write("%s,%i\n" % (specname, spec['distancekm'] / 1.609344))
		sentencelinks += "<p><a href='%s'>%s</a></p>\n" % (outfname, construct_html_sentence(spec))

	# Now the "index" page
	outfname = "index.html"
	print("Generating %s" % outfname)
	pathlist = 'var pathlist = [%s];' % ', '.join(["'%s'" % apath for apath in pathlist])
	html = template_index.replace('{{pathlist}}', pathlist).replace('{{sentencelinks}}', sentencelinks)
	with open("%s/%s" % (htmloutfolder, outfname), 'wb') as fp:
		fp.write(html)

	print("Generating cache.manifest")
	with open("%s/cache.manifest" % (htmloutfolder), 'wb') as fp:
		fp.write("""CACHE MANIFEST
# Generated %s
index.html
static/pixel.png
static/style-ffar.css

# Now for each type:
""" % (str(datetime.now())))

		for specname in specs:
			fp.write("""%s.html
images/%s.png
""" % (specname, specname))

	rmtree('html/static')
	copytree('static', 'html/static')
	copyfile('manifest.webapp', 'html/manifest.webapp')

