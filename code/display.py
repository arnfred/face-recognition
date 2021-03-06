"""
Python module for use with openCV and features.py to display keypoints
and their links between images

Jonas Toft Arnfred, 2013-03-08
"""

####################################
#                                  #
#            Imports               #
#                                  #
####################################

import cv2
import pylab
import numpy
import scipy
import math
import louvain
import colors
import pylab
from scipy.misc import imresize, imread
import Image
from itertools import combinations, groupby, tee, product, combinations_with_replacement, dropwhile
from sklearn import metrics


####################################
#                                  #
#             Images               #
#                                  #
####################################

def appendimages(im1, im2, seperator = 0) :
    """ return a new image that appends the two images side-by-side.
    """

    barrier = numpy.ones((im1.shape[0],seperator)) * 255

    if (im1.shape[0] == im2.shape[0]) :
        tmp = im2

    elif (im1.shape[0] > im2.shape[0]) :
        tmp = numpy.ones((im1.shape[0], im2.shape[1])) * 255
        tmp[0:im2.shape[0], :] = im2

    elif (im1.shape[0] < im2.shape[0]) :
        tmp = numpy.ones((im1.shape[0], im2.shape[1])) * 255
        tmp[0:im1.shape[0], :] = im2[0:im1.shape[0],:]

    else :
        print("Detonating thermo-nuclear devices")

    return numpy.concatenate((im1,barrier, tmp), axis=1)





def keypoints(im, pos) :
    """ show image with features. input: im (image as array), 
        locs (row, col, scale, orientation of each feature) 
    """
    # Plot all keypoints
    pylab.gray()
    pylab.imshow(im)
    #for (x,y), c in zip(pos, colors.get()) :
    for i, (x,y) in enumerate(pos) :
        pylab.plot(x, y, marker='.', color = colors.getRedGreen(float(i+1) / len(pos)))
    pylab.axis('off')
    pylab.show()


def compareKeypoints(im1, im2, pos1, pos2, filename = None, separation = 0) :
    """ Show two images next to each other with the keypoints marked
    """

    # Construct unified image
    im3 = appendimages(im1,im2, separation)

    # Find the offset and add it
    offset = im1.shape[1]
    pos2_o = [(x+offset + separation,y) for (x,y) in pos2]

    # Create figure
    fig = pylab.figure(frameon=False, figsize=(12.0, 8.0))
    #ax = pylab.Axes(fig, [0., 0., 1., 1.])

    # Show images
    pylab.gray()
    pylab.imshow(im3)
    pylab.plot([x for x,y in pos1], [y for x,y in pos1], marker='o', color = '#00aaff', lw=0)
    pylab.plot([x for x,y in pos2_o], [y for x,y in pos2_o], marker='o', color = '#00aaff', lw=0)
    pylab.axis('off')

    pylab.xlim(0,im3.shape[1])
    pylab.ylim(im3.shape[0],0)

    if filename != None :
        fig.savefig(filename, bbox_inches='tight', dpi=300)


