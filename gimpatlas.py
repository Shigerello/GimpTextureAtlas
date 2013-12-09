#!/usr/bin/env python
# -*- coding: utf-8 -*-

#region IBM common public license v1
"""
This library is free software; you can redistribute it and/or
modify it under the terms of the IBM Common Public License as
published by the IBM Corporation; either version 1.0 of the
License, or (at your option) any later version.
 
This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
IBM Common Public License for more details.
 
You should have received a copy of the IBM Common Public
License along with this library


Copyright (c) of the original code held by Eniko,
obtained on 2013 Dec. 12 from:
http://projectdrake.net/blog/2008/12/29/bin-packing-rectangle-packing-and-image-atlasses/

Copyright (c) of the edited part is held by Shigekazu Fukui
"""

from bisect import bisect_left
 
class OutOfSpaceError(Exception): pass
 
class Point(object):
    def __init__(self, x, y):
        self.x = x
        self.y = y
 
    def __cmp__(self, other):
        """Compares the starting position of height slices"""
        return self.x - other.x
 
class RectanglePacker(object):
    """Base class for rectangle packing algorithms
 
    By uniting all rectangle packers under this common base class, you can
    easily switch between different algorithms to find the most efficient or
    performant one for a given job.
 
    An almost exhaustive list of packing algorithms can be found here:
 
http://www.csc.liv.ac.uk/~epa/surveyhtml.html"""
 
    def __init__(self, packingAreaWidth, packingAreaHeight):
        """Initializes a new rectangle packer
 
        packingAreaWidth: Maximum width of the packing area
        packingAreaHeight: Maximum height of the packing area"""
        self.packingAreaWidth = packingAreaWidth
        self.packingAreaHeight = packingAreaHeight
 
    def Pack(self, rectangleWidth, rectangleHeight):
        """Allocates space for a rectangle in the packing area
 
        rectangleWidth: Width of the rectangle to allocate
        rectangleHeight: Height of the rectangle to allocate
 
        Returns the location at which the rectangle has been placed"""
        point = self.TryPack(rectangleWidth, rectangleHeight)
 
        if not point:
            raise OutOfSpaceError("Rectangle does not fit in packing area")
 
        return point
 
    def TryPack(self, rectangleWidth, rectangleHeight):
        """Tries to allocate space for a rectangle in the packing area
 
        rectangleWidth: Width of the rectangle to allocate
        rectangleHeight: Height of the rectangle to allocate
 
        Returns a Point instance if space for the rectangle could be allocated
        be found, otherwise returns None"""
        raise NotImplementedError
 
