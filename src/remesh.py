#! /usr/bin/env python

# from image_load import *
import loader
from cWarpImage import warp_image
import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree
from scipy.ndimage.filters import gaussian_filter
from pyFAI import geometry
from pyFAI import detectors
from matplotlib import pylab


def gaussian(pts, p0, h):
    t = 0.5 * ((pts[:, 0] - p0[0]) ** 2 + (pts[:, 1] - p0[1]) ** 2) / h ** 2
    k = 0.5 / h ** 2 / np.pi
    return k * np.exp(-t)


def remap(xcrd, ycrd, tree, img, radius):
    qimg = np.zeros(xcrd.shape, dtype=float)
    it = np.nditer([xcrd, ycrd], flags=['multi_index'])
    while not it.finished:
        pt = it[:2]
        n = tree.query_ball_point(pt, radius)
        if len(n) > 0:
            i, j = it.multi_index
            w = gaussian(tree.data[n, :], pt, radius)
            qimg[i, j] = np.dot(img[n], w) / w.sum()
        it.iternext()
    return qimg


def transform(ny, nz, geometry, alphai):
    """
    :type geometry: P
    :param ny:
    :param nz:
    :param geometry: pyFAI.Geometry
    :param alphai:
    :return:
    """
    sdd = geometry.get_dist() * 1.0E+10
    wave = geometry.get_wavelength()

    # transform into q-space
    y = np.arange(ny)
    z = np.arange(nz)
    y, z = np.meshgrid(y, z)
    # print(geometry.get_poni1() / geometry.get_pixel1(), geometry.get_poni2() / geometry.get_poni2())
    y = (y - (
    geometry.get_poni2() / geometry.get_pixel2())) * geometry.get_pixel2() * 1.0E+10  #1679-geometry.get_poni2()/geometry.get_pixel2())
    print(geometry.get_pixel1())
    z = (z - (
        nz - geometry.get_poni1() / geometry.get_pixel1())) * geometry.get_pixel1() * 1.0E+10  # 1475-(geometry.get_poni1()/geometry.get_pixel1())


    tmp = np.sqrt(y ** 2 + sdd ** 2)
    cos2theta = sdd / tmp
    sin2theta = y / tmp
    tmp = np.sqrt(z ** 2 + sdd ** 2)
    cosalpha = sdd / tmp
    sinalpha = z / tmp
    K0 = 2. * np.pi / wave

    qx = K0 * (cosalpha * cos2theta - np.cos(alphai))
    qy = K0 * cosalpha * sin2theta
    qz = K0 * (sinalpha + np.sin(alphai))
    return qx, qy, qz


def remesh(filename, geometry):
    # read image
    img, paras = loader.loadpath(filename)


    # read incident angle
    if paras is None:
        print "Failed to read incident angle"
        return img
    alphai = paras["Sample Alpha Stage"] / 360.0 * 2 * np.pi

    nz, ny = img.shape
    qx, qy, qz = transform(ny, nz, geometry, alphai)
    qr = np.sqrt(qx ** 2 + qy ** 2) * np.sign(qy)

    # pylab.plot(qr,qz,'ko')
    #pylab.savefig('testimage.png')
    #misc.imsave('testimage.png')
    # interpolation
    xcrd = np.linspace(qr.min(), qr.max(), ny)
    ycrd = np.linspace(qz.min(), qz.max(), nz)
    rad = 0.5 * np.sqrt((xcrd[1] - xcrd[0]) ** 2 + (ycrd[1] - ycrd[0]) ** 2)
    xcrd, ycrd = np.meshgrid(xcrd, ycrd)

    # try faster c/openmp remesh
    try:
        qimg = warp_image(
            img.astype(
                np.float32), qr.astype(
                np.float32), qz.astype(
                np.float32), xcrd.astype(
                np.float32), ycrd.astype(
                np.float32), 0)
    except:
        print 'Warning: cWarpImage failed. Falling back to python remap'
        qimg = np.zeros((nz, ny), dtype=float)
        im1 = img.ravel()
        pts = np.zeros((ny * nz, 2), dtype=float)
        pts[:, 0] = qr.ravel()
        pts[:, 1] = qz.ravel()

        # put data into a KDTree
        tree = cKDTree(pts, leafsize=10)

        # remesh in python-slow
        qimg = remap(xcrd, ycrd, tree, im1, rad)

    #qimg = gaussian_filter(qimg, sigma=1)


    return np.rot90(qimg, 3)


def remesh_mask(agbfile, agb):
    # read incedent angle
    alphai = get_incedent_angle(agbfile)
    if alphai is None:
        print "Failed to read incident angle"

    img = agb.mask_
    nz, ny = img.shape
    qx, qy, qz = transform(ny, nz, agb, alphai)
    qr = np.sqrt(qx ** 2 + qy ** 2) * np.sign(qy)
    qrange = [qr.min(), qr.max(), qz.min(), qz.max()]
    agb.setQrange(qrange)

    # interpolation
    xcrd = np.linspace(qr.min(), qr.max(), ny)
    ycrd = np.linspace(qz.min(), qz.max(), nz)
    rad = 0.5 * np.sqrt((xcrd[1] - xcrd[0]) ** 2 + (ycrd[1] - ycrd[0]) ** 2)
    xcrd, ycrd = np.meshgrid(xcrd, ycrd)

    # try faster c/openmp remesh
    try:
        qimg = warp_image(
            img.astype(
                np.float32), qr.astype(
                np.float32), qz.astype(
                np.float32), xcrd.astype(
                np.float32), ycrd.astype(
                np.float32), 0)
    except:
        print 'Warning: cWarpImage failed. Falling back to python remap'
        qimg = np.zeros((nz, ny), dtype=float)
        im1 = img.ravel()
        pts = np.zeros((ny * nz, 2), dtype=float)
        pts[:, 0] = qr.ravel()
        pts[:, 1] = qz.ravel()

        # put data into a KDTree
        tree = cKDTree(pts, leafsize=10)

        # remesh in python-slow
        qimg = remap(xcrd, ycrd, tree, im1, rad)

    qimg = np.round(qimg)
    return qimg.astype(bool).astype(np.float32)


if __name__ == '__main__':
    geo = geometry.Geometry(0.298, 29 * .000172, 620 * .000172, 0, 0, 0, .000172, .000172,
                            detector=detectors.Pilatus2M(), wavelength=0.124)
    # img,param= loader.loadpath('../samples/AgB_00017.edf')
    img = remesh('../samples/AgB_00016.edf', geo)
    # write PNG file
    plt.imshow(np.log(img + 3))
    plt.savefig('testimage.png')
    print(':)')
    plt.close()