def matchPoints(im1, im2, matches, dist = None, filename = None, max_dist = 100, line_width = 0.8, matches_im1 = None, dist_im1 = None, matches_im2 = None, dist_im2 = None) :
    """ show a figure with lines joining the accepted matches in im1 and im2
        input: im1,im2 (images as arrays), locs1,locs2 (location of features), 
        matchscores (as output from 'match'). 
    """

    separation = 20

    # Construct unified image
    im3 = appendimages(im1,im2, separation)

    # Create figure
    fig = pylab.figure(frameon=False, figsize=(12.0, 8.0))
    ax = pylab.Axes(fig, [0., 0., 1., 1.])

    ax.set_axis_off()
    fig.add_axes(ax)

    # Display image
    pylab.gray()
    ax.imshow(im3)

    # Get colors
    if dist != None and len(dist) == len(matches) :
        cs = [colors.getRedGreen(numpy.log(d+1)/numpy.log(max_dist)) for d in dist]
    else :
        cs = ['#00aaff' for m in matches]

    # Get colors for images
    if dist_im1 != None and len(dist_im1) == len(matches_im1) :
        cs_im1 = [colors.getRedGreen(numpy.log(d+1)/numpy.log(max_dist)) for d in dist_im1]
    else :
        cs_im1 = ['#00aaff' for m in matches]
    if dist_im2 != None and len(dist_im2) == len(matches_im2) :
        cs_im2 = [colors.getRedGreen(numpy.log(d+1)/numpy.log(max_dist)) for d in dist_im2]
    else :
        cs_im2 = ['#00aaff' for m in matches]
    
    # Plot all lines
    offset_x = im1.shape[1]
    for i,((x1,y1),(x2,y2)) in enumerate(matches) :
        ax.plot([x1, x2+offset_x + separation], [y1,y2], color=cs[i], lw=line_width)
    if matches_im1 != None :
        for i,((x1,y1),(x2,y2)) in enumerate(matches_im1) :
            ax.plot([x1, x2], [y1,y2], color=cs_im1[i], lw=line_width)
    if matches_im2 != None :
        for i,((x1,y1),(x2,y2)) in enumerate(matches_im2) :
            ax.plot([x1+offset_x + separation, x2+offset_x + separation], [y1,y2], color=cs_im2[i], lw=line_width)

    pylab.xlim(0,im3.shape[1])
    pylab.ylim(im3.shape[0],0)

    if filename != None :
        fig.savefig(filename, bbox_inches='tight', dpi=72)



def matchesWithMask(images, keypoints, matchPos, mask) :
    """ Display only those matches that are masked
        input: images [A list containing two images] The two images you want to plot
               keypoints [A list containing two keypoints] The keypoints in use
               matchPos [A list of indices] matchPos[0] is the keypoint in keypoints[1] 
                                            that match with keypoints[0][0]
               mask [array of booleans] If mask[i] == true then keypoints[0][i] is displayed
    """
    # Take the n highest scoring points and plot them
    masked_matchPos = [m if b else None for (m,b) in zip(matchPos, mask)]

    # Show result
    matchPoints(images[0], images[1], keypoints[0], keypoints[1], masked_matchPos)



####################################
#                                  #
#            Plotting              #
#                                  #
####################################


def barWithMask(X,Y,mask,color='blue') :
    """ Show a barplot, but make the bars corresponding to the mask stand out
        input: X [array of numbers] (x-values of the data)
               Y [array of numbers] (y-values of the data)
               mask [array of booleans] (if mask[i] == true, then Y[i] is emphatized)
               color [string] (the preferred color)
    """
    # Show scores in subplot
    margin = (max(Y) - min(Y)) * 0.15
    x_min, x_max = min(X),max(X)
    y_min, y_max = min(Y)-margin, max(Y)+margin

    alpha = [0.5, 0.7]
    alphaMap = [alpha[1] if b else alpha[0] for b in mask]
    for x, y, a in zip(X,Y,alphaMap) :
        pylab.bar(x, y, color=color, alpha=a)
        
    pylab.xlim(x_min, x_max)
    pylab.ylim(y_min, y_max)

    # Remove uneeded axices
    ax = pylab.gca()
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')