class CygonRectanglePacker(RectanglePacker):
    """
    Packer using a custom algorithm by Markus 'Cygon' Ewald
 
    Algorithm conceived by Markus Ewald (cygon at nuclex dot org), though
    I'm quite sure I'm not the first one to come up with it :) 
 
    The algorithm always places rectangles as low as possible in the packing
    area. So, for any new rectangle that is to be added, the packer has to
    determine the X coordinate at which the rectangle can have the lowest
    overall height without intersecting any other rectangles.
 
    To quickly discover these locations, the packer uses a sophisticated
    data structure that stores the upper silhouette of the packing area. When
    a new rectangle needs to be added, only the silouette edges need to be
    analyzed to find the position where the rectangle would achieve the lowest"""
 
    def __init__(self, packingAreaWidth, packingAreaHeight):
        """Initializes a new rectangle packer
 
        packingAreaWidth: Maximum width of the packing area
        packingAreaHeight: Maximum height of the packing area"""
        RectanglePacker.__init__(self, packingAreaWidth, packingAreaHeight)
 
        # Stores the height silhouette of the rectangles
        self.heightSlices = []
 
        # At the beginning, the packing area is a single slice of height 0
        self.heightSlices.append(Point(0,0))
 
    def TryPack(self, rectangleWidth, rectangleHeight):
        """Tries to allocate space for a rectangle in the packing area
 
        rectangleWidth: Width of the rectangle to allocate
        rectangleHeight: Height of the rectangle to allocate
 
        Returns a Point instance if space for the rectangle could be allocated
        be found, otherwise returns None"""
        placement = None
 
        # If the rectangle is larger than the packing area in any dimension,
        # it will never fit!
        if rectangleWidth > self.packingAreaWidth or rectangleHeight > \
        self.packingAreaHeight:
            return None
 
        # Determine the placement for the new rectangle
        placement = self.tryFindBestPlacement(rectangleWidth, rectangleHeight)
 
        # If a place for the rectangle could be found, update the height slice
        # table to mark the region of the rectangle as being taken.
        if placement:
            self.integrateRectangle(placement.x, rectangleWidth, placement.y \
            + rectangleHeight)
 
        return placement
 
    def tryFindBestPlacement(self, rectangleWidth, rectangleHeight):
        """Finds the best position for a rectangle of the given dimensions
 
        rectangleWidth: Width of the rectangle to find a position for
        rectangleHeight: Height of the rectangle to find a position for
 
        Returns a Point instance if a valid placement for the rectangle could
        be found, otherwise returns None"""
        # Slice index, vertical position and score of the best placement we
        # could find
        bestSliceIndex = None # Slice index where the best placement was found
        bestSliceY = 0 # Y position of the best placement found
        bestScore = self.packingAreaWidth * self.packingAreaHeight # lower == better!
 
        # This is the counter for the currently checked position. The search
        # works by skipping from slice to slice, determining the suitability
        # of the location for the placement of the rectangle.
        leftSliceIndex = 0
 
        # Determine the slice in which the right end of the rectangle is located
        rightSliceIndex = bisect_left(self.heightSlices, Point(rectangleWidth, 0))
 
        while rightSliceIndex <= len(self.heightSlices):
            # Determine the highest slice within the slices covered by the
            # rectangle at its current placement. We cannot put the rectangle
            # any lower than this without overlapping the other rectangles.
            highest = self.heightSlices[leftSliceIndex].y
            for index in range(leftSliceIndex + 1, rightSliceIndex):
                if self.heightSlices[index].y > highest:
                    highest = self.heightSlices[index].y
 
            # Only process this position if it doesn't leave the packing area
            if highest + rectangleHeight < self.packingAreaHeight:
                score = highest
 
                if score < bestScore:
                    bestSliceIndex = leftSliceIndex
                    bestSliceY = highest
                    bestScore = score
 
            # Advance the starting slice to the next slice start
            leftSliceIndex += 1
            if leftSliceIndex >= len(self.heightSlices):
                break
 
            # Advance the ending slice until we're on the proper slice again,
            # given the new starting position of the rectangle.
            rightRectangleEnd = self.heightSlices[leftSliceIndex].x + rectangleWidth
            while rightSliceIndex <= len(self.heightSlices):
                if rightSliceIndex == len(self.heightSlices):
                    rightSliceStart = self.packingAreaWidth
                else:
                    rightSliceStart = self.heightSlices[rightSliceIndex].x
 
                # Is this the slice we're looking for?
                if rightSliceStart > rightRectangleEnd:
                    break
 
                rightSliceIndex += 1
 
            # If we crossed the end of the slice array, the rectangle's right
            # end has left the packing area, and thus, our search ends.
            if rightSliceIndex > len(self.heightSlices):
                break
 
        # Return the best placement we found for this rectangle. If the
        # rectangle didn't fit anywhere, the slice index will still have its
        # initialization value of %None and we can report that no placement
        # could be found.
        if bestSliceIndex == None:
            return None
        else:
            return Point(self.heightSlices[bestSliceIndex].x, bestSliceY)
 
    def integrateRectangle(self, left, width, bottom):
        """Integrates a new rectangle into the height slice table
 
        left: Position of the rectangle's left side
        width: Width of the rectangle
        bottom: Position of the rectangle's lower side"""
        # Find the first slice that is touched by the rectangle
        startSlice,hit = binary_search(self.heightSlices, Point(left, 0))
 
        # Did we score a direct hit on an existing slice start?
        if hit:
            # We scored a direct hit, so we can replace the slice we have hit
            firstSliceOriginalHeight = self.heightSlices[startSlice].y
            self.heightSlices[startSlice] = Point(left, bottom)
        else: # No direct hit, slice starts inside another slice
            # Add a new slice after the slice in which we start
            firstSliceOriginalHeight = self.heightSlices[startSlice - 1].y
            self.heightSlices.insert(startSlice, Point(left, bottom))
 
        right = left + width
        startSlice += 1
 
        # Special case, the rectangle started on the last slice, so we cannot
        # use the start slice + 1 for the binary search and the possibly
        # already modified start slice height now only remains in our temporary
        # firstSliceOriginalHeight variable
        if startSlice >= len(self.heightSlices):
            # If the slice ends within the last slice (usual case, unless it
            # has the exact same width the packing area has), add another slice
            # to return to the original height at the end of the rectangle.
            if right < self.packingAreaWidth:
                self.heightSlices.append(Point(right, firstSliceOriginalHeight))
        else: # The rectangle doesn't start on the last slice
            endSlice,hit = binary_search(self.heightSlices, Point(right,0), \
            startSlice, len(self.heightSlices))
 
            # Another direct hit on the final slice's end?
            if hit:
                del self.heightSlices[startSlice:endSlice]
            else: # No direct hit, rectangle ends inside another slice
                # Find out to which height we need to return at the right end of
                # the rectangle
                if endSlice == startSlice:
                    returnHeight = firstSliceOriginalHeight
                else:
                    returnHeight = self.heightSlices[endSlice - 1].y
 
                # Remove all slices covered by the rectangle and begin a new
                # slice at its end to return back to the height of the slice on
                # which the rectangle ends.
                del self.heightSlices[startSlice:endSlice]
                if right < self.packingAreaWidth:
                    self.heightSlices.insert(startSlice, Point(right, returnHeight))
