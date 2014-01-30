from __future__ import division #always float divisions for python version < 3.0
import numpy as np
import math
import os
import sys
import matplotlib.pyplot as plt
import matplotlib.lines as lin
import matplotlib.patches as pat
import matplotlib.legend as pyleg
from minuit2 import Minuit2 as minuit #minuit2.so needed. Please compile yourself
from numpy  import *

castor_inner_octant_radius = 40.6507 #cos(22.5) * 44
beampipe_r = (57+0.5)/2 #in mm #+white paper = 0.5mm
beampipe_x = -0.7 #hauke's value
beampipe_y = -1.4

def rotatePoint(centerPoint,point,angle):
    """Rotates a point around another centerPoint. Angle is in degrees.
    Rotation is counter-clockwise"""
    angle = math.radians(angle)
    temp_point = point[0]-centerPoint[0] , point[1]-centerPoint[1]
    temp_point = ( temp_point[0]*math.cos(angle)-temp_point[1]*math.sin(angle) , temp_point[0]*math.sin(angle)+temp_point[1]*math.cos(angle))
    temp_point = temp_point[0]+centerPoint[0] , temp_point[1]+centerPoint[1]
    return temp_point

def distance_to_beampipe( x , y , xe=0 , ye=0 ):
   "calculate distance for any given point to beam pipe outer circle"
   global beampipe_x
   global beampipe_y
   global beampipe_r
   r = math.sqrt((x-beampipe_x)**2 + (y-beampipe_y)**2)
   distance = math.fabs(beampipe_r - r);
   ddisdx = 1 / 2 / r * 2 * (x-beampipe_x)
   ddisdy = 1 / 2 / r * 2 * (y-beampipe_y)
   error = math.sqrt( xe**2 * ddisdx**2 + ye**2 * ddisdy**2)
   return distance , error

class castor_half():
    def __init__(self, name,sensor_angles,sensor_pos,r,r_error):
        self.nsensors = len(sensor_angles)
        assert  self.nsensors == len(r), '#angles must be #r'
        assert  self.nsensors == len(sensor_pos), '#angles must be #positions'
        if name.find("far") != -1:
            self.isFarHalf = True
        elif name.find("near") != -1:
            self.isFarHalf = False
        else:
            sys.stderr.write("Please choose name with either \"near\" or \"far\" in it\n")
            exit(1)
        self.sensor_angles = sensor_angles #x direction is 0. counter-clockwise
        self.sensor_pos = sensor_pos #in ideal geometry
        self.r = r
        self.r_error = r_error #from averaging r (negligible)
        self.verbosity = 1

    def setVerbosity(self, verbosity):
        #0: no output, 1:essential results, 2:everything
        self.verbosity = verbosity

    def fit_pos(self):
        def f(x,y):
            #chi2 function. returns distance to beam pipe circle for all vector(sensorpos)-vector(r) for given (x,y) shift
            chi2 = 0
            for i in range(0,self.nsensors):
                pos = array(self.sensor_pos[i])
                angle = self.sensor_angles[i]
                r = self.r[i]
                r_error = self.r_error[i]

                pointingat = pos - array([r * math.cos(radians(angle)), r * math.sin(radians(angle))])

                error_r = sqrt(1**2 + r_error**2) #1mm sys + stat error
                error_theta = radians(1)

                dpxdr     = -math.cos(radians(angle))
                dpxdtheta = r * math.sin(radians(angle))
                dpydr     = -math.sin(radians(angle))
                dpydtheta = -r * math.cos(radians(angle))

                xe = sqrt( error_r**2 * dpxdr**2 + error_theta**2 * dpxdtheta**2)#x and y is initial sensor positions from drawings. maybe no uncertainty
                ye = sqrt( error_r**2 * dpydr**2 + error_theta**2 * dpydtheta**2)#x and y is initial sensor positions from drawings. maybe no uncertainty

                delta,sigma = distance_to_beampipe(pointingat[0]+x,pointingat[1]+y, xe, ye)
                if self.verbosity>1: print "xe=",xe,"ye=",ye, " --> delta=",delta,"sigma=",sigma
                chi2 += delta ** 2 / sigma ** 2
                
            return chi2
        m = minuit(f)
        if verbosity > 1 : m.printMode = 1
        m.migrad()
        m.minos()
        self.x = m.values["x"]
        self.y = m.values["y"]
        self.xeu = m.merrors["x", 1]
        self.yeu = m.merrors["y", 1]
        self.xel = m.merrors["x", -1]
        self.yel = m.merrors["y", -1]
        chi2 = m.fval / self.nsensors
        if verbosity > 0 :print "far half: " if self.isFarHalf else "near half: "," fitted position (x,y)=({0:.2f}{1:+.2f}{2:+.2f},{3:.2f}{4:+.2f}{5:+.2f}) with chi2={6:.2f}".format(self.x,self.xeu,self.xel,self.y,self.yeu,self.yel,chi2)
        return