def scoreNormHist(resultMat, labels) :
    # Normalize resultMat row by row with respect to mean and standard deviation
    resultMat_norm = numpy.zeros(resultMat.shape)
    label_array = numpy.array(labels)
    for i,(row,l) in enumerate(zip(resultMat, labels)) :

        same = label_array == l
        diff = label_array != l
        mean_same = numpy.mean(row[same])
        mean_diff = numpy.mean(row[diff])
        weighted_mean = mean_same * (numpy.sum(same) / float(len(labels))) + mean_diff * (numpy.sum(diff) / float(len(labels)))
        sd = numpy.sqrt(numpy.var(row))
        ratio = mean_same / (mean_diff + 0.000001)
        resultMat_norm[i] = (row - weighted_mean) / (sd + 00000.1)
        
    # Make sure the diagonal is zero
    for i in range(len(labels)) : resultMat_norm[i][i] = 0.0
        
    # Create mask
    resultMask = numpy.zeros(resultMat.shape, dtype=numpy.bool)
    for i,l in enumerate(labels) :
        resultMask[i] = label_array == l

    # Get vectors with results for same and diff
    same = resultMat_norm[resultMask]
    diff = resultMat_norm[numpy.invert(resultMask)]

    mean_same = numpy.mean(same)
    mean_diff = numpy.mean(diff)
    variance = numpy.mean([numpy.var(same), numpy.var(diff)])
    sd = numpy.sqrt(variance)

    print("Mean(same):\t\t{0:.3f}".format(mean_same))
    print("Mean(diff):\t\t{0:.3f}".format(mean_diff))
    print("Diff of means:\t\t{0:.3f}".format(numpy.abs(mean_diff - mean_same)))
    print("Standard deviation:\t{0:.3f}".format(sd)) 
    print("# of sd's:\t\t{0:.3f}".format(numpy.abs(mean_diff - mean_same)/sd))

    x_min = min([numpy.min(same),numpy.min(diff)]) 
    x_max = max([numpy.max(same),numpy.max(diff)]) 
    margin = (x_max - x_min) * 0.2

    pylab.subplot(1,2,1)
    pylab.hist(same, bins=20, label="Same", color="green", alpha=0.65)
    pylab.legend()
    pylab.xlim(x_min - margin ,x_max + margin )
    removeDecoration()

    pylab.subplot(1,2,2)
    pylab.hist(diff, bins=20,label="Diff", color="red", alpha=0.65)
    pylab.legend()
    pylab.xlim(x_min - margin ,x_max + margin )
    removeDecoration()


def accuHist(accu_list, labels, colors = ["blue", "cyan", "green", "orange", "red"], ylim = 100) :
    n = len(accu_list)
    pylab.figure(figsize=(10, 3))
    for i,(a,l,c) in enumerate(zip(accu_list, labels, colors)) :
        pylab.subplot(1,n,(i+1))
        pylab.hist(a, bins=20, label=l, color=c, alpha=0.65)
        pylab.legend()
        pylab.xlim(0,1.01)
        pylab.ylim(0,ylim)
        removeDecoration()


def accuDetail(correct, total, legend, ylim = 100, treshold=1000) :
    get_index = lambda cs : list(dropwhile(lambda (i,c) : sum(c) < treshold,enumerate(cs)))[0][0]
    indices = [get_index(cs) for cs in correct]
    print(indices)
    
    for c,t,l,i in zip(correct, total, legend, indices) :
        print("%s:\t%i of %i\t(%.2f%%)" % (l, sum(c[i]), sum(t[i]), 100*sum(c[i])/float(sum(t[i]))))
        
    get_accu = lambda ts,cs,index : [1 if t == 0 else c/float(t) for t,c in zip(ts[index], cs[index])]
    accu = [get_accu(ts, cs, index) for ts,cs,index in zip(total, correct, indices)]
    accuHist(accu, legend, ylim=ylim)


# Showing all keypoints from a given node in a ball tree
def showNode(bt, ks, indices, node_index) :
    node = getNode(bt, node_index)
    idx = numpy.array(bt.idx_array[node['idx_start']:node['idx_end']])
    keypoints = ks[idx]
    im_idx = indices[idx]
    positions = numpy.array(features.getPositions(keypoints))
    display.compareKeypoints(images[0], images[1], positions[im_idx == 0], positions[im_idx == 1])


