get_modis
==========
:Info: MODIS data product granule downloader
:Author: J Gomez-Dans <j.gomez-dans@ucl.ac.uk>, Andrew Tedstone <andrew.tedstone@unifr.ch>
:Date: $Date: 2013-06-17 17:00:00 +0000  $
:Description: README file

Description
--------------

This repository contains a Python script (and executable) that allows one to download MODIS data granules for different products and periods. 

The code is quite simple and generic but requires at least a couple of specific libraries not usually available by default: Beautiful Soup (conda-forge: `bs4`) and lxml (conda-forge: `lxml`).

See more `here <http://jgomezdans.github.io/downloading-modis-data-with-python.html>`_.

Usage
------

This is a command line tool. It has only been tested on Linux, but should also work with Windows. There are a number of options that can be used, and you can get a list of them
issuing the ``-h`` or ``--help`` commands:

.. code-block: bash

    $ ./get_modis.py -h


An example command to download version 6 of the MOD10A1 product, held at the NSIDC, looks like this:

.. code-block: bash
    
    $ get_modis.py -u <earthdata_username> -P <earthdata_password> -s MOST -l NSIDC -t h16v02 -b 200 -e 202 -y 2016 -v -p MOD10A1.006

You will need a NASA EarthData login to use this tool.

Useful things to bear in mind:

* The platform is one of ``MOLA`` (Aqua), ``MOLT`` (Terra) or ``MOTA`` (Combined) for USGS-served products (default).
* To download products from NSIDC user `-l NSIDC` or `--provider=NSIDC`.
* The product must have an indication of the collection following the product name. i.e. ``MCD45A1.005``)
* The ``--begin`` and ``--end`` flags are optional, and yu can ignore them if you just want the complete year
* Use the ``--proxy`` option to set the required proxy. It should be read from the environment variable, but this is added flexiblity

The code has some logic not to download files several times, and the overall behaviour rests on the ``--quick`` flag: if this flag is **not** set, then the program will look at the remote available files and skip any files that are present and have the same file size as the remote. In some cases, this could lead to duplicities are re-processing takes place. If the ``--quick`` flag is set, then when the remote list of available dates is created, any present files that match the requested product and year will be ignored, irrespective of file size. This can mean that files that failed to download half way through will not the downloaded, but it's an overall faster process if a download failed halfway through a year.
