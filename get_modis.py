#!/usr/bin/env python

"""
SYNOPSIS
    
./get_modis.py [-h,--help] [--verbose, -v] [--platform=PLATFORM, -s PLATFORM] \
    [--product=PRODUCT, -p PRODUCT] [--tile=TILE, -t TILE] [--year=YEAR, -y YEAR] \
    [--output=DIR_OUT, -o DIR_OUT] [--begin=DOY_START, -b DOY_START] [--end=DOY_END, -e DOY_END]

DESCRIPTION

A program to download MODIS data from the USGS website using the HTTP
transport. This program is able to download daily, monthly, 8-daily, etc products
for a given year, it only requires the product names (including the collection number), 
the year, the MODIS reference tile and additionally, where to save the data to, and
whether to verbose. The user may also select a temporal period in terms of days of year.

EXAMPLES

    The following example downloads daily surface reflectance from the TERRA platform for
    tile h17v04 for 2004, between DoY 153 and 243:
    
    $ ./get_modis.py -v -p MOD09GA.005 -s MOLT -y 2004 -t h17v04 -o /tmp/ -b 153 -e 243
    
    The script will also work with monthly or 8-daily composites. Here's how you 
    download the monthly MCD45A1 (burned area) product for the same period:
    
    $ ./get_modis.py -v -p MCD45A1.005 -s MOTA -y 2004 -t h17v04 -o /tmp/ -b 153 -e 243
        

EXIT STATUS
    No exit status yet, can't be bothered.

AUTHOR

    J Gomez-Dans <j.gomez-dans@ucl.ac.uk>
    See also http://github.com/jgomezdans/get_modis/

"""
import optparse
import os
import urllib2
import time
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


def get_modisfiles ( platform, product, year, tile, doy_start=1, doy_end = -1,  \
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
    headers = { 'User-Agent' : 'get_modis Python 1.0.0' }
    if not os.path.exists ( out_dir ):
        if verbose:
            log.info("Creating outupt dir %s" % out_dir )
        os.mkdirs ( out_dir )
    if doy_end == -1:
        if calendar.isleap ( year ):
            doy_end = 367
        else:
            doy_end = 366
    
    dates = [time.strftime("%Y.%m.%d", time.strptime( "%d/%d" % ( i, year ), "%j/%Y")) \
            for i in xrange(doy_start, doy_end )]
    url = "%s/%s/%s/" % ( base_url, platform, product )
    for date in dates:
        req = urllib2.Request ( "%s/%s" % ( url, date), None, headers)
        try:
            html = urllib2.urlopen(req).readlines()
            for l in html:
                if l.find( tile ) >=0  and l.find(".hdf") >= 0 and l.find(".hdf.xml") < 0:
                    fname = l.split("href=")[1].split(">")[0].strip('"')
                    req = urllib2.Request ( "%s/%s/%s" % ( url, date, fname), None, headers)
                    download = False
                    if not os.path.exists ( os.path.join( out_dir, fname ) ):
                        # File not present, download
                        download = True
                    else:
                        f = urllib2.urlopen(req)
                        remote_file_size = int ( f.headers.dict['content-length'] )
                        local_file_size = os.path.getsize(os.path.join( out_dir, fname ) )
                        if remote_file_size != local_file_size:
                            download = True
                        
                    if download:
                        if verbose:
                                log.info ( "Getting %s..... " % fname )
                        with open ( os.path.join( out_dir, fname ), 'wb' ) as fp:
                            shutil.copyfileobj(urllib2.urlopen(req), fp)
                            if verbose:
                                log.info("Done!")
                    else:
                        if verbose:
                            log.info ("File %s already present. Skipping" % fname )

        except urllib2.URLError:
            log.info("Could not find data for %s(%s) for %s" % ( product, platform, date ))
    if verbose:
        log.info("Completely finished downlading all there was")
        

if __name__ == "__main__":
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), \
        usage=globals()['__doc__'])
    parser.add_option ('-v', '--verbose', action='store_true', \
        default=False, help='verbose output')
    parser.add_option ('-s', '--platform', action='store', dest="platform",\
        type=str, help='Platfor type: MOLA, MOLT or MOTA')
    parser.add_option ('-p', '--product', action='store', dest="product", \
        type=str, help="MODIS product name with collection tag at the end (e.g. MOD09GA.005)" )
    parser.add_option ('-t', '--tile', action="store", dest="tile", \
        type=str, help="Required tile (h17v04, for example)")
    parser.add_option ( "-y", "--year", action="store", dest="year", \
        type=int, help="Year of interest" )
    parser.add_option('-o', '--output', action="store", dest="dir_out", default=".",\
        type=str, help="Output directory" )
    parser.add_option('-b', '--begin', action="store", dest="doy_start", default=1,\
        type=int, help="Starting day of year (DoY)" )
    parser.add_option('-e', '--end', action="store", dest="doy_end", type=int, default=-1, \
        help="Ending day of year (DoY)" )
    
    (options, args) = parser.parse_args()
    if not ( options.platform in [ "MOLA", "MOTA", "MOLT" ] ) :
        log.fatal ("`platform` has to be one of MOLA, MOTA, MOLT")
        sys.exit(-1)
    
    
    get_modisfiles ( options.platform, options.product, options.year, options.tile, \
            doy_start=options.doy_start, doy_end=options.doy_end, out_dir=options.dir_out, \
            verbose=options.verbose )