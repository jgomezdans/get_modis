#!/usr/bin/env python

"""
SYNOPSIS
    
./get_modis.py [-h,--help] [--verbose, -v] [--platform=PLATFORM, -s PLATFORM]\
    [--proxy=PROXY -p PROXY] \
    [--product=PRODUCT, -p PRODUCT] [--tile=TILE, -t TILE] \
    [--year=YEAR, -y YEAR] [--output=DIR_OUT, -o DIR_OUT] \
    [--begin=DOY_START, -b DOY_START] [--end=DOY_END, -e DOY_END]

DESCRIPTION

A program to download MODIS data from the USGS website using the HTTP
transport. This program is able to download daily, monthly, 8-daily, etc 
products for a given year, it only requires the product names (including the 
collection number), the year, the MODIS reference tile and additionally, where
to save the data to, and whether to verbose. The user may also select a 
temporal period in terms of days of year.

EXAMPLES

    The following example downloads daily surface reflectance from the TERRA 
    platform for tile h17v04 for 2004, between DoY 153 and 243:
    
    $ ./get_modis.py -v -p MOD09GA.005 -s MOLT -y 2004 -t h17v04 -o /tmp/ \
        -b 153 -e 243
    
    The script will also work with monthly or 8-daily composites. Here's how 
    you download the monthly MCD45A1 (burned area) product for the same period:
    
    $ ./get_modis.py -v -p MCD45A1.005 -s MOTA -y 2004 -t h17v04 -o /tmp/ \
        -b 153 -e 243
        

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
import fnmatch

LOG = logging.getLogger( __name__ )
OUT_HDLR = logging.StreamHandler( sys.stdout )
OUT_HDLR.setFormatter( logging.Formatter( '%(asctime)s %(message)s') )
OUT_HDLR.setLevel( logging.INFO )
LOG.addHandler( OUT_HDLR )
LOG.setLevel( logging.INFO )

HEADERS = { 'User-Agent' : 'get_modis Python 1.3.0' }

def return_url ( url ):

    the_day_today = time.asctime().split()[0]
    the_hour_now = int( time.asctime().split()[3].split(":")[0] )
    if the_day_today == "Wed" and 14 <= the_hour_now <= 17:
        LOG.info ( "Sleeping for %d hours... Yawn!" % ( 18 - the_hour_now) )
        time.sleep ( 60*60*( 18-the_hour_now) )
        #LOG.info ( "Sleeping for %d hours... Yawn!" % ( 18 - the_hour_now) )
    
    req = urllib2.Request ( "%s" % ( url ), None, HEADERS)
    html = urllib2.urlopen(req).readlines()
    return html
                
    
def parse_modis_dates ( url, dates, product, out_dir, ruff=False ):
    """Parse returned MODIS dates.
    
    This function gets the dates listing for a given MODIS products, and 
    extracts the dates for when data is available. Further, it crosses these 
    dates with the required dates that the user has selected and returns the 
    intersection. Additionally, if the `ruff` flag is set, we'll check for
    files that might already be present in the system and skip them. Note
    that if a file failed in downloading, it might still be around
    incomplete.
    
    Parameters
    ----------
    url: str
        A URL such as "http://e4ftl01.cr.usgs.gov/MOTA/MCD45A1.005/"
    dates: list
        A list of dates in the required format "YYYY.MM.DD"
    product: str
        The product name, MOD09GA.005
    out_dir: str
        The output dir
    ruff: bool
        Whether to check for present files
    Returns
    -------
    A (sorted) list with the dates that will be downloaded.
    """
    if ruff:
        product = product.split(".")[0]
        already_here = fnmatch.filter ( os.listdir ( out_dir ), "%s*hdf" % product )
        already_here_dates = [ x.split(".")[-5][1:] \
            for x in already_here ]
                                      
    #req = urllib2.Request ( "%s" % ( url ), None, HEADERS)
    #html = urllib2.urlopen(req).readlines()
    html = return_url ( url )
            
    available_dates = []
    for line in html:
        
        if line.find ( "href" ) >= 0 and line.find ( "[DIR]" ) >= 0:
            # Points to a directory
            the_date = line.split('href="')[1].split('"')[0].strip("/")
            
            if ruff:
                try:
                    modis_date = time.strftime( "%Y%j", time.strptime( \
                        the_date, "%Y.%m.%d") )
                except ValueError:
                    continue
                if modis_date in already_here_dates:
                    continue
                else:
                    available_dates.append ( the_date )    
            else:
                available_dates.append ( the_date )    
                
            
    
    dates = set ( dates )
    available_dates = set ( available_dates )
    suitable_dates = list( dates.intersection( available_dates ) )
    suitable_dates.sort()
    return suitable_dates
    
    
def get_modisfiles ( platform, product, year, tile, proxy, \
    doy_start=1, doy_end = -1,  \
    base_url="http://e4ftl01.cr.usgs.gov", out_dir=".", ruff=False, verbose=False ):

    """Download MODIS products for a given tile, year & period of interest

    This function uses the `urllib2` module to download MODIS "granules" from 
    the USGS website. The approach is based on downloading the index files for
    any date of interest, and parsing the HTML (rudimentary parsing!) to search
    for the relevant filename for the tile the user is interested in. This file
    is then downloaded in the directory specified by `out_dir`.
    
    The function also checks to see if the selected remote file exists locally.
    If it does, it checks that the remote and local file sizes are identical. 
    If they are, file isn't downloaded, but if they are different, the remote 
    file is downloaded. 

    Parameters
    ----------
    platform: str
        One of three: MOLA, MOLT MOTA
    product: str
        The product name, such as MOD09GA.005 or MYD15A2.005. Note that you 
        need to specify the collection number (005 in the examples)
    year: int
        The year of interest
    tile: str
        The tile (e.g., "h17v04")
    proxy: dict
        A proxy definition, such as {'http': 'http://127.0.0.1:8080', \
        'ftp': ''}, etc.
    doy_start: int
        The starting day of the year.
    doy_end: int 
        The ending day of the year.
    base_url: str, url
        The URL to use. Shouldn't be changed, unless USGS change the server.
    out_dir: str 
        The output directory. Will be create if it doesn't exist
    ruff: Boolean
        Check to see what files are already available and download them without
        testing for file size etc.
    verbose: Boolean
        Whether to sprout lots of text out or not.

    Returns
    -------
    Nothing
    """
    
    if proxy is not None:
        proxy = urllib2.ProxyHandler( proxy )
        opener = urllib2.build_opener( proxy )
        urllib2.install_opener( opener )
    
    if not os.path.exists ( out_dir ):
        if verbose:
            LOG.info("Creating outupt dir %s" % out_dir )
        os.makedirs ( out_dir )
    if doy_end == -1:
        if calendar.isleap ( year ):
            doy_end = 367
        else:
            doy_end = 366
    
    dates = [time.strftime("%Y.%m.%d", time.strptime( "%d/%d" % ( i, year ), \
            "%j/%Y"))  for i in xrange(doy_start, doy_end )]
    url = "%s/%s/%s/" % ( base_url, platform, product )
    dates = parse_modis_dates ( url, dates, product, out_dir, ruff=ruff )
    for date in dates:
        #req = urllib2.Request ( "%s/%s" % ( url, date), None, HEADERS )
        try:
            html = return_url ( "%s/%s" % ( url, date ) )
            #html = urllib2.urlopen(req).readlines()
            for line in html:
                if line.find( tile ) >=0  and line.find(".hdf") >= 0 and \
                    line.find(".hdf.xml") < 0:
                    fname = line.split("href=")[1].split(">")[0].strip('"')
                    req = urllib2.Request ( "%s/%s/%s" % ( url, date, fname), \
                        None, HEADERS )
                    download = False
                    if not os.path.exists ( os.path.join( out_dir, fname ) ):
                        # File not present, download
                        download = True
                    else:
                        the_remote_file = urllib2.urlopen(req)
                        remote_file_size = int ( \
                            the_remote_file.headers.dict['content-length'] )
                        local_file_size = os.path.getsize(os.path.join( \
                            out_dir, fname ) )
                        if remote_file_size != local_file_size:
                            download = True
                        
                    if download:
                        if verbose:
                            LOG.info ( "Getting %s..... " % fname )
                        with open ( os.path.join( out_dir, fname ), 'wb' ) \
                                as local_file_fp:
                            shutil.copyfileobj(urllib2.urlopen(req), \
                                local_file_fp)
                            if verbose:
                                LOG.info("Done!")
                    else:
                        if verbose:
                            LOG.info ("File %s already present. Skipping" % \
                                fname )

        except urllib2.URLError:
            LOG.info("Could not find data for %s(%s) for %s" % ( product, \
                platform, date ))
    if verbose:
        LOG.info("Completely finished downlading all there was")
        

if __name__ == "__main__":
    parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), \
        usage=globals()['__doc__'])
    parser.add_option ('-v', '--verbose', action='store_true', \
        default=False, help='verbose output')
    parser.add_option ('-s', '--platform', action='store', dest="platform", \
        type=str, help='Platform type: MOLA, MOLT or MOTA' )
    parser.add_option ('-p', '--product', action='store', dest="product", \
        type=str, help="MODIS product name with collection tag at the end " + \
            "(e.g. MOD09GA.005)" )
    parser.add_option ('-t', '--tile', action="store", dest="tile", \
        type=str, help="Required tile (h17v04, for example)")
    parser.add_option ( "-y", "--year", action="store", dest="year", \
        type=int, help="Year of interest" )
    parser.add_option('-o', '--output', action="store", dest="dir_out", \
        default=".", type=str, help="Output directory" )
    parser.add_option('-b', '--begin', action="store", dest="doy_start", \
        default=1, type=int, help="Starting day of year (DoY)" )
    parser.add_option('-e', '--end', action="store", dest="doy_end", \
        type=int, default=-1, help="Ending day of year (DoY)" )
    parser.add_option('-r', '--proxy', action="store", dest="proxy", \
        type=str, default=None, help="HTTP proxy URL" )
    parser.add_option('-q', '--quick', action="store_true", dest="quick", \
        default=False, help="Quick check to see whether files are present" )
    (options, args) = parser.parse_args()
    if not ( options.platform in [ "MOLA", "MOTA", "MOLT" ] ) :
        LOG.fatal ("`platform` has to be one of MOLA, MOTA, MOLT")
        sys.exit(-1)
    if options.proxy is not None:
        PROXY = { 'http': options.proxy }
    else:
        PROXY = None
        
    
    
    get_modisfiles ( options.platform, options.product, options.year, \
            options.tile, PROXY, \
            doy_start=options.doy_start, doy_end=options.doy_end, \
            out_dir=options.dir_out, \
            verbose=options.verbose, ruff=options.quick )
