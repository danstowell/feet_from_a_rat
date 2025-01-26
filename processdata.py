#!/usr/bin/python
# vim: set fileencoding=utf8 :

import os, glob, json
#import numpy as np
from scipy.spatial import Delaunay, KDTree
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import matplotlib.path as mplPath
from math import radians, cos, sin, asin, sqrt
import cPickle as pickle

from ffarcommon import *

# TODO clobber option

uktightpath = mplPath.Path(uktight)

fontfamily='Palatino Linotype'

def haversine(lon1, lat1, lon2, lat2):
	"""
	Calculate the great circle distance between two points
	on the earth (specified in decimal degrees)
	"""
	# convert decimal degrees to radians
	lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

	# haversine formula
	dlon = lon2 - lon1
	dlat = lat2 - lat1
	a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
	c = 2 * asin(sqrt(a))

	# 6367 km is the radius of the Earth
	km = 6367 * c
	return km


if __name__ == '__main__':
	specs = loadspecs()
	allmidpoints = []
	for inpath in glob.glob('data_overpass/*.json'):
		print("-----------------------------------------------------------------------")
		print("Processing: %s" % inpath)
		lbl = os.path.splitext(os.path.basename(inpath))[0]
		readable = specs[lbl]['readable']
		points = []  # lon, lat
		ids	= []  # id
		with open(inpath) as infp:
			jsondata = json.load(infp)
			timestamp = jsondata['osm3s']['timestamp_osm_base']
			print("Timestamp: %s.  Num elements: %i" % (timestamp, len(jsondata['elements'])))
			numpos = 0
			numneg = 0
			for element in jsondata['elements']:
				if all([key in element for key in ['type', 'id', 'lat', 'lon']]) and element['type']=='node':
					numpos += 1
					points.append([element[key] for key in ['lon', 'lat']])
					ids.append(element['id'])
				else:
					numneg += 1
			print("pos: %i, neg: %i" % (numpos, numneg))

		########################################################
		# now do delaunay
		tri = Delaunay(points)

		edge_points = []
		edges = set()

		def add_edge(i, j):
			"""Add a line between the i-th and j-th points, if not in the list already"""
			if (i, j) in edges or (j, i) in edges:
				# already added
				return
			edges.add( (i, j) )
			edge_points.append([ points[i], points[j] ])

		best_tri  = None
		best_dist = 0.0
		best_area = 0.0
		best_midpoint = None
		for ia, ib, ic in tri.vertices:
			# nb midpoint should be circumcentre, not centre of mass
			ax = points[ia][0]
			ay = points[ia][1]
			bx = points[ib][0]
			by = points[ib][1]
			cx = points[ic][0]
			cy = points[ic][1]
			d = max(2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by)), 1e-24)
			midpoint = [
				((ax*ax + ay*ay)*(by-cy) + (bx*bx + by*by)*(cy-ay) + (cx*cx + cy*cy)*(ay-by)) / d,
				((ax*ax + ay*ay)*(cx-bx) + (bx*bx + by*by)*(ax-cx) + (cx*cx + cy*cy)*(bx-ax)) / d,
			]

			# check if midpoint is over the sea, skip if so
			if not uktightpath.contains_point(midpoint):
				continue
			add_edge(ia, ib)
			add_edge(ib, ic)
			add_edge(ic, ia)
			# check if winner
			threedistances = [haversine(midpoint[0], midpoint[1], points[index][0], points[index][1]) for index in [ia, ib, ic]]
			distancekm = min(threedistances)
			if distancekm > best_dist:
				best_dist = distancekm
				best_proximest = [ia, ib, ic]
				best_midpoint = midpoint

		###################################################
		# Next we want to handle the coastal points as well
		print("doing kdtree bit")
		kdtree = KDTree(points)
		for coastpoint in uktight:
			kddist, kdnearest = kdtree.query(coastpoint)
			distancekm = haversine(coastpoint[0], coastpoint[1], points[kdnearest][0], points[kdnearest][1])
			#print(kdresult)
			if distancekm > best_dist:
				best_dist = distancekm
				best_proximest = [kdnearest]
				best_midpoint = coastpoint

		####################################
		# OK, now we have a winner.
		# Let's geocode it.
		nominatimq = "http://nominatim.openstreetmap.org/reverse?format=json&addressdetails=0&zoom=12&lon=%g&lat=%g" % (best_midpoint[0], best_midpoint[1])
		print nominatimq
		# NOTE: always sleep 2 sec after nominatim query, since hard-limited max usage of 1/sec

		# OK ready.
		# write out a pickle listing:
		#  * winning location
		#  * last-updated-date (date of the overpass dnld)
		#  * the three proximest
		#  * the distance in km
		#  * num nodes considered
		outdata = {
			'lbl': lbl,
			'midpoint': best_midpoint,
			'timestamp': timestamp,
			'proximest': [[points[index][0], points[index][1], ids[index]] for index in best_proximest], # NB lon, lat, index for each
			'distancekm':  best_dist,
			'numnodesconsidered': numpos,
		}
		print(outdata)
		print("Furthest point: http://www.openstreetmap.org/?mlat=%g&mlon=%g#map=15/%g/%g" % (best_midpoint[1], best_midpoint[0], best_midpoint[1], best_midpoint[0]))
		with open("data_pickles/type_%s.pickle" % lbl, 'wb') as pfp:
			pickle.dump(outdata, pfp, -1)

		# and remember the midpoint for plotting
		allmidpoints.append([best_midpoint[0], best_midpoint[1], lbl])

		###############################################
		plt.figure()
		plt.title('Furthest point from %s %s' % (specs[lbl]['article'], readable), family=fontfamily)
		lines = LineCollection([[uktight[i], uktight[i+1]] for i in range(len(uktight)-1)])
		plt.gca().add_collection(lines)
		# plot the delaunay too, if small enough
		if len(points) < 5000:
			plotlines = LineCollection(edge_points)
			plotpoints = points
		else:
			# else, just plot the nearest points...
			for boxscaler in [8, 4, 2, 1, 0.5, 0.25]:
				minlon = min([points[index][0] for index in best_proximest])
				maxlon = max([points[index][0] for index in best_proximest])
				lonexpand = max((maxlon-minlon), 0.5) * boxscaler * 2
				minlon -= lonexpand
				maxlon += lonexpand
				minlat = min([points[index][1] for index in best_proximest])
				maxlat = max([points[index][1] for index in best_proximest])
				latexpand = max((maxlat-minlat), 0.5) * boxscaler * 0.5
				minlat -= latexpand
				maxlat += latexpand

				def withinbox(point):
					return (point[0]>=minlon) and (point[0]<=maxlon) and (point[1]>=minlat) and (point[1]<=maxlat)

				plotpoints = [point for point in points if withinbox(point)]
				plotlines = LineCollection([edge_point for edge_point in edge_points if withinbox(edge_point[0]) or withinbox(edge_point[1])])
				if len(plotpoints) < 5000:
					break

		plt.gca().add_collection(plotlines)
		plt.plot([datum[0] for datum in plotpoints] + [best_midpoint[0]], [datum[1] for datum in plotpoints] + [best_midpoint[1]], '.k', hold=1)
		plt.plot([best_midpoint[0]], [best_midpoint[1]], 'ro')
		plt.xlim(-9.95459,  5.82373)
		plt.ylim(49.85122, 58.76551)
		plt.text(1.01, 0, "This image is part of 'Feet From A Rat', by Dan Stowell, CC BY-SA 4.0.\nImage makes use of map data (c) OpenStreetMap contributors (www.openstreetmap.org), ODbL.", transform=plt.gca().transAxes, rotation=90, family=fontfamily, fontsize=8, color=(0.5, 0.5, 0.5), horizontalalignment='left', verticalalignment='bottom')
		plt.gca().axis('off')
		plt.savefig('pdf/delaunay_%s.pdf' % lbl)
		plt.savefig('%s/images/%s.png' % (htmloutfolder, lbl))
		plt.clf()
		plt.close()

	###############################################
	# a single plot of all the furthest points
	if False:
		blobstyles = (['o'] * 7) + (['D'] * 7) + (['p'] * 7)
		plt.figure()
		plt.title('All furthest points', family=fontfamily)
		lines = LineCollection([[uktight[i], uktight[i+1]] for i in range(len(uktight)-1)])
		plt.gca().add_collection(lines)
		for whichmidpoint, (midx, midy, lbl) in enumerate(allmidpoints):
			plt.plot([midx], [midy], blobstyles[whichmidpoint], hold=1, label=specs[lbl]['readable'])
		plt.xlim(-7.95459,  7.82373)
		plt.ylim(49.85122, 58.76551)
		plt.legend(fontsize=10)
		plt.savefig('pdf/allmidpoints.pdf')
		plt.clf()
		plt.close()


