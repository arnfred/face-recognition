"""
Python module for dealing with the 3D objects dataset published here:
http://www.vision.caltech.edu/pmoreels/Datasets/TurntableObjects/

Jonas Toft Arnfred, 2013-11-18
"""

####################################
#                                  #
#            Imports               #
#                                  #
####################################

import cv2
import numpy
import features
import os
import fnmatch
import display
import matching
import mirrormatch
import colors
import random

####################################
#                                  #
#           Functions              #
#                                  #
####################################

def get_turntable_path(image_set, object_type, angle, camera_position, turntable_dir = "../../turntable") :
    """ Returns path to image of image_set and object_type where:
        image_set : Int (the main folder)
        object_type : String (the object pictured on the turntable)
        angle : Int (Rotation in degrees. Must be divisible by 5)
        camera_position : String ("Top" or "Bottom")
        turntable_dir : String (path to folder with image sets)
    """
    directory = "%s/imageset_%i/%s/%s" % (turntable_dir, image_set, object_type, camera_position)
    file_names = os.listdir(directory)
    file_glob = "img_1-%03i_*_0.JPG" % angle
    image_paths = sorted(fnmatch.filter(file_names, file_glob))
    return "%s/%s" % (directory, image_paths[0])



def load_calibration_image(image_set, angle, camera_position, pattern_position, scale = None, turntable_dir = "../../turntable") :
    """ Loads a checkerboard pattern image taken from the same angle and rotation:
        image_set : Int (the image set folder)
        angle : Int (Rotation in degrees. Must be divisible by 5)
        pattern_position : String (either: "flat", "angled" or "steep")
        scale : Float (the calibration images are double size, so put 2.0)
        turntable_dir : String (path to folder with image sets)
    """
    pattern_index = { "flat" : 0, "steep" : 1, "angled" : 2 }[pattern_position]
    image_index = (angle / 5) * 3 + 1 + pattern_index
    image_path = "%s/imageset_%i/%s/%s/calib%i.jpg" % (turntable_dir, image_set, "Calibration", camera_position, image_index)
    img = cv2.imread(image_path)
    if not scale == None :
        img_scaled = cv2.resize(img, (int(img.shape[1] / scale), int(img.shape[0] / scale)))
        return img_scaled
    else :
        return img



# Get calibration points
def get_calibration_points(img, pattern_position) :
    """ Returns the calibration points from an image with the checkerboard pattern """
    if pattern_position == "steep" :
        grid_size = (9, 13)
    else :
        grid_size = (13, 9)
    success, cv_points = cv2.findChessboardCorners(img, grid_size, flags = cv2.CALIB_CB_FILTER_QUADS)
    if not success :
        raise Exception("Can't get lock on chess pattern for img")
    points = numpy.array([[p[0][0], p[0][1]] for p in cv_points])
    #print(points)
    return points# Get calibration points



def get_foundamental_matrix(image_set, angles, camera_position, scale = 2.0, return_points = False) :
    """ Returns fundamental matrix:
        image_set : Int (the image set folder)
        angles : (Int, Int) (two angles in degrees. Must be divisible by 5)
        camera_position : String (either "Top" or "Bottom")
        scale : Float (scale of images compared to calibration images)
        return_points : Boolean (set to True if you need the calibration points)
    """
    
    # Fetch all images for the angle pair
    img1_flat = load_calibration_image(image_set, angles[0], camera_position[0], "flat")
    img2_flat = load_calibration_image(image_set, angles[1], camera_position[1], "flat")
    img1_angled = load_calibration_image(image_set, angles[0], camera_position[0], "angled")
    img2_angled = load_calibration_image(image_set, angles[1], camera_position[1], "angled")
    img1_steep = load_calibration_image(image_set, angles[0], camera_position[0], "steep")
    img2_steep = load_calibration_image(image_set, angles[1], camera_position[1], "steep")
    
    # Fetch points for all images
    points1_flat = get_calibration_points(img1_flat, "flat")
    points2_flat = get_calibration_points(img2_flat, "flat")
    points1_angled = get_calibration_points(img1_angled, "angled")
    points2_angled = get_calibration_points(img2_angled, "angled")
    points1_steep = get_calibration_points(img1_steep, "steep")
    points2_steep = get_calibration_points(img2_steep, "steep")
    
    # Concatenate point sets
    points1 = numpy.concatenate((points1_flat, points1_angled, points1_steep)) / scale
    points2 = numpy.concatenate((points2_flat, points2_angled, points2_steep)) / scale
    
    # Find fundamental matrix based on points
    F, inliers = cv2.findFundamentalMat(points1, points2, method = cv2.FM_RANSAC)
    
    # return matrix with or without points
    if return_points :
        return F, (points1_flat / scale, points2_flat / scale)
    else :
        return F