#FITTING
verbosity = 1

#FAR SIDE
far_parameters = [ [180-22.5,-6.5,10] , [180+67.5,-6.5,10] ] #angle,laser is off-center unrotated y-direction in mm, zeroshift means distance when touching the metal in mm
far_angles = [row[0] for row in far_parameters]
far_pos = []
for angle,offcenter,zeroshift in far_parameters:
    far_pos.append(rotatePoint([0,0],[castor_inner_octant_radius+zeroshift,offcenter], angle))
if verbosity > 0:
    print "\nPositions of -far side- sensors are: "
    for pos in far_pos: print "{0[0]:.3f},{0[1]:.3f}".format(pos)

far_r_old = [8.68439,20.2883] #top,bottom
far_r_old_error = [0,0.00508586] #top,bottom
farside_old = castor_half("farside_old",far_angles,far_pos,far_r_old,far_r_old_error)
farside_old.setVerbosity(verbosity)
print "Before B field"
farside_old.fit_pos()

far_r_new = [12.6556,22.2788] #top,bottom
far_r_new_error = [0,0.00172011] #top,bottom
farside_new = castor_half("farside_new",far_angles,far_pos,far_r_new,far_r_new_error)
farside_new.setVerbosity(verbosity)
print "After B field"
farside_new.fit_pos()

#NEAR SIDE
near_parameters = [ [22.5,-6.5,10] , [-67.5,-6.5,10] ]
near_angles = [row[0] for row in near_parameters]
near_pos = []
for angle,offcenter,zeroshift in near_parameters:
    near_pos.append(rotatePoint([0,0],[castor_inner_octant_radius+zeroshift,offcenter], angle))
if verbosity > 0:
    print "\nPositions of -near side- sensors are: "
    for pos in near_pos: print "{0[0]:.3f},{0[1]:.3f}".format(pos)

near_r_old = [15.2248,25.8462] #top,bottom
near_r_old_error = [0.00119269,0.0232433] #top,bottom #near bottom is the problematic channel. it has rms of 0.8 but /sqrt(1200) data points ~ 0.02
nearside_old = castor_half("nearside_old",near_angles,near_pos,near_r_old,near_r_old_error)
nearside_old.setVerbosity(verbosity)
print "Before B field"
nearside_old.fit_pos()

near_r_new = [32.9261,32.6869] #top,bottom
near_r_new_error = [2.44163e-15,0.00781898] #top,bottom
nearside_new = castor_half("nearside_new",near_angles,near_pos,near_r_new,near_r_new_error)
nearside_new.setVerbosity(verbosity)
print "After B field"
nearside_new.fit_pos()

def printShift(old,new):
    dx = new.x-old.x
    dy = new.y-old.y
    dr = math.sqrt(dx**2+dy**2)
    print "Shift due to magnetic field (","far  half" if old.isFarHalf else "near half", "): dx={0:.3f} dy={1:.3f} dr={2:.3f}".format(dx,dy,dr)

print("\n\n")
printShift(farside_old,farside_new)
printShift(nearside_old,nearside_new)

#DRAWING
fig = plt.figure(figsize=[8,8])
ax = fig.gca()

