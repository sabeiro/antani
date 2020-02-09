"""
geo_ops:
geometrical operations
"""
import json, datetime, re
import numpy as np
import pandas as pd
import geopandas as gpd
import scipy as sp
import matplotlib.pyplot as plt
import geomadi.geo_octree as g_o
import shapely as sh
from shapely import geometry
from shapely.ops import cascaded_union
import shapely.speedups
shapely.speedups.enable()
from rtree import index
import geomadi.geo_octree as otree


def bbox(BBox):
    """return a polygon from a bounding box"""
    P = geometry.Polygon([[BBox[0][0],BBox[0][1]]
                          ,[BBox[0][0],BBox[1][1]]
                          ,[BBox[1][0],BBox[1][1]]
                          ,[BBox[1][0],BBox[0][1]]
                          ,[BBox[0][0],BBox[0][1]]
    ])
    return P

def boxAround(xl,yl,BBox=[0.05,0.05]):
    """a list of boxes around the coordinates"""
    P = [sh.geometry.Polygon([[x-BBox[0],y-BBox[1]],[x+BBox[0],y-BBox[1]],[x+BBox[0],y+BBox[1]],[x-BBox[0],y+BBox[1]]]) for x,y in zip(xl,yl)]
    return P

def intersectionList(poly1,poly2):
    """return the intersection area between two lists of polygons"""
    idx = index.Index()
    for i, p in enumerate(poly2):
        idx.insert(i, p.bounds)
    sectL = []
    for p in poly1:
        merged_cells = cascaded_union([poly2[i] for i in idx.intersection(p.bounds)])
        sectL.append(p.intersection(merged_cells).area)
    return sectL

def intersectGeom(poly1,poly2,id1,id2,precDigit=10):
    """return the intersection ids between two lists of polygons"""
    gO = otree.h3tree()
    idx = index.Index()
    for i, p in enumerate(poly2):
        idx.insert(i, p.bounds)
    sectL = {}
    numL = []
    for i,p in zip(id1,poly1):
        merged_cells = cascaded_union([poly2[i] for i in idx.intersection(p.bounds)])
        pint = p.intersection(merged_cells)
        if isinstance(pint,sh.geometry.Point):
            l = [gO.encode(pint.x,pint.y,precision=precDigit)]
        else:
            l = [gO.encode(x.x,x.y,precision=precDigit) for x in pint]
        sectL[i] = l
        numL.append(len(l))
    print("%.2f points per polygon" % (np.mean(numL)) )
    return sectL

def minDist(point1,poly2):
    """return the minimum distances between points and polygons"""
    p2 = cascaded_union(poly2)
    distL = [p1.distance(p2) for p1 in point1]
    return distL

