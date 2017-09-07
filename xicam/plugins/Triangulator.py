import os
import cv2
import numpy as np
import visvis as vv
import vtk
from vtk.util import numpy_support
import base
import pyqtgraph.opengl as gl


# In case we need to make a normal map, this might be nice:
# http://stackoverflow.com/questions/5281261/generating-a-normal-map-from-a-height-map


def polytopointstriangles(polys):
    vertexes = np.array([polys.GetPoint(i) for i in xrange(polys.GetNumberOfPoints())], dtype=float)

    pdata = polys.GetPolys().GetData()

    values = [int(pdata.GetTuple1(i)) for i in xrange(pdata.GetNumberOfTuples())]

    triangles = []
    while values:
        n = values[0]  # number of points in the polygon
        triangles.append(values[1:n + 1])
        del values[0:n + 1]

    return vertexes, triangles


def numpytovtk(dataarray):
    dataarray = np.ascontiguousarray(dataarray)
    VTK_data = numpy_support.numpy_to_vtk(num_array=dataarray, deep=True, array_type=vtk.VTK_FLOAT)
    return VTK_data


def loadafmasmesh(path):
    flatten = Triangulator.parameters.child('flatten').value()
    gaussianblursize = Triangulator.parameters.child('gaussian').value()
    pixelsize = Triangulator.parameters.child('pixelsize').value()

    # load the image
    #img = misc.imread(path)
    img = np.nan_to_num(np.loadtxt(path))
    print img
    #img=scipy.misc.imresize(img, .1, 'bilinear')

    if flatten:  # if we want to remove the parabolic/spherical background from AFM image
        # make a kernal to scan with; This should be tested with more images to choose the best shape and size;
        # Current kernel is a 20x20 square
        kernel = np.ones((20, 20), np.uint8)
        # Remove background artifact
        img = img - np.minimum(img, cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel))
        # Add optional gaussian blur to denoise
        img = cv2.GaussianBlur(img, (0, 0), gaussianblursize)
        # img = cv2.bilateralFilter(img,9,80,80)

        if len(img.shape) > 2:
            if img.shape[2] == 3:  # if the image is a 3 channel rgb average the channels
                img = np.sum(img, axis=2) / 3.0

    # make a grid array for x and y
    xx, yy = np.mgrid[0:img.shape[0], 0:img.shape[1]].astype(np.float)

    # make the array of points, then reshape it to an Nx3 array
    points = np.array([xx/img.shape[0]*1.e-6, yy/img.shape[1]*1.e-6, img])*1.e9
    points = points.reshape((3, img.shape[0] * img.shape[1])).T

    pointsforvtk = vtk.vtkPoints()
    polygondata = vtk.vtkPolyData()
    cellarray = vtk.vtkCellArray()
    delaunay = vtk.vtkDelaunay2D()
    boundary = vtk.vtkPolyData()

    pointsarray = numpytovtk(points)
    # print type(pointsarray)
    pointsforvtk.SetData(pointsarray)
    polygondata.SetPoints(pointsforvtk)
    boundary.SetPoints(polygondata.GetPoints())
    boundary.SetPolys(cellarray)

    delaunay.SetInputData(polygondata)
    delaunay.SetSourceData(boundary)

    # print(delaunay.GetOutput())
    # meshpoly=delaunay.GetOutput()

    decimator = vtk.vtkDecimatePro()
    decimator.SetInputConnection(delaunay.GetOutputPort())
    decimator.SetTargetReduction(0.9)
    decimator.PreserveTopologyOn()
    # decimator.BoundaryVertexDeletionOff()

    decimator.Update()

    # plotvtk(decimator, boundary)



    print "mesh finished"

    points, triangles = polytopointstriangles(decimator.GetOutput())
    points = points*pixelsize

    points[:, 2] -= min(points[:, 2])

    # do base
    A = len(points)
    B = A + 1
    C = B + 1
    D = C + 1

    points = np.vstack([points,[0,0,0]])
    points = np.vstack([points,[1.e-6,0,0]])
    points = np.vstack([points,[1.e-6,1.e-6,0]])
    points = np.vstack([points,[0,1.e-6,0]])
    triangles = np.vstack([triangles,[A,B,D]])
    triangles = np.vstack([triangles, [B,C,D]])

    print(triangles.__len__())

    return points, triangles