def comparePlot(correct, 
                compareCorrect, 
                total, 
                compareTotal,
                legends, 
                compareLegends,
                colors  = ["blue", "red", "green", "maroon", "cyan"], 
                ylim=(0.0, 1.01), 
                xlim = (0.01, 0.5),
                size = (4,6), 
                nb_correspondences = None, 
                outside = False, 
                output = None) :
    """ Plot that show curves but compares with a different line in dots """

    fig = pylab.figure(figsize=size)
    ax = pylab.subplot(111)
    if nb_correspondences == None :
        nb_correspondences = [1 for ts in total]

    for i in range(0,len(total)) :
        ts, ts_i = total[i], compareTotal[i]
        cs, cs_i = correct[i], compareCorrect[i]
        l, l_i = legends[i], compareLegends[i]
        color = colors[i]
        nb_corr = nb_correspondences[i]
        xs = [sum(c)/float(nb_corr) for c in cs]
        ys = [1 if sum(t) == 0 else sum(c)/float(sum(t)) for (c, t) in zip(cs, ts)]
        xs_i = [sum(c)/float(nb_corr) for c in cs_i]
        ys_i = [1 if sum(t) == 0 else sum(c)/float(sum(t)) for (c, t) in zip(cs_i, ts_i)]
        pylab.plot(xs, ys, '-', label=l, color=color, alpha=0.95)
        pylab.plot(xs_i, ys_i, '--', label="%s" % (l_i), color=color, alpha=1)

    # Remove superflous lines and add axis labels
    removeDecoration()
    if nb_correspondences != None :
        pylab.xlabel("Recall")
    else :
        pylab.xlabel("# of Matches")
    pylab.ylabel("Precision")
    pylab.ylim(ylim[0],ylim[1])

    # Put legend outside of plot
    pylab.legend(loc="best")
    if outside == True :
        # Shink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    pylab.xlim(xlim[0],xlim[1])
    #ax.set_xscale('log')

    # Print to file
    if output != None :
        pylab.savefig(output, bbox_inches='tight', dpi=80)



def improvPlot(data, ref, labels, colors = ["green", "red", "orange" ,"blue", "maroon", "black"], nb_correspondences = None, size = (7,3), ylim = (0.0,1.01), xlim = (1.0), output = None, outside = False) :
    fig = pylab.figure(figsize=size)
    ax = pylab.subplot(111)
    
    # Make function for interpolating
    def interpolate(total, correct, xlim = (0.0,1.0), samples = 1000) :
        xs = numpy.linspace(xlim[0], xlim[1], samples)
        if nb_correspondences != None :
            recall = [sum(c)/float(nb_correspondences) for c in correct]
        else :
            recall = [sum(t) for t in ref[1]]
        precision = [1 if sum(t) == 0 else sum(c)/float(sum(t)) for (t, c) in zip(total, correct)]
        ys = scipy.interp(xs, recall, precision)
        max_recall = numpy.max(recall)
        max_index = int((max_recall - xlim[0]) / ((xlim[1] - xlim[0]) / samples))
        return xs[:max_index], ys[:max_index]
    
    # get interpolated ref
    xs_ref, ys_ref = interpolate(ref[0], ref[1])
    
    # Calculate the improvement in amount of false negatives
    def false_neg_rate(y, y_ref) :
        return 0 if (1 - y_ref) < 0.001 else (y - y_ref) / (1 - y_ref)
            
    for (total, correct), l, color in zip(data, labels, colors) :
        xs, ys = interpolate(total, correct)
        improv = [false_neg_rate(y, y_ref) for y, y_ref in zip(ys, ys_ref)]
        #print(improv)
        pylab.plot(xs, improv, '-', label=l, color=color, alpha=0.95)
        pylab.legend(loc="best")

    # Remove superflous lines and add axis labels
    removeDecoration()
    if nb_correspondences != None :
        pylab.xlabel("Recall" % nb_correspondences)
    else :
        pylab.xlabel("# of Matches")
    pylab.ylabel("False Positive Elimination Rate")
    pylab.ylim(ylim[0],ylim[1])

    # Put legend outside of plot
    if outside == True :
        # Shink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    if xlim != None : pylab.xlim(0,xlim)

    # Print to file
    if output != None :
        pylab.savefig(output, bbox_inches='tight', dpi=80)



