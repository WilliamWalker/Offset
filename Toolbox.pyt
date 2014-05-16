####################################################################################################
# Toolbox.pyt
# Author:   William Walker
# Date:     05-03-2014
# Modified: 05-16-2014
####################################################################################################
# Description:
# Contains offset tool
####################################################################################################
# Thank you Carl Trachte @ http://pyright.blogspot.com/2011/02/simple-polygon-offset.html
# for the linear algebra refresher.
#
# Thank you Curtis Price @ USGS
# for help writing polygon geometry objects with arcpy.
####################################################################################################

import math, os, arcpy
from arcpy import env

def calcoffsetpoint(pt1, pt2, offset):
    theta = math.atan2(pt2[1] - pt1[1], pt2[0] - pt1[0])
    theta += math.pi/2.0
    return (pt1[0] + math.cos(theta) * offset, pt1[1] + math.sin(theta) * offset)

def getoffsetintercept(pt1, pt2, m, offset):
    """From points pt1 and pt2 defining a line in the Cartesian plane, the slope of the line m,
    and an offset distance, calculates the y intercept of the new line offset from the original."""
    x, y = calcoffsetpoint(pt1, pt2, offset)
    return y - m * x

def getpt(pt1, pt2, pt3, offset):
    """Gets intersection point of the two lines defined by pt1, pt2, and pt3; offset is the
    distance to offset the point from the polygon."""
    ### Get first offset intercept
    if pt2[0] - pt1[0] != 0:
        m = (pt2[1] - pt1[1])/(pt2[0] - pt1[0])
        boffset = getoffsetintercept(pt1, pt2, m, offset)
    else: # if vertical line (i.e. undefined slope)
        m = "undefined"
        
    ### Get second offset intercept
    if pt3[0] - pt2[0] != 0:
        mprime = (pt3[1] - pt2[1])/(pt3[0] - pt2[0])
        boffsetprime = getoffsetintercept(pt2, pt3, mprime, offset)
    else: # if vertical line (i.e. undefined slope)
        mprime = "undefined"
                
    ### Get intersection of two offset lines
    if m != "undefined" and mprime != "undefined":
        # if neither offset intercepts are vertical
        newx = (boffsetprime - boffset)/(m - mprime)
        newy = m * newx + boffset
    elif m == "undefined":
        # if first offset intercept is vertical
        newx, y_infinity = calcoffsetpoint(pt1, pt2, offset)
        newy = mprime * newx + boffsetprime
    elif mprime == "undefined":
        # if second offset intercept is vertical
        newx, y_infinity = calcoffsetpoint(pt2, pt3, offset)
        newy = m * newx + boffset
    elif m == "undefined" and mprime == "undefined":
        # if both offset intercepts are vertical (same line)
        newx, y_infinity = calcoffsetpoint(pt1, pt2, offset)
        newy = pt2[1]
    return newx, newy

def offsetpolygon(polyx, offset):
    """Offsets a clockwise list of coordinates polyx distance offset to the outside of the polygon.
    Returns list of offset points."""
    polyy = []
    # need three points at a time
    for counter in range(0, len(polyx) - 3):
        # get first offset intercept
        pt = getpt(polyx[counter],
                   polyx[counter + 1],
                   polyx[counter + 2],
                   offset)
        # append new point to polyy
        polyy.append(pt)
    # last three points
    pt = getpt(polyx[-3], polyx[-2], polyx[-1], offset)
    polyy.append(pt)
    pt = getpt(polyx[-2], polyx[-1], polyx[0], offset)
    polyy.append(pt)
    pt = getpt(polyx[-1], polyx[0], polyx[1], offset)
    polyy.append(pt)
    return polyy

class Toolbox(object):
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = ""

        # List of tool classes associated with this toolbox
        self.tools = [Offset]


class Offset(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Offset"
        self.description = ""
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        
        # First parameter
        param0 = arcpy.Parameter(
            displayName = "Input features",
            name = "inFC",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Input")
        param0.filter.list = ["Polyline", "Polygon"]
        
        # Second parameter
        param1 = arcpy.Parameter(
            displayName = "Output features",
            name = "outFC",
            datatype = "GPFeatureLayer",
            parameterType = "Required",
            direction = "Output")

        # Third parameter
        param2 = arcpy.Parameter(
            displayName = "Offset distance",
            name = "offset_dist",
            datatype = "GPDouble",
            parameterType = "Required",
            direction = "Input")

        params = [param0, param1, param2]
        
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""

        ### get parameters
        inFC = parameters[0].valueAsText
        outFC = parameters[1].valueAsText
        offset_dist = parameters[2].valueAsText

        ### check geometry type (Polygon or Polyline)
        desc = arcpy.Describe(inFC)
        geomType = desc.shapeType
        if geomType == 'Polygon':
            
            ### convert offset_dist to float
            offset_dist = float(offset_dist)
    
            ### Print progress
            spat = arcpy.Describe(inFC).spatialReference
            units = spat.linearUnitName
            arcpy.AddMessage("Offsetting %s %s..." % (offset_dist, units))
    
            ### Enable overwrite permission
            arcpy.env.overwriteOutput = True
    
            ### Create output shapefile by copying input shapefile
            arcpy.Copy_management(inFC, outFC)
    
            ### Create empty Array objects
            parts = arcpy.Array()
            rings = arcpy.Array()
            ring = arcpy.Array()
    
            ### Create cursor and update vertex coordinates
            cursor = arcpy.UpdateCursor(outFC)
            shapefield = arcpy.Describe(outFC).shapeFieldName
    
            ### Loop through features of inFC
            for row in cursor:
                newPartList = []
                # loop trough parts of feature
                for part in row.getValue(shapefield):
                    coordList = []
                    counter = 0
                    # loop through points in part
                    for pnt in part:
                        if counter == 0: #skip first point
                            counter += 1
                        else:
                            if pnt:
                                coordList.append((pnt.X, pnt.Y))
                                counter += 1
                            else: #null point, denotes beginning of inner ring
                                counter = 0 #reset counter
                                offsetList = offsetpolygon(coordList, offset_dist) #calculate offset points
                                newPartList.append(offsetList) #add coordinates to new list
                                coordList = [] #empty list
    
                    ### Add final (or only) offset coordinates for part
                    offsetList = offsetpolygon(coordList, offset_dist)
                    newPartList.append(offsetList)
                           
                ### loop through newPartList, to create new polygon geometry object for row
                for part in newPartList:
                    for pnt in part:
                        if pnt:
                            ring.add(arcpy.Point(pnt[0], pnt[1]))
                        else: #null point
                            rings.add(ring)
                            ring.removeAll()
                            
                    ### if last ring, add it
                    rings.add(ring)
                    ring.removeAll()
    
                    ### if only one ring, remove nesting
                    if len(rings) == 1:
                        rings = rings.getObject(0)
    
                    parts.add(rings)
                    rings.removeAll()
                    
                ### if single-part, remove nesting
                if len(parts) == 1:
                    parts = parts.getObject(0)
    
                ### create polygon object based on parts array
                polygon = arcpy.Polygon(parts)
                parts.removeAll()
                
                ### replace geometry with new polygon object
                row.setValue(shapefield, polygon)
    
                ### update cursor
                cursor.updateRow(row)
                
        elif geomType == 'Polyline':
            ### print progress
            units = desc.spatialReference.linearUnitName
            arcpy.AddMessage("Offsetting %s %s..." % (offset_dist, units))

            ### enable overwrite permission
            arcpy.env.overwriteOutput = True

            ###TODO: update code to offset polylines
            
        return
