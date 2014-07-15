# By Mostapha Sadeghipour Roudsari
# Sadeghipour@gmail.com
# Honeybee started by Mostapha Sadeghipour Roudsari is licensed
# under a Creative Commons Attribution-ShareAlike 3.0 Unported License.

"""
Solve adjacencies
-
Provided by Honeybee 0.0.53

    Args:
        _HBZones: List of Honeybee zones
        altConstruction_: Optional alternate EP construction
        altBC_: Optional alternate boundary condition
    Returns:
        readMe!: Report of the adjacencies
        HBZonesWADJ: List of Honeybee zones with adjacencies
"""
ghenv.Component.Name = "Honeybee_Solve Adjacencies"
ghenv.Component.NickName = 'solveAdjc'
ghenv.Component.Message = 'VER 0.0.53\nJUL_15_2014'
ghenv.Component.Category = "Honeybee"
ghenv.Component.SubCategory = "00 | Honeybee"
try: ghenv.Component.AdditionalHelpFromDocStrings = "3"
except: pass


import Rhino as rc
import scriptcontext as sc
import Grasshopper.Kernel as gh
import uuid

def shootIt(rayList, geometry, tol = 0.01, bounce =1):
   # shoot a list of rays from surface to geometry
   # to find if geometry is adjacent to surface
   for ray in rayList:
        intPt = rc.Geometry.Intersect.Intersection.RayShoot(ray, geometry, bounce)
        if intPt:
            if ray.Position.DistanceTo(intPt[0]) <= tol:
                return True #'Bang!'

def updateAdj(surface1, surface2, altConstruction, altBC, tol):
    # change roof to ceiling
    if surface1.type == 1: surface1.setType(3) # roof + adjacent surface = ceiling
    elif surface2.type == 1: surface2.setType(3)
    
    
    if surface1.type == 2.75: surface1.setType(2)
    if surface2.type == 2.75:  surface2.setType(2) 
    
    # change construction
    if altConstruction == None:
        surface1.setEPConstruction(surface1.intCnstrSet[surface1.type])
        surface2.setEPConstruction(surface1.intCnstrSet[surface2.type])
    else:
        surface1.setEPConstruction(altConstruction)
        surface2.setEPConstruction(altConstruction)
        
    # change bc
    if altBC != None:
        surface2.setBC(altBC)
        surface1.setBC(altBC)
    else:
        surface1.setBC('SURFACE', True)
        surface2.setBC('SURFACE', True)
        # change bc.Obj
        # used to be only a name but I changed it to an object so you can find the parent, etc.
        surface1.setBCObject(surface2)
        surface2.setBCObject(surface1)
    
    # set sun and wind exposure to no exposure
    surface2.setSunExposure('NoSun')
    surface1.setSunExposure('NoSun')
    surface2.setWindExposure('NoWind')
    surface1.setWindExposure('NoWind')
    
    # check for child objects
    if (surface1.hasChild or surface2.hasChild) and (len(surface2.childSrfs)!= len(surface1.childSrfs)):
        # give warning
        warnMsg= "Number of windows doesn't match between " + surface1.name + " and " + surface2.name + "." + \
                 " Make sure adjacent surfaces are divided correctly and have similar windows."
        print warnMsg
        w = gh.GH_RuntimeMessageLevel.Warning
        ghenv.Component.AddRuntimeMessage(w, warnMsg)
        return
        
    if surface1.hasChild and surface2.hasChild:
        # find child surfaces that match the other one
        for childSurface1 in surface1.childSrfs:
            for childSurface2 in surface2.childSrfs:
                if childSurface2.BCObject.name == "":
                    if childSurface1.cenPt.DistanceTo(childSurface2.cenPt) <= tol:
                        childSurface1.BCObject.name = childSurface2.name
                        childSurface2.BCObject.name = childSurface1.name
                        print 'Interior window ' + childSurface1.BCObject.name + \
                              '\t-> is adjacent to <-\t' + childSurface2.BCObject.name + '.'
        