def accuPlot(correct, total, legends, colors = ["blue", "red", "green", "orange", "maroon"], ylim=(0.0, 1.01), xlim = None, size = (4,6), nb_correspondences = None, outside = False, output = None) :
    fig = pylab.figure(figsize=size)
    ax = pylab.subplot(111)
    if isinstance(nb_correspondences, ( int, long ) ) or nb_correspondences == None :
        nb_correspondences = [nb_correspondences] * len(correct)
    for ts, cs, l, color, corr in zip(total, correct, legends, colors, nb_correspondences) :
        if corr != None :
            xs = [sum(c)/float(corr) for c in cs]
        else :
            xs = [sum(t) for t in ts]
        ys = [1 if sum(t) == 0 else sum(c)/float(sum(t)) for (c, t) in zip(cs, ts)]
        pylab.plot(xs, ys, '-', label=l, color=color, alpha=0.95)
        pylab.legend(loc="best")

    # Remove superflous lines and add axis labels
    removeDecoration()
    if nb_correspondences != None :
        pylab.xlabel("Recall")# % nb_correspondences)
    else :
        pylab.xlabel("# of Matches")
    pylab.ylabel("Precision")
    pylab.ylim(ylim[0],ylim[1])

    # Put legend outside of plot
    if outside == True :
        # Shink current axis by 20%
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.75, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    if xlim != None : pylab.xlim(0,xlim)

    # Print to file
    if output != None :
        pylab.savefig(output, bbox_inches='tight', dpi=80)


def distHist(dist, dist_treshold = 5, dist_distinct = None, accuracity = None, accu_y_lim = 100) :

    plots = 2 if accuracity == None else 3
    dist_under_median = [d for d in dist if d <= (numpy.median(dist) * 2)]
    dist_under_treshold = [d for d in dist if d <= dist_treshold]
    if (len(dist) == 0) : return
    dist_p = float(len(dist_under_treshold)) / float(len(dist))
    if dist_distinct != None :
        distinct_under_treshold = [d for d in dist_distinct if d <= dist_treshold]
        distinct_p = float(len(distinct_under_treshold)) / float(len(dist_distinct))

    pylab.figure(figsize=(10, 3))

    pylab.subplot(1,plots,1)
    pylab.hist(dist, bins=20, label="Distances", color="blue", alpha=0.65)
    pylab.legend()
    removeDecoration()

    pylab.subplot(1,plots,2)
    pylab.hist(dist_under_median, bins=20, label="Distances", color="cyan", alpha=0.65)
    pylab.legend()
    removeDecoration()

    if accuracity != None :
        pylab.subplot(1,plots,3)
        pylab.hist(accuracity, bins=20, label="Accuracity", color="green", alpha=0.65)
        pylab.legend()
        pylab.xlim(0,1.01)
        pylab.ylim(0,accu_y_lim)
        removeDecoration()


    if dist_distinct != None :
        print("Number of matches:\t%i\t(distinct: %i)" % (len(dist), len(dist_distinct)))
        print("Correct matches:\t%i\t(distinct: %i)\t\t[under %ipx error]" % (len(dist_under_treshold), len(distinct_under_treshold), dist_treshold) )
        print("Success Rate:\t\t%.2f%%\t(distinct: %.2f%%)" % (dist_p*100, distinct_p*100))
    else :
        print("Number of matches:\t%i" % len(dist))
        print("Correct matches:\t%i\t[under %ipx error]" % (len(dist_under_treshold), dist_treshold) )
        print("Under %ipx error:\t%.2f%%" % (dist_treshold, dist_p*100))