#endregion

#region MIT license
"""
The MIT license

Copyright (c) 2013 Shigekazu Fukui (shigerello@gmail.com)

Permission is hereby granted, free of charge, to any person obtaining a 
copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the Software 
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all 
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A 
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION 
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE 
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. 
"""
"""
GIMP plugin to export layers into a texture atlas image and map files.

@author: Shigekazu Fukui 
"""

from os import getcwd
from os.path import join, splitext
from gimpfu import *

class TextureRect(object):
    def __init__(self, x, y, width, height, name):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.name = name
    
    # Official & debugging string representation
    def __repr__(self):
        res = self.__class__.__name__
        res += "@0x{id}".format(id = id(self))
        res += ("(x={x}, y={y}, width={w}, height={h}, name=\"{name}\" )".
                format(x = self.x, y = self.y, w = self.width, h = self.height,
                       name = self.name)
                )
        return res
    
    # Casual string representation
    def __str__(self):
        res = ("{x} {y} {w} {h} \"{name}\"".
               format(x = self.x, y = self.y, w = self.width, h = self.height,
                      name = self.name)
               )
        return res
 
'''
TODO: "trim" (trimming blank rim) is not implemented.
'''
def generate_atlas_and_map(timg, tdrawable,
                           output_name, output_dir,
                           only_visible, pow2, max_w, max_h, trim, pad):
    # Logic check of args
    if output_name is None:
        pdb.gimp_message("You must specify output file name!")
    if output_dir is None:
        pdb.gimp_message("You must specify export path!")
#     if not isinstance(only_visible, bool):
#         pdb.gimp_message("Export setting (layer visibility) must be true or false!")
    if max_w < 1 or max_h < 1:
        pdb.gimp_message("Maximum width or height must be larger than or equal to 1!");
    if pad < 0:
        pdb.gimp_message("Padding must be non-negative!");