def epilines(img, points, lines, size = (12, 12)) :
    """ Draws a set of epilines and points on an image """
    # Generate figure
    fig = figure(figsize=size)
    imshow(img)
    
    # Get x values
    min_x = 0
    max_x = img.shape[1]
    min_y = 0
    max_y = img.shape[0]
    
    # Limit plot
    xlim(0,max_x)
    ylim(max_y-1,0)
    
    # plot lines
    for l, c in zip(lines, colors.get()) :
        # get line functions
        line_fun = lambda x : (-1 * l[0] * x - l[2]) / (float(l[1]))
        # plot line
        plot([0, max_x], [line_fun(0), line_fun(max_x)], color=c, marker='_')
    
    # plot points
    for p, c in zip(points, colors.get()) :
        # Plot feature match point
        plot(p[0], p[1], color=c, marker='o')   



def match_distances(matches, angles, match_object, image_set, check_threshold) :
    """ Find the distance of matches as measured against two intersection epipolar lines:
        matches : List[(Pos,Pos)] (List of corresponding coordinates in two images)
        angles : (Int, Int) (two angles in degrees. Must be divisible by 5)
        match_object : String (The type of 3d model we are looking at)
        image_set : Int (The image set where this 3d model is found)
        check_threshold : Float (The threshold for a correct correspondence)
    """
    
    # Get features in B
    path_B = get_turntable_path(image_set, match_object, angles[0], "Top")
    img_B = features.loadImage(path_B)
    
    # Find fundamental matrices
    F_AC = get_foundamental_matrix(image_set, (angles[0], angles[1]), ("Bottom", "Bottom"), scale = 2.0)
    F_AB = get_foundamental_matrix(image_set, (angles[0], angles[0]), ("Bottom", "Top"), scale = 2.0)
    F_BC = get_foundamental_matrix(image_set, (angles[0], angles[1]), ("Top", "Bottom"), scale = 2.0)
    
    # return distances
    return list(calc_match_distances(matches, img_B, F_AB, F_AC, F_BC, check_threshold))



def calc_match_distances(matches, img_B, F_AB, F_AC, F_BC, check_threshold) :
    """ Helper function for match_distances()
        Check ground truth for a set of matches given fundamental matrices,
        As proposed in: "Evaluation of Features Detectors and Descriptors 
        based on 3D objects by Pierre Moreels and Peitro Perona.
    """
    
    # Calculate distance between line and 2D-point
    def dist(line, point) :
        return numpy.abs(line.dot([point[0], point[1], 1]))
    
    # return epipolar line
    def get_lines(points, F) :
        return [l[0] for l in cv2.computeCorrespondEpilines(points.reshape(-1, 1, 2), 1, F)]
    
    # Find points that are on l_AB
    points_A = numpy.array([m[0] for m in matches], dtype=numpy.float32)
    points_C = numpy.array([m[1] for m in matches], dtype=numpy.float32)
    lines_AB = get_lines(points_A, F_AB)
    lines_AC = get_lines(points_A, F_AC)
    
    # Collect features from B, so we can check the match there
    feature_pos_B = features.getPositions(features.getKeypoints(img_B))

    for p_A, p_C, l_AB, l_AC in zip(points_A, points_C, lines_AB, lines_AC) :
        
        # Is p_C on l_AC?
        min_dist = dist(l_AC, p_C)
        if min_dist < check_threshold :
            
            # Collect all features in B that are on l_AB:
            points_B = numpy.array([p_B for p_B in feature_pos_B if dist(l_AB, p_B) < check_threshold], dtype=numpy.float32)
            
            # Check if points match up
            if len(points_B) > 0 :
                lines_BC = get_lines(points_B, F_BC)
                min_dist = max((numpy.min([dist(l_BC, p_C) for l_BC in lines_BC]), min_dist))
                
        yield min_dist