def scoreHist(scores) : 

    if (len(scores[0]) == 3) :
        same = [s for b,s,p in scores if b and not math.isnan(s) ]
        diff = [s for b,s,p in scores if not b and not math.isnan(s)] 
    else :
        same = [s for b,s in scores if b and not math.isnan(s)]
        diff = [s for b,s in scores if not b and not math.isnan(s)] 

    mean_same = numpy.mean(same)
    mean_diff = numpy.mean(diff)
    variance = numpy.mean([numpy.var(same), numpy.var(diff)])
    sd = numpy.sqrt(variance)

    print("Mean(same):\t\t{0:.3f}".format(mean_same))
    print("Mean(diff):\t\t{0:.3f}".format(mean_diff))
    print("Diff of means:\t\t{0:.3f}".format(numpy.abs(mean_diff - mean_same)))
    print("Standard deviation:\t{0:.3f}".format(sd)) 
    print("# of sd's:\t\t{0:.3f}".format(numpy.abs(mean_diff - mean_same)/sd))

    x_min = min(min([same,diff])) 
    x_max = max(max([same, diff]))
    margin = (x_max - x_min) * 0.2

    pylab.subplot(1,2,1)
    pylab.hist(same, bins=20, label="Same", color="green", alpha=0.65)
    pylab.legend()
    pylab.xlim(x_min - margin ,x_max + margin )
    removeDecoration()

    pylab.subplot(1,2,2)
    pylab.hist(diff, bins=20,label="Diff", color="red", alpha=0.65)
    pylab.legend()
    pylab.xlim(x_min - margin ,x_max + margin )
    removeDecoration()



def scoreRatioHist(resultMat, labels, lower_is_better=False) :
    scores = numpy.zeros(labels.shape)
    for i,row in enumerate(resultMat) :
        equal_labels = (labels == labels[i])
        diff_labels = (labels != labels[i])
        mean_same = numpy.mean(row[equal_labels]) + 0.0000001
        mean_diff = numpy.mean(row[diff_labels]) + 0.0000001
        ratio = mean_diff/mean_same if lower_is_better else mean_same/mean_diff
        scores[i] = ratio
        
    # Remove outliers
    scores[scores > 3] = 3
    below_1 = numpy.sum(scores<1)
    above_1 = numpy.sum(scores>1)
    equal_1 = numpy.sum(scores==1)
    above_3 = numpy.sum(scores>3)
    if equal_1 > 0 : 
        gray_start = 0.95
        gray_end = 1.05
    else :
        gray_start = 1
        gray_end = 1
    ax = pylab.subplot(1,1,1)
    pylab.hist(scores[scores < 1],bins=numpy.linspace(0,gray_start,7), color="red", alpha=0.7, label="< 1.0 (%i)" % below_1)
    if equal_1 > 0 : pylab.hist(scores[scores == 1],bins=numpy.linspace(gray_start,gray_end,2), color="grey", alpha=0.7, label="= 1.0 (%i)" % equal_1)
    pylab.hist(scores[scores > 1],bins=numpy.linspace(gray_end,3,14), color="green", alpha=0.7, label="> 1.0 (%i)" % above_1)
    pylab.xlim(0,3.01)
    pylab.legend(loc="best")
    #ax.set_xscale("log")
    removeDecoration()


def farPlot(scores, n = 500, lower_is_better = False) :

    if (len(scores[0]) == 3) :
        same = [s for b,s,p in scores if b and not math.isnan(s) ]
        diff = [s for b,s,p in scores if not b and not math.isnan(s)] 
    else :
        same = [s for b,s in scores if b and not math.isnan(s)]
        diff = [s for b,s in scores if not b and not math.isnan(s)] 

    # set compare function
    compare = (lambda a,b : a < b) if lower_is_better else (lambda a,b : a > b)

    # Create linspace
    min_val = numpy.min(same)
    max_val = numpy.max(same)
    start = min_val if lower_is_better else max_val
    end = max_val if lower_is_better else min_val
    tresholds = numpy.linspace(start,end,n)

    # Calculate x and y rows
    sum_same = float(len(same))
    sum_diff = float(len(diff))
    false_positive_rate = [(len([s for s in diff if compare(s,t)]) / sum_diff)*100 for t in tresholds]
    true_positive_rate = [len([s for s in same if compare(s,t)]) / sum_same for t in tresholds]

    # Show figure
    fig = pylab.figure()
    ax = fig.add_subplot(1,1,1)
    ax.plot(false_positive_rate, true_positive_rate)
    ax.set_xscale('log')
    removeDecoration()