#     if not isinstance(pow2, bool):
#         pdb.gimp_message("Export setting (power-of-2) must be true or false!")
    
    # Prepare a working image, duplicating the original image.
    img_w = nearest_pow2(max_w) if pow2 else max_w
    img_h = nearest_pow2(max_h) if pow2 else max_h
    tmp_img = pdb.gimp_image_duplicate(timg)
    
    # Prepare a rectangle packer.
    rect_packer = CygonRectanglePacker(img_w, img_h)
    
    #
    # Determine the packing position of textures (layers).
    #
    
    # Initialize progress bar.
    pdb.gimp_progress_init("Progress", None)
    
    layer_len = len(tmp_img.layers)
    tex_rects = []
    for layer,i in zip(tmp_img.layers, range(layer_len)):
        # if the texture is invisible but was requested to be included into
        # the texture atlas, make it visible.
        #
        # We can always assign %True to %layer.visible if %only_visible is %True, but
        # underlying operation for changing %layer.visible is costly (it involves image
        # redraw). Thus, it assigns %True to %layer.visible only if %layer.visible and 
        # %only_visible are %False.
        if not (layer.visible or only_visible):
            layer.visible = True
        if layer.visible:
            # Actual rectangle + padding
            pos = rect_packer.TryPack(layer.width + pad, layer.height + pad)
            if pos:
                # Yay, one layer down! Rectangle packing succeeded.
                
                # Update progress bar (how many textures were processed?)
                pdb.gimp_progress_update(float(i)/layer_len)
                
                # Register packing position, texture size, and texture name.
                tex_rects.append(TextureRect(pos.x, pos.y,
                                             layer.width, layer.height,
                                             layer.name.decode("utf_8") ))
                
                # Move the texture to its packing position.
                offx,offy = layer.offsets
                pdb.gimp_layer_translate(layer, pos.x - offx, pos.y - offy)
            else:
                # Ouch, this layer is tough! Rectangle packing failed.
                
                # Stop progress bar
                pdb.gimp_progress_end()
                
                pdb.gimp_message("Error: failed to pack layer \"%s\" into "
                                 "the texture atlas, process aborted.\n"
                                 "Possible cause: the layer is too big to fit." %
                                 layer.name.decode("utf_8") );
                # Abort 
                return
    # Merge textures into a texture atlas (visible layers into a single layer).
    tmp_drawable = pdb.gimp_image_merge_visible_layers(tmp_img, EXPAND_AS_NECESSARY)
    
    # Based on the size of the result layer, dynamically trim the size of the image
    # if requested.
    if trim:
        # Trimming is requested.
        crop_w = nearest_pow2(tmp_drawable.width) if pow2 else tmp_drawable.width
        crop_h = nearest_pow2(tmp_drawable.height) if pow2 else tmp_drawable.height
        pdb.gimp_image_resize(tmp_img, crop_w, crop_h, 0, 0)
    else:
        # No dynamic trimming of the image, just accepting the initially determined size.
        pdb.gimp_image_resize(tmp_img, img_w, img_h, 0, 0)
    # The size of the image was finally determined. Reflect it to the size of layer.
    pdb.gimp_layer_resize_to_image_size(tmp_drawable)
    
    #
    # Output the result
    #
    
    # %output_name is expected to have image extension.
    output_atlas = join(output_dir, output_name).decode("utf_8")
    output_map = splitext(output_atlas)[0] + "_map.txt"
    
    # Generate a map file
    # TODO: sort by rectangle position
    with open(output_map, "w") as f:
        for rect in tex_rects:
            # See TextureRect.__str__ for string representation of TextureRect.
            f.write(str(rect) + "\n")
        f.flush()
    
    # Generate a texture atlas image
    pdb.gimp_file_save(tmp_img, tmp_drawable, output_atlas, splitext(output_atlas)[0])
    # Delete the working image
    pdb.gimp_image_delete(tmp_img)

# Calculate the nearest power-of-2 (including itself)
# http://en.wikipedia.org/wiki/Power_of_two
def nearest_pow2(n):
    m = n & (n-1)
    # It's already pow2. Simply returns it.
    if not m:
        return n
    n = m
    m = n & (n-1)
    while m:
        n = m
        m = n & (n-1)
    return n << 1

def binary_search(a, x, lo = 0, hi = None):
    # %hi defaults to %len(a)
    if hi is None:
        hi = len(a)
    # Find insertion position
    pos = bisect_left(a, x, lo, hi)
    # 2nd element is True if %x was already in %a
    return (pos, pos != hi and a[pos] == x)

# See gimpfu.py for info on register()
register(
    proc_name =  "python-fu-atlas",
    blurb =      "Export layers into a texture atlas image and create a map file",
    help =       "Export layers into a texture atlas image and create a map file. "
                 "Image format of the texture atlas is automatically guessed by "
                 "file extension of the output file name.",
    author =     "Shigekazu Fukui",
    copyright =  "(c) 2013 MIT license and IBM CPL v1",
    date =       "December 2013",
    label =      "_Texture atlas...",
    imagetypes = "*",
    params =     [
        (PF_IMAGE, "image", "Input image", None),
        (PF_DRAWABLE, "drawable", "Input drawable", None),
        (PF_STRING, "output_name", "Filename\n(Image format is guessed from its extension)",
         "generated_texatlas.png"),
        (PF_DIRNAME, "output_dir", "Export path", getcwd()), 
        (PF_BOOL, "only_visible", "Exports only visible layers?", True),
        (PF_BOOL, "pow2", "Output dimensions must be power-of-2?\n(Overrides preferred width and height, also trimming)", True),
        (PF_INT, "max_w", "Preferred width\n(Or the nearest power-of-2)", 4096),
        (PF_INT, "max_h", "Preferred height\n(Or the nearest power-of-2)", 4096),
        (PF_BOOL, "trim", "Trim output dimensions?\n(Conforms to power-of-2 if it's true)", True),
        (PF_INT, "pad", "Padding between adjacent images", 0)
    ],
    results =    [],
    function =   generate_atlas_and_map,
    menu =       "<Image>/Tools"
)

main()
#endregion
