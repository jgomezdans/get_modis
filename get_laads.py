#!/usr/bin/env python

import json
import logging
import optparse
import sys
from concurrent import futures
from pathlib import Path

import requests
from tqdm.auto import tqdm

__author__ = "J Gomez-Dans"
__copyright__ = "Copyright 2020 J Gomez-Dans"
__version__ = "1.0.0"
__license__ = "GPLv3"
__email__ = "j.gomez-dans@ucl.ac.uk"

HELP_TEXT = """
SYNOPSIS
./get_laads.py [-h,--help] 
[--verbose, -v] 
[--product=PRODUCT, -p PRODUCT]      [--year=YEAR, -y YEAR]
[--output=DIR_OUT, -o DIR_OUT]     [--doys=DOY,DOY, -b DOY,DOY]
DESCRIPTION
A program to download MODIS data from the LAADS website using the HTTP
transport. 
EXIT STATUS
    No exit status yet, can't be bothered.
AUTHOR
    J Gomez-Dans <j.gomez-dans@ucl.ac.uk>
    See also http://github.com/jgomezdans/get_modis/
"""


LOG = logging.getLogger(__name__)
OUT_HDLR = logging.StreamHandler(sys.stdout)
OUT_HDLR.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
OUT_HDLR.setLevel(logging.INFO)
LOG.addHandler(OUT_HDLR)
LOG.setLevel(logging.DEBUG)

HEADERS = {"User-Agent": "get_modis Python %s" % __version__}

CHUNKS = 65536


URL = "https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/61"


def download_products(url, loc):
    fname = loc / url.split("/")[-1]
    r = requests.get(url)
    with fname.open(mode="wb") as fp:
        fp.write(r.content)
    LOG.debug("Saved " + str(fname))


def download_filelist(url):
    r = requests.get(url)
    return json.loads(r.content)


def make_query(location, product, years, doys, n_threads=8):
    location = Path(location)
    grabber = lambda x: download_products(x, location)
    if not location.exists():
        raise IOError(f"Destination folder {location} does not exist!")
    if type(doys) != list:
        doys = [
            doys,
        ]
    if type(years) != list:
        years = [
            years,
        ]
    for year in years:
        LOG.info(f"Doing year {year}")
        urls = [f"{URL}/{product}/{year}/{doy:03d}.json" for doy in doys]
        dload_files = []
        with futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
            dload_files = list(
                tqdm(executor.map(download_filelist, urls), total=len(urls))
            )
        datas = list(zip(doys, dload_files))
        req_products = [
            f"{URL}/{years}/{doy:03}/{x['name']}"
            for doy, z in datas
            for x in z
        ]
        LOG.info(
            f"\tWill now download {len(req_products)} products in total..."
        )
        with futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
            dload_files = list(
                tqdm(
                    executor.map(grabber, req_products),
                    total=len(req_products),
                )
            )
        LOG.info("\tDone with this year!")


def main():
    parser = optparse.OptionParser(
        formatter=optparse.TitledHelpFormatter(), usage=HELP_TEXT
    )
    parser.add_option(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="verbose output",
    )
    parser.add_option(
        "-p",
        "--product",
        action="store",
        dest="product",
        type=str,
        help="MODIS product name "
        + "(e.g. MOD05_L2)",
    )
    parser.add_option(
        "-o",
        "--output",
        action="store",
        dest="dir_out",
        default=".",
        type=str,
        help="Output directory",
    )
    parser.add_option(
        "-y",
        "--year",
        action="store",
        dest="year",
        type=str,
        help="Years to consider (comma-separated)",
    )
    parser.add_option(
        "-d",
        "--doys",
        action="store",
        dest="doys",
        type=str,
        default=None,
        help="Doys to consider (comma-separated)",
    )

    (options, args) = parser.parse_args()
    if options.verbose:
        LOG.setLevel(logging.DEBUG)
    else:
        LOG.setLevel(logging.INFO)
    product = options.product.upper()
    years = list(map(int, options.year.split(",")))
    doys = list(map(int, options.doys.split(",")))
    LOG.info("MODIS downloader by J Gomez-Dans...")
    LOG.info("Starting downloading")

    make_query(options.dir_out, product, years, doys)


if __name__ == "__main__":
    main()