def main(HBZones, altConstruction, altBC, tol, remCurrent):
    
    # import the classes
    if not sc.sticky.has_key('honeybee_release'):
        print "You should first let Honeybee to fly..."
        w = gh.GH_RuntimeMessageLevel.Warning
        ghenv.Component.AddRuntimeMessage(w, "You should first let Honeybee to fly...")
        return
    
    # extra check to be added later.
    # check altBC and altConstruction to be valid inputs
    
    # call the objects from the lib
    hb_hive = sc.sticky["honeybee_Hive"]()
    HBZoneObjects = hb_hive.callFromHoneybeeHive(HBZones)
    
    # clean current boundary condition
    if remCurrent:
        for testZone in HBZoneObjects:
            for srf in testZone.surfaces:
                srf.setBC('OUTDOORS')
                srf.setBCObjectToOutdoors()
    
    # solve it zone by zone
    for testZone in HBZoneObjects:
        # mesh each surface and test if it will be adjacent to any surface
        # from other zones
        for srf in testZone.surfaces:
            #print srf.type, srf.BC 
            if srf.BC.upper() == 'OUTDOORS':
                #Create a mesh of surface to use center points as test points
                meshPar = rc.Geometry.MeshingParameters.Default
                BrepMesh = rc.Geometry.Mesh.CreateFromBrep(srf.geometry, meshPar)[0]
                
                # calculate face normals
                BrepMesh.FaceNormals.ComputeFaceNormals()
                BrepMesh.FaceNormals.UnitizeFaceNormals()
                
                # dictionary to collect center points and rays
                raysDict = {}
                for faceIndex in range(BrepMesh.Faces.Count):
                    srfNormal = (BrepMesh.FaceNormals)[faceIndex]
                    meshSrfCen = BrepMesh.Faces.GetFaceCenter(faceIndex)
                    # move testPt backward for half of tolerance
                    meshSrfCen = rc.Geometry.Point3d.Add(meshSrfCen, -rc.Geometry.Vector3d(srfNormal)* tol /2)
                    
                    raysDict[meshSrfCen] = rc.Geometry.Ray3d(meshSrfCen, srfNormal)
                
                for targetZone in HBZoneObjects:
                    if targetZone.name != testZone.name:
                        # check ray intersection to see if this zone is next to the surface
                        if shootIt(raysDict.values(), [targetZone.geometry], tol + sc.doc.ModelAbsoluteTolerance):
                            for surface in targetZone.surfaces:
                                # check if z value of center points matches
                                if abs(surface.cenPt.Z - srf.cenPt.Z) < tol:
                                    # check distance with the nearest point on each surface
                                    for pt in raysDict.keys():
                                        if surface.geometry.ClosestPoint(pt).DistanceTo(pt) <= tol:
                                            # extra check for normal direction
                                            normalAngle = abs(rc.Geometry.Vector3d.VectorAngle(surface.normalVector, srf.normalVector))
                                            revNormalAngle = abs(rc.Geometry.Vector3d.VectorAngle(surface.normalVector, -srf.normalVector))
                                            #print normalAngle
                                            #print revNormalAngle
                                            if normalAngle==0  or revNormalAngle <= sc.doc.ModelAngleToleranceRadians:
                                                print 'Surface ' + srf.name + ' which is a ' + srf.srfType[srf.type] + \
                                                      '\t-> is adjacent to <-\t' + surface.name + ' which is a ' + \
                                                      surface.srfType[surface.type] + '.'
                                                #if normalAngle == 0:
                                                #    msg = "Warning: Normal direction of one of the surfaces " + srf.name + ", " + surface.name + " should be reversed!"
                                                #    print msg
                                                #    w = gh.GH_RuntimeMessageLevel.Warning
                                                #    ghenv.Component.AddRuntimeMessage(w, msg)
                                                    
                                                updateAdj(srf, surface, altConstruction, altBC, tol)                                        
        
                                                break
                    
                #if srf.type == 3 and srf.BCObject.name == '':
                #        srf.setType(1) # Roof
                #        srf.setBC(srf.srfBC[srf.type])
    
    # add zones to dictionary
    ModifiedHBZones  = hb_hive.addToHoneybeeHive(HBZoneObjects, ghenv.Component.InstanceGuid.ToString() + str(uuid.uuid4()))
    
    return ModifiedHBZones



if _findAdjc and _HBZones and _HBZones[0]!=None:
    try: tol = float(tolerance_)
    except: tol = sc.doc.ModelAbsoluteTolerance
    
    # tolrance can't be less than document tolerance
    if tol < sc.doc.ModelAbsoluteTolerance:
        tol = sc.doc.ModelAbsoluteTolerance
        
    HBZonesWADJ = main(_HBZones, altConstruction_, altBC_, tol, remCurrentAdjc_)