def clusterPlot(resultMat, labels, pruner, ylim=0.5, xlim=8) :
    xs = numpy.linspace(0.001,xlim,100)

    def getRandScore(l) :
        pruned_w = pruner(resultMat, l, n=500, start=0.0)
        p = louvain.cluster(pruned_w)
        #ars = metrics.adjusted_rand_score(labels, p)
        amis = metrics.adjusted_mutual_info_score(labels,p)
        return amis

    ys = [getRandScore(x) for x in xs]
    pylab.plot(xs,ys)
    pylab.ylim(0,ylim)
    removeDecoration()



def showPartitions(points, partitioning, image = None, output = "partitions.jpg") :
    max_x = numpy.max(points[:,0])
    max_y = numpy.max(points[:,1])
    cs = colors.get()
    pylab.gray()
    if image != None :
        pylab.imshow(image)
        pylab.xlim(0,image.shape[1])
        pylab.ylim(image.shape[0],0)
    else :
        pylab.xlim(0,max_y*1.1)
        pylab.ylim(0,max_x*1.1)

    for pos,p in zip(points, partitioning) :
        pylab.plot(pos[0], pos[1], color=cs[p], marker='o')

    pylab.axis('off')
    pylab.savefig(output, bbox_inches='tight')



####################################
#                                  #
#            Clusters              #
#                                  #
####################################



#def trait_graph(tg, images) :
#    graph_on_images(
#            tg, 
#            images, 
#            clusters=tg.vp["partitions"], 
#            path="trait_graph.png",
#            edge_color=tg.ep["edge_colors"], 
#            vertex_size=tg.vp["variance"])


#def draw_graph(g, clusters="orange", filename="graph.png", size=(1000,1000)) :
#    """ Show a graph with its clustering marked
#    """
#    # Get indices
#    indices = g.vertex_properties["indices"]
#
#    # Get class colors
#    class_colors = g.vertex_properties["class_colors"]
#
#    # Get weights and positions
#    weights = g.edge_properties["weights"]
#    pos = gt.sfdp_layout(g, eweight=weights)
#
#    # Print graph to file
#    gt.graph_draw(g, pos=pos, output_size=size, vertex_halo=True, vertex_halo_color=class_colors, vertex_color=clusters,
#               vertex_fill_color=clusters, vertex_size=5, edge_pen_width=weights, output=filename)
#
#    g_img = imread(filename)
#    pylab.imshow(g_img)



#def graph_partitions(g, clusters, filename="graph_clusters.png") :
#    """ Create an image where the clusters are disconnected
#    """
#    # Prune inter cluster edges
#    intra_cluster = g.new_edge_property("bool")
#    intra_cluster.fa = [(clusters[e.source()] == clusters[e.target()]) for e in graph.edges()]
#
#    # Create graph with less edges
#    g_cluster = gt.GraphView(g, efilt=intra_cluster)
#
#    graph(g_cluster, clusters, filename=filename)



