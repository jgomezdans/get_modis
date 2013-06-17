#!/usr/bin/env python

"""
SYNOPSIS

    
    

DESCRIPTION

  This program receives a metadata file in USGS format, and it then applies
  the Wang atmospheric correction method based on a minimimal set of input
  parameters. It will take the original data, subset it if required using a
  geographical box in projection units (UTM). It will produce datasets with
  the TOA radiance (e.g. `LE72040312010347EDC00_ROI_B2_TOARAD.tif`), as well
  as a datafile with the visible bands with atmospheric correction  (filename
  is e.g. `LE72040312010347EDC00_WANG_VIS_WLRAD.tif`). 

EXAMPLES
            $ ./do_atcorr.py -H 0.5 -i data/LE72040312010347EDC00_MTL.txt \
                --roi 578745.000,4650765.000,608535.000,4618935.000 -v
                
            Sat Jun 15 15:19:56 2013
            1 data/LE72040312010347EDC00_ROI_B1.vrt data/LE72040312010347EDC00_B1.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            2 data/LE72040312010347EDC00_ROI_B2.vrt data/LE72040312010347EDC00_B2.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            3 data/LE72040312010347EDC00_ROI_B3.vrt data/LE72040312010347EDC00_B3.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            4 data/LE72040312010347EDC00_ROI_B4.vrt data/LE72040312010347EDC00_B4.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            5 data/LE72040312010347EDC00_ROI_B5.vrt data/LE72040312010347EDC00_B5.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            7 data/LE72040312010347EDC00_ROI_B7.vrt data/LE72040312010347EDC00_B7.TIF
            Input file size is 8081, 7151
            Computed -srcwin 3822 2685 993 1061 from projected window.
            Start reading data/LE72040312010347EDC00_ROI_B1.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B1_TOARAD.tif
            Start reading data/LE72040312010347EDC00_ROI_B2.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B2_TOARAD.tif
            Start reading data/LE72040312010347EDC00_ROI_B3.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B3_TOARAD.tif
            Start reading data/LE72040312010347EDC00_ROI_B4.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B4_TOARAD.tif
            Start reading data/LE72040312010347EDC00_ROI_B5.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B5_TOARAD.tif
            Start reading data/LE72040312010347EDC00_ROI_B7.vrt
            Using blocksize 128 x 128
            Creating output data/LE72040312010347EDC00_ROI_B7_TOARAD.tif
                    Theta_i=22.545988, Phi_i=160.273075
            Lambdas:  [   482.5    565.     660.     837.5   1650.   11450.    2220. ]
            LE72040312010347EDC00_MTL.txt
            Doy: 347, Year: 2010
            Using default O3 conc file, O3 conc: 265.000000
            Starting interpolation...
            Interpolation done...
            Creating output data/LE72040312010347EDC00_WANG_VIS_WLRAD.tif
            Sat Jun 15 15:23:22 2013
            TOTAL TIME IN MINUTES: 3.43263668219


EXIT STATUS

    -1 if numpy and/or GDAL aren't present

AUTHOR

    J Gomez-Dans <j.gomez-dans@ucl.ac.uk>

NOTE
    
    The program has not been verified. Needs severe testing!!!!!!!!
"""
import os
import urllib2
import datetime
import calendar
import shutil
import logging
import sys

log = logging.getLogger(__name__)
out_hdlr = logging.StreamHandler(sys.stdout)
out_hdlr.setFormatter(logging.Formatter('%(asctime)s %(message)s'))
out_hdlr.setLevel(logging.INFO)
log.addHandler(out_hdlr)
log.setLevel(logging.INFO)


def get_modisfiles ( platform, product, year, tile, doy_start=1, doy_end = None,  \
    base_url="http://e4ftl01.cr.usgs.gov", out_dir=".", verbose=False ):

    """Download MODIS products for a given tile, year & period of interest

    This function uses the `urllib2` module to download MODIS "granules" from the
    USGS website. The approach is based on downloading the index files for any
    date of interest, and parsing the HTML (rudimentary parsing!) to search for
    the relevant filename for the tile the user is interested in. This file
    is then downloaded in the directory specified by `out_dir`.

    Parameters
    ----------
    platform: str
        One of three: MOLA, MOLT MOTA
    product: str
        The product name, such as MOD09GA.005 or MYD15A2.005. Note that you need to 
        specify the collection number (005 in the examples)
    year: int
        The year of interest
    tile: str
        The tile (e.g., "h17v04")
    doy_start: int
        The starting day of the year.
    doy_end: int 
        The ending day of the year.
    base_url: str, url
        The URL to use. Shouldn't be changed, unless USGS change the server.
    out_dir: str 
        The output directory. Will be create if it doesn't exist
    verbose: Boolean
        Whether to sprout lots of text out or not.

    Returns
    -------
    Nothing
    """
    headers = { 'User-Agent' : 'get_modis Python 1.0' }
    if not os.path.exists ( out_dir ):
        if verbose:
            log.info("Creating outupt dir %s" % out_dir )
        os.mkdirs ( out_dir )
    if doy_end is None:
        if calendar.isleap ( year ):
            doy_end = 367
        else:
            doy_end = 366
    
    dates = [time.strftime("%Y.%m.%d", time.strptime( "%d/%d" % ( i, year ), "%j/%Y")) \
            for i in xrange(doy_start, doy_end )]
    url = "%s/%s/%s/" % ( base_url, platform, product )
    for date in dates:
        req = urllib2.Request ( "%s/%s" % ( url, date), None, headers)
        html = urllib2.urlopen(req).readlines()
        for l in html:
            if l.find( tile ) >=0  and l.find(".hdf") >= 0 and l.find(".hdf.xml") < 0:
                fname = l.split("href=")[1].split(">")[0].strip('"')
                if verbose:
                    log.info ( "Getting %s..... " % fname )
                req = urllib2.Request ( "%s/%s/%s" % ( url, date, fname), None, headers)
                with open ( os.path.join( out_dir, fname ), 'wb' ) as fp:
                    shutil.copyfileobj(urllib2.urlopen(req), fp)
                if verbose:
                    log.info("Done!")
    if verbose:
        log.info("Completely finished downlading all there was")
if __name__ == "__main__":
    get_modisfiles ( "MOLT", "MOD09GA.005", 2004, "h17v04", verbose=True )