#!/usr/bin/env python
# get_modis A MODIS land product downloading tool
# Copyright (c) 2013-2016 J Gomez-Dans, 2016, 2020 Andrew Tedstone. All rights reserved.
#
# This file is part of get_modis.
#
# get_modis is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# get_modis is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import argparse
import os
try:
    import urllib.request as urllib2
except ImportError:
    import urllib2
import time
import calendar
import logging
import sys
import fnmatch
import requests
from bs4 import BeautifulSoup


__author__ = "J Gomez-Dans & Andrew Tedstone"
__copyright__ = "Copyright 2013-2016 J Gomez-Dans, portions 2016 Andrew Tedstone"
__version__ = "1.4.0"
__license__ = "GPLv3"
__email__ = "j.gomez-dans@ucl.ac.uk; andrew.tedstone@unifr.ch"

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
    Andrew Tedstone <a.j.tedstone@bristol.ac.uk>
    See also http://github.com/jgomezdans/get_modis/

"""

LOG = logging.getLogger( __name__ )
OUT_HDLR = logging.StreamHandler( sys.stdout )
OUT_HDLR.setFormatter( logging.Formatter( '%(asctime)s %(message)s') )
OUT_HDLR.setLevel( logging.INFO )
LOG.addHandler( OUT_HDLR )
LOG.setLevel( logging.INFO )

HEADERS = { 'User-Agent' : 'get_modis Python %s' % __version__ }

CHUNKS = 65536

# ------------------------------------------------------------------------------
EARTHDATA_SSO_PORTAL = 'https://urs.earthdata.nasa.gov/'
EARTHDATA_SSO_LOGIN  = 'https://urs.earthdata.nasa.gov/login'

DATA_PROVIDERS = {
    'USGS': 'https://e4ftl01.cr.usgs.gov',
    'NSIDC': 'https://n5eil01u.ecs.nsidc.org'
}
DEFAULT_DATA_PROVIDER = 'USGS'
#-------------------------------------------------------------------------------


def return_url(url, s):
    the_day_today = time.asctime().split()[0]
    the_hour_now = int(time.asctime().split()[3].split(":")[0])
    # if the_day_today == "Wed" and 14 <= the_hour_now <= 17:
    #     LOG.info("Sleeping for %d hours... Yawn!" % (18 - the_hour_now))
    #     time.sleep(60 * 60 * (18 - the_hour_now))

    r = s.get(url)
    parsed_html = BeautifulSoup(r.text, 'lxml')
    #req = urllib2.Request("%s" % (url), None, HEADERS)
    #html = urllib2.urlopen(req).readlines()
    return parsed_html


def parse_modis_dates (s, url, dates, product, tile, out_dir, check_sizes=False ):
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
    check_sizes: bool
        Default False. If true then this function will not bother to check 
        for existing local files as the user wants the script to do fine
        checking by comparing local and remote file sizes instead of just
        relying on .part suffixes for incomplete files.

    Returns
    -------
    A (sorted) list with the dates that will be downloaded.
    """

    if not check_sizes:
        product = product.split(".")[0]
        already_here = fnmatch.filter(os.listdir(out_dir),
                                      "%s*%s*hdf" % (product, tile))
        already_here_dates = [x.split(".")[-5][1:]
                              for x in already_here]

    html = return_url(url, s)
    links = html.body.find_all('a')

    available_dates = []
    for link in links:

        the_date = link.get('href')[:-1]
        
        if not check_sizes:
            try:
                modis_date = time.strftime("%Y%j",
                                           time.strptime(the_date,
                                                         "%Y.%m.%d"))
            except ValueError:
                continue
            if modis_date in already_here_dates:
                continue
            else:
                available_dates.append(the_date)

        else:
            available_dates.append(the_date)

    dates = set(dates)
    available_dates = set(available_dates)
    suitable_dates = list(dates.intersection(available_dates))
    suitable_dates.sort()
    return suitable_dates