circle1=plt.Circle((beampipe_x,beampipe_y),beampipe_r,color='0.5',fill=False,label="beampipe")
ax.add_artist(circle1)

leglables=["beampipe"]
legpointers=[circle1]

def draw(fig,old,new):
    ax = fig.gca()
    assert old.nsensors == new.nsensors

    def drawSensor(label,color,pos,pointingat):
       sightline = lin.Line2D( [pos[0],pointingat[0]] , [pos[1],pointingat[1]], color=color, label=label)
       ax.add_artist(sightline)
       sensor=plt.Circle((pos[0],pos[1]),3,color=color,fill=True, alpha=0.5)
       ax.add_artist(sensor)
       if(label): legpointers.append(sensor)
       if(label): leglables.append(label)

    for i in range(0,old.nsensors):
        pos = array(old.sensor_pos[i])
        angle = old.sensor_angles[i]
        rold = old.r[i]
        shift = array([old.x,old.y])
        pointingat = pos - array([rold * math.cos(radians(angle)), rold * math.sin(radians(angle))])

        #draw ideal position
        drawSensor("nominal position" if i==0 else "","0.5",pos,pointingat); #no name skips label for i>1, 0.5 is grey colour

        #draw fitted old position
        drawSensor("w/o B field" if i==0 else "","r",pos+shift,pointingat+shift);

        posnew = array(new.sensor_pos[i])
        anglenew = new.sensor_angles[i]
        rnew = new.r[i]
        shiftnew = array([new.x,new.y])
        pointingatnew = posnew - array([rnew * math.cos(radians(angle)), rnew * math.sin(radians(angle))])

        #draw fitted new position
        drawSensor("w B field" if i==0 else "","g",posnew+shiftnew,pointingatnew+shiftnew);

        #arrows and text
        ax.annotate("",
                xy=(posnew[0]+shiftnew[0],posnew[1]+shiftnew[1]), xycoords='data',
                xytext=(pos[0]+shift[0],pos[1]+shift[1]), textcoords='data',
                arrowprops=dict(arrowstyle="fancy", #linestyle="dashed",
                                color="0.1",
                                shrinkA=0, shrinkB=0,
                                patchA=None,
                                patchB=None,
                                connectionstyle="arc3,rad=0.2",
                                ),
                )


        text = ("Far" if new.isFarHalf else "Near") + " (without B field)\nx={0:.2f}+-{1:.2f}\ny={2:.3f}+-{3:.2f}".format(old.x,(old.xeu-old.xel)/2,old.y,(old.yeu-old.yel)/2)
        an1 = ax.annotate(text, xy=(0.02 if new.isFarHalf else 0.59,0.97), xycoords="axes fraction",
                  va="top", ha="left" if new.isFarHalf else "right",
                  bbox=dict(boxstyle="round", fc="w"))

        from matplotlib.text import OffsetFrom
        offset_from = OffsetFrom(an1, (0.5, 0))
        text = ("Far" if new.isFarHalf else "Near") + " (with B field)\nx={0:.2f}+-{1:.2f}\ny={2:.3f}+-{3:.2f}".format(new.x,(new.xeu-new.xel)/2,new.y,(new.yeu-new.yel)/2)
        an2 = ax.annotate(text, xy=(0.1, 0.1), xycoords="data",
                          xytext=(0, -10), textcoords=offset_from,
                          # xytext is offset points from "xy=(0.5, 0), xycoords=at"
                          va="top", ha="center",
                          bbox=dict(boxstyle="round", fc="w"))

plt.xlabel('x [mm]')
plt.ylabel('y [mm]')
plt.title('IR Sensors (IP side) [Jan 08 -> Jan 17]')
#plt.text(60, .025, r'$\mu=100,\ \sigma=15$')

draw(fig,farside_old,farside_new)
leg = ax.legend(legpointers,leglables,loc='upper right', fancybox=True)
draw(fig,nearside_old,nearside_new)

plt.axis([-70, 70, -60, 80]) #make it square

plt.savefig("ir_IP_pos.png",bbox_inches="tight")
plt.savefig("ir_IP_pos.pdf",bbox_inches="tight")

