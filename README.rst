get_modis
==========
:Info: MODIS data product granule downloader
:Author: J Gomez-Dans <j.gomez-dans@ucl.ac.uk>
:Date: $Date: 2013-06-17 17:00:00 +0000  $
:Description: README file

Description
--------------

This repository contains a Python script (and executable) that allows one to download MODIS data granules for different products and periods. 

The code is quite simple and generic, and should work with most standard Python installations.

See more `here <http://jgomezdans.github.io/downloading-modis-data-with-python.html>`_.

Usage
------

This is a command line tool. It has only been tested on Linux, but should also work with Windows. There are a number of options that can be used, and you can get a list of them issuing the ``-h`` or ``--help`` commands. Also note that as of summery 2016, you **must have a username and password** pair to access the server. If you haven't got one, you can get it `here <https://earthdata.nasa.gov/>`_. You will also need to allow your user account to access the USGS MODIS archive (you only need to do this once).

.. code-block: bash

    $ ./get_modis.py -h
    Usage
    =====
      
    SYNOPSIS
        
    ./get_modis.py [-h,--help] [--username=USERNAME, -u USERNAME] [--password=PASSWORD, -P PASSWORD] 
    [--verbose, -v] [--platform=PLATFORM, -s PLATFORM]    [--proxy=PROXY -p PROXY]     
    [--product=PRODUCT, -p PRODUCT] [--tile=TILE, -t TILE]     [--year=YEAR, -y YEAR] 
    [--output=DIR_OUT, -o DIR_OUT]     [--begin=DOY_START, -b DOY_START] [--end=DOY_END, -e DOY_END]

    DESCRIPTION

    A program to download MODIS data from the USGS website using the HTTP
    transport. This program is able to download daily, monthly, 8-daily, etc 
    products for a given year, it only requires the product names (including the 
    collection number), the year, the MODIS reference tile and additionally, where
    to save the data to, and whether to verbose. The user may also select a 
    temporal period in terms of days of year.  Note that as of summer 2016, NASA
    requires that all downloads are identified with a username and password.

    EXAMPLES

        The following example downloads daily surface reflectance from the TERRA 
        platform for tile h17v04 for 2004, between DoY 153 and 243:
        
        $ ./get_modis.py -v -p MOD09GA.005 -s MOLT -y 2004 -t h17v04 -o /tmp/         -b 153 -e 243
        
        The script will also work with monthly or 8-daily composites. Here's how 
        you download the monthly MCD45A1 (burned area) product for the same period:
        
        $ ./get_modis.py -v -p MCD45A1.005 -s MOTA -y 2004 -t h17v04 -o /tmp/         -b 153 -e 243
            

    EXIT STATUS
        No exit status yet, can't be bothered.

    AUTHOR

        J Gomez-Dans <j.gomez-dans@ucl.ac.uk>
        See also http://github.com/jgomezdans/get_modis/



    Options
    =======
    --help, -h              show this help message and exit
    --verbose, -v           verbose output
    --platform=PLATFORM, -s PLATFORM
                            Platform type: MOLA, MOLT or MOTA
    --product=PRODUCT, -p PRODUCT
                            MODIS product name with collection tag at the end
                            (e.g. MOD09GA.005)
    --tile=TILE, -t TILE    Required tile (h17v04, for example)
    --year=YEAR, -y YEAR    Year of interest
    --output=DIR_OUT, -o DIR_OUT
                            Output directory
    --begin=DOY_START, -b DOY_START
                            Starting day of year (DoY)
    --end=DOY_END, -e DOY_END
                            Ending day of year (DoY)
    --proxy=PROXY, -r PROXY
                            HTTP proxy URL
    --quick, -q             Quick check to see whether files are present
    
Useful things to bear in mind:

* The platform **MUST** be one of ``MOLA`` (Aqua), ``MOLT`` (Terra) or ``MOTA`` (Combined).
* The product must have an indication of the collection follwing the product name. i.e. ``MCD45A1.005``)
* The ``--begin`` and ``--end`` flags are optional, and yu can ignore them if you just want the complete year
* Use the ``--proxy`` option to set the required proxy. It should be read from the environment variable, but this is added flexiblity

The code has some logic not to download files several times, and the overall behaviour rests on the ``--quick`` flag: if this flag is **not** set, then the program will look at the remote available files and skip any files that are present and have the same file size as the remote. In some cases, this could lead to duplicities are re-processing takes place. If the ``--quick`` flag is set, then when the remote list of available dates is created, any present files that match the requested product and year will be ignored, irrespective of file size. This can mean that files that failed to download half way through will not the downloaded, but it's an overall faster process if a download failed halfway through a year.