def get_modisfiles(username, password, platform, product, year, tile, proxy,
                   doy_start=1, doy_end=-1,
                   base_url=DATA_PROVIDERS[DEFAULT_DATA_PROVIDER], out_dir=".",
                   verbose=False,
                   reconnection_attempts=200,
                   check_sizes=False):

    """Download MODIS products for a given tile, year & period of interest

    This function uses the `urllib2` module to download MODIS "granules" from
    the USGS website. The approach is based on downloading the index files for
    any date of interest, and parsing the HTML (rudimentary parsing!) to search
    for the relevant filename for the tile the user is interested in. This file
    is then downloaded in the directory specified by `out_dir`.

    The function can also check if complete files exist locally.
    If it does, it checks that the remote and local file sizes are identical.
    If they are, file isn't downloaded, but if they are different, the remote
    file is downloaded.

    Parameters
    ----------
    username: str
        The EarthData username string
    password: str
        The EarthData username string
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
    verbose: Boolean
        Whether to sprout lots of text out or not.
    reconnection_attempts: int, default 5
        Number of times to attempt to open HTTP Connection before giving up.
    check_sizes : boolean, default False
        If True then first retrieve remote file size to check against local file.
        Only use on legacy dataset directories which were downloaded before 
        13 October 2016, when code based switched to naming files in progress
        with .part, rendering this option unnecessary.

    Returns
    -------
    Nothing
    """

    if proxy is not None:
        proxy = urllib2.ProxyHandler(proxy)
        opener = urllib2.build_opener(proxy)
        urllib2.install_opener(opener)

    if not os.path.exists(out_dir):
        if verbose:
            LOG.info("Creating outupt dir %s" % out_dir)
        os.makedirs(out_dir)
    if doy_end == -1:
        if calendar.isleap(year):
            doy_end = 367
        else:
            doy_end = 366

    dates = [time.strftime("%Y.%m.%d", time.strptime("%d/%d" % (i, year),
                                                     "%j/%Y")) for i in
             range(doy_start, doy_end)]
    url = "%s/%s/%s/" % (base_url, platform, product)
    dates_available = None
    
    count_reconn_attempts = 0
    while count_reconn_attempts <= reconnection_attempts:
        if verbose:
            LOG.info("Session Attempt %d" % (count_reconn_attempts+1))

        try:
            with requests.Session() as s:
                s.mount(base_url, requests.adapters.HTTPAdapter(max_retries=5))

                ## Login to the EarthData Service for this session
                # First get an authenticity token
                r = s.get(EARTHDATA_SSO_PORTAL)
                parsed_html = BeautifulSoup(r.text, 'lxml')
                token = parsed_html.body.find('input', attrs={'name':'authenticity_token'})['value']

                # Now do the login, providing the token
                r = s.post(EARTHDATA_SSO_LOGIN, 
                    data={'username':username, 'password':password, 'authenticity_token':token,
                    'utf8':'&#x2713;'})
                if not r.ok:
                    raise IOError('Could not log in to EarthData server: %s' %r )

                check_login = BeautifulSoup(r.text, 'lxml')
                check_login = check_login.body.find('div', attrs={'class':'eui-banner--danger'})
                if check_login is None:
                    print('LOGGED IN')
                else:
                    raise IOError('Could not log into EarthData server: %s' %check_login)

                # Reset return object
                r = None


                if dates_available is None:
                    dates_available = parse_modis_dates(s, url, dates, product, tile, out_dir, 
                        check_sizes=check_sizes)

                while len(dates_available) > 0:

                    date = dates_available.pop(0)

                    r = s.get("%s/%s" % (url, date), verify=False)
                    download = False
                    for line in r.text.split("\n"):

                        if (line.find(tile) >= 0) & \
                            (line.find(".hdf") >= 0 > line.find(".hdf.xml")):

                            # Find remote file name and URL
                            fname = line.split("href=")[1].split(">")[0].strip('"')
                            the_url = "%s%s/%s" % (url, date, fname)

                            # Set download flag
                            download = True
                            r = None
                            # File found so break out of loop
                            break

                    if not download:
                        LOG.info('File not found for date: %s' % date)
                        continue


                    # If local file present, check if it is complete
                    # Incomplete files will still have .part suffix
                    rfile = None
                    if os.path.exists(os.path.join(out_dir, fname)):

                        if check_sizes:
                            # Open link to remote file
                            #r1 = s.request('get', the_url, timeout=(5,5))
                            rfile = s.get(the_url, stream=True, timeout=(5,5))
                            if not rfile.ok:
                                raise IOError("Can't access... [%s]" % the_url)
                            # Get remote file size
                            remote_file_size = int(rfile.headers['content-length'])

                            local_file_size = os.path.getsize(os.path.join( \
                                out_dir, fname ) )

                            # Skip download if local and remote sizes match
                            if remote_file_size == local_file_size:
                                download = False
                                if verbose:
                                    LOG.info("File %s already present. Skipping" % fname)
                            else:
                                if verbose:
                                    LOG.info("Local version of %s incomplete, will be overwritten." % fname)
                                  
                        else:
                            download = False


                    if download:

                        # Open stream to remote file
                        # Stream might have been opened above, check
                        if rfile is None:
                            rfile = s.get(the_url, stream=True, timeout=(9, 9))
                            if not rfile.ok:
                                raise IOError("Can't access... [%s]" % the_url)
                            # Get remote file size
                            remote_file_size = int(rfile.headers['content-length'])

                        LOG.info("Starting download on %s(%d bytes) ..." %
                                 (os.path.join(out_dir, fname), remote_file_size))
                        with open(os.path.join(out_dir, fname + '.part'), 'wb') as fp:
                            for chunk in rfile.iter_content(chunk_size=CHUNKS):
                                if chunk:
                                    fp.write(chunk)
                            #fp.flush() # disabled 2016/11/15, takes ages with no clear benefit
                            #os.fsync(fp.fileno())
                            if verbose:
                                LOG.info("\tDone!")

                        # Once download finished, remove .part suffix
                        os.rename(os.path.join(out_dir, fname + '.part'),
                            os.path.join(out_dir, fname))


                # Finished looping through dates with while
                if verbose:
                    LOG.info("All downloads complete")

                return

        except requests.exceptions.Timeout:
            # Don't increment connection number
            dates.insert(0, date)
            if verbose:
                LOG.info('Timeout error, opening new session')
            continue

        except requests.exceptions.ConnectionError:

            # Increment number of reconnection attempts
            count_reconn_attempts += 1

            # Put the most recent (failed) date back into the list
            dates_available.insert(0, date)

            # Begin the re-connection process (unless max attempts reached)    
            continue

        # If we manage to get here then the download session has been successful
        # Break out of the session reconnect loop
        break

    # Raise error if download session failed
    if count_reconn_attempts == reconnection_attempts:
        print('Maximum number of Session reconnection attempts reached.')
        raise requests.exceptions.ConnectionError


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A program to download MODIS data \
        using HTTP \
        transport. This program is able to download daily, monthly, 8-daily, etc \
        products for a given year, it only requires the product names (including the \
        collection number), the year, the MODIS reference tile and additionally, where \
        to save the data to, and whether to verbose. The user may also select a \
        temporal period in terms of days of year.")

    parser.add_argument('-u', '--username', dest="username",
                      help="EarthData username", 
                      required=True)
    parser.add_argument('-P', '--password',dest="password",
                      help="EarthData password", 
                      required=True)
    parser.add_argument('-v', '--verbose', action='store_true',
                      default=False, help='verbose output')
    parser.add_argument('-s', '--platform', action='store', dest="platform",
                      type=str, help='Platform type: MOLA, MOLT, MOTA or MOST', 
                      required=True)
    parser.add_argument('-p', '--product', dest="product",
                      type=str,
                      help="MODIS product name with collection tag at the end " +
                           "(e.g. MOD09GA.005)",
                      required=True)
    parser.add_argument('-t', '--tile', dest="tile",
                      type=str, help="Required tile (h17v04, for example)",
                      required=True)
    parser.add_argument("-y", "--year", dest="year",
                      type=int, help="Year of interest",
                      required=True)
    parser.add_argument('-o', '--output', dest="dir_out",
                      default=".", type=str, help="Output directory")
    parser.add_argument('-b', '--begin', dest="doy_start",
                      default=1, type=int, help="Starting day of year (DoY)")
    parser.add_argument('-e', '--end', dest="doy_end",
                      type=int, default=-1, help="Ending day of year (DoY)")
    parser.add_argument('-r', '--proxy', dest="proxy",
                      type=str, default=None, help="HTTP proxy URL")
    parser.add_argument('-c', '--checksizes', action="store_true", dest="checksizes",
                      default=False,
                      help="Compare size of local and remote files")
    parser.add_argument('-l', '--provider', dest="provider",
                      default='USGS',
                      help='Specify a data provider: one of USGS, NSIDC.')
    parser.add_argument('-d', '--baseurl', dest="baseurl",
                      default=None,
                      help="Specify base URL to download from. Only needed in the \
                      case that your data are not stored with one of the \
                      existing --providers. If this parameter is specified then \
                      it will override any choice made for --provider.")
    args = parser.parse_args()
    
    if not (args.platform in ["MOLA", "MOTA", "MOLT", "MOST"]):
        LOG.fatal("Unknown `platform`.")
        sys.exit(-1)
    if not (args.provider in DATA_PROVIDERS):
        LOG.fatal("`Unknown `provider`.")
    
    # If a baseurl is provided then allow it to override the data provider.
    if args.baseurl is None:
        baseurl = DATA_PROVIDERS[args.provider]
    else:
        baseurl = args.baseurl

    if args.proxy is not None:
        PROXY = {'http': options.proxy}
    else:
        PROXY = None


    get_modisfiles(args.username, args.password, args.platform,
                   args.product, args.year,
                   args.tile, PROXY,
                   doy_start=args.doy_start, doy_end=args.doy_end,
                   out_dir=args.dir_out,
                   verbose=args.verbose, check_sizes=args.checksizes,
                   base_url=baseurl)