#def graph_on_images(graph, images, clusters = "orange", path="graph_on_images.png", vertex_size=15, edge_color=[0.0, 0.0, 0.0, 0.8]) :
#    """ Displays the feature points of the graph as they are located on the images
#        Input: graph [Graph]
#               images [List of images]
#    """
#
#    def tails(it):
#        """ tails([1,2,3,4,5]) --> [[1,2,3,4,5], [2,3,4,5], [3,4,5], [4,5], [5], []] """
#        while True:
#            tail, it = tee(it)
#            yield tail
#            next(it)
#
#    # Interpolate images to double size
#    scale = 2.0
#    separation = 20
#
#    # Show in gray-scale
#    pylab.gray()
#
#    # Image paths
#    bg_path = "graph_background.png"
#    fg_path = "graph_foreground.png"
#    merge_path = path
#
#    # Put images together and resize
#    bg_small = appendimages(images[0], images[1], seperator = separation)
#    bg = imresize(bg_small, size=scale, interp='bicubic')
#    pylab.imsave(bg_path, bg)
#
#    # Calculate offsets
#    offsets = map(sum, [list(t) for t in tails(map(lambda i : (i.shape[1] + separation)*scale, images))])[::-1]
#    print(offsets)
#
#    # Get scaled positions
#    ind_prop = graph.vertex_properties["indices"]
#    x,y = (graph.vertex_properties["x"], graph.vertex_properties["y"])
#    pos = graph.new_vertex_property("vector<float>")
#    for v in graph.vertices() : 
#        x_scaled = x[v] * scale + offsets[ind_prop[v]]
#        y_scaled = y[v] * scale
#        pos[v] = [x_scaled, y_scaled]
#
#    # Get weights
#    weights = graph.edge_properties["weights"]
#
#    # Draw graph
#    class_colors = graph.vertex_properties["class_colors"]
#    gt.graph_draw(graph, 
#                  pos=pos, 
#                  fit_view=False, 
#                  output_size=[bg.shape[1], bg.shape[0]],
#                  vertex_halo=True,
#                  vertex_halo_color="black",
#                  vertex_size=vertex_size,
#                  vertex_fill_color=clusters,
#                  edge_color=edge_color,
#                  edge_pen_width=weights,
#                  output=fg_path
#                 )
#    
#    # Merge the graph and background images
#    background = Image.open(bg_path)
#    foreground = Image.open(fg_path)
#    background.paste(foreground, (0, 0), foreground)
#    background.save(merge_path)
#    
#    # Show resulting image
#    im = pylab.imread(merge_path)
#    pylab.imshow(im)



#def faceGraph(graph, partitions, paths, filename = "facegraph.png") :
#    partition_prop = graph.new_vertex_property("int")
#    partition_prop.fa = partitions
#    path_prop = graph.new_vertex_property("string")
#    for v, p in zip(graph.vertices(), paths) : path_prop[v] = p
#    pos = gt.sfdp_layout(graph, eweight=graph.ep["weights"])
#    gt.graph_draw(graph, 
#                  pos=pos, 
#                  output_size=(2000, 1400), 
#                  vertex_halo=True, 
#                  vertex_halo_color=partition_prop, 
#                  #vertex_fill_color=partitioning, 
#                  vertex_anchor=0,
#                  vertex_pen_width=10,
#                  vertex_color=partition_prop,
#                  vertex_surface=path_prop,
#                  vertex_size=50, 
#                  edge_pen_width=graph.ep["weights"], 
#                  output=filename)

#def showTwoPartitions(part_1, part_2, indices, images, positions, output = "isomatch_partitions") :
#    pylab.figure(frameon=False, figsize=(14,5))
#    pylab.subplot(1,2,1)
#    showPartitions(positions[indices==0], part_1, image = images[0], output =  "%s_1.jpg" % output)
#    pylab.subplot(1,2,2)
#    showPartitions(positions[indices==1], part_2, image = images[1], output = "%s_2.jpg" % output)
#    ax = pylab.gca()
#    #ax.xaxis.set_ticks_position('bottom')
#    #ax.yaxis.set_ticks_position('left')
#    pylab.show()
#    pylab.savefig(output)

####################################
#                                  #
#              Util                #
#                                  #
####################################

def makeMask(f,ls) : return [f(k) for k in ls]

def removeDecoration() :
    # Remove uneeded axices
    ax = pylab.gca()
    ax.spines['right'].set_color('none')
    ax.spines['top'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.yaxis.set_ticks_position('left')