def plotvtk(mesh, boundary):
    meshMapper = vtk.vtkPolyDataMapper()
    meshMapper.SetInputConnection(mesh.GetOutputPort())

    meshActor = vtk.vtkActor()
    meshActor.SetMapper(meshMapper)
    meshActor.GetProperty().SetEdgeColor(0, 0, 1)
    meshActor.GetProperty().SetInterpolationToFlat()
    meshActor.GetProperty().SetRepresentationToWireframe()

    boundaryMapper = vtk.vtkPolyDataMapper()
    if vtk.VTK_MAJOR_VERSION <= 5:
        boundaryMapper.SetInputConnection(boundary.GetProducerPort())
    else:
        boundaryMapper.SetInputData(boundary)

    boundaryActor = vtk.vtkActor()
    boundaryActor.SetMapper(boundaryMapper)
    boundaryActor.GetProperty().SetColor(1, 0, 0)

    renderer = vtk.vtkRenderer()
    renderWindow = vtk.vtkRenderWindow()
    renderWindow.AddRenderer(renderer)
    renderWindowInteractor = vtk.vtkRenderWindowInteractor()
    renderWindowInteractor.SetRenderWindow(renderWindow)
    renderer.AddActor(meshActor)
    renderer.AddActor(boundaryActor)
    renderer.SetBackground(.2, .3, .4)

    renderWindowInteractor.Initialize()
    renderWindow.Render()
    renderWindowInteractor.Start()


def plot3D(vxyz, triangles,
           coordSys='Cartesian',
           raised=True,
           depRange=[-40, 0],
           ambient=0.9,
           diffuse=0.4,
           colormap=vv.CM_JET,
           faceShading='smooth',
           edgeColor=(0.5, 0.5, 0.5, 1),
           edgeShading='smooth',
           faceColor=(1, 1, 1, 1),
           shininess=50,
           specular=0.35,
           emission=0.45):
    # false scale z
    vxyz[:,2]=vxyz[:,2]*10
    zbound = vxyz[:, 2].max()

    # Get axes
    ax = vv.gca()

    ms = vv.Mesh(ax, vxyz, faces=triangles)  # , normals=vxyz
    ms.SetValues(np.array(vxyz[:, 2], dtype=np.float) / zbound)
    ms.ambient = ambient
    ms.diffuse = diffuse
    ms.colormap = colormap
    ms.faceShading = faceShading
    ms.edgeColor = edgeColor
    ms.edgeShading = edgeShading
    ms.faceColor = faceColor
    ms.shininess = shininess
    ms.specular = specular
    ms.emission = emission
    ax.SetLimits(rangeX=[vxyz[:, 0].min(), vxyz[:, 0].max()],
                 rangeY=[vxyz[:, 1].min(), vxyz[:, 1].max()],
                 rangeZ=[vxyz[:, 2].min(), vxyz[:, 2].max()])


def writeobj(vertices, triangles, filename):
    with open(filename, 'w') as f:
        for vertex in vertices:
            f.write('v {0} {1} {2}\n'.format(vertex[0], vertex[1], vertex[2]))

        for triangle in triangles:
            f.write('f {0} {1} {2}\n'.format(triangle[0] + 1, triangle[1] + 1, triangle[2] + 1))


def openfiles(filepaths):
    pixelsize = Triangulator.parameters.child('pixelsize').value()
    for path in filepaths:
        points, triangles = loadafmasmesh(path)

        displaypoints = points/pixelsize
        displaypoints[:,2]*=10
        mesh = gl.GLMeshItem(vertexes=displaypoints,
                             faces=triangles,
                             smooth=False,
                             shader='shaded',
                             glOptions='opaque',
                             drawEdges=True,
                             edgeColor=(1,1,1,1))
        for item in Triangulator.centerwidget.items:
            Triangulator.centerwidget.removeItem(item)
        dx,dy,dz=0,0,0
        # dx=-img.shape[0]/2
        # dy=-img.shape[1]/2
        # dz=-np.average(img)
        mesh.translate(dx,dy,dz,local=True)
        Triangulator.centerwidget.addItem(mesh)

        writeobj(points,triangles,os.path.splitext(path)[0]+'.obj')


Triangulator = base.EZplugin(name='Triangulator',
                             parameters=[{'name': 'gaussian', 'value': 5, 'type': 'int'},
                                         {'name': 'flatten', 'value': False, 'type': 'bool'},
                                         {'name': 'pixelsize', 'value': 1, 'type': 'int'},
                                         {'name': 'Target decimation', 'value': 1, 'type': 'int'},
                                         {'name': 'Display scale', 'value': 1, 'type': 'int'}],
                             openfileshandler=openfiles,
                             centerwidget=gl.GLViewWidget,
                             bottomwidget=lambda: None)
