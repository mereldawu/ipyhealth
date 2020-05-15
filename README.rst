=========
ipyhealth
=========


.. image:: https://img.shields.io/pypi/v/ipyhealth.svg
        :target: https://pypi.python.org/pypi/ipyhealth

.. image:: https://github.com/mereldawu/ipyhealth/workflows/ipyhealth%20package/badge.svg

.. image:: https://readthedocs.org/projects/ipyhealth/badge/?version=latest
        :target: https://ipyhealth.readthedocs.io/en/latest/?badge=latest
        :alt: Documentation Status


ipyhealth is a Python3 library to parse, wrangle and plot `Apple Health data <https://developer.apple.com/documentation/healthkit/>`_ from all Apple devices.

ipyhealth makes it easy for developers to obtain the Apple Health data, saved as four `pandas` dataframes:

1. `Samples <https://developer.apple.com/documentation/healthkit/samples>`_: data that is recorded at a specific time, including HKQuantitySample (height, heart rate, energy consumed, etc.), HKCategorySample (user in bed, asleep, or awake) and HKCorrelation (food and blood pressure).

2. `Workouts <https://developer.apple.com/documentation/healthkit/workouts_and_activity_rings>`_: dataframe containing type (Walk, Run, Hike, Yoga, etc.), duration, energy burned and distance of a recorded workout.

3. `Activity Summary <https://developer.apple.com/documentation/healthkit/hkactivitysummary>`_: dataframe containing the move, exercise and stand data for a given day.

4. `Routes <https://developer.apple.com/documentation/healthkit/workouts_and_activity_rings/reading_route_data>`_: dataframe containing the location of the route file (.gpx file exported), the latitude, lonitude and elevation at different points of the route.

© ipyhealth contributors 2020 (see `AUTHORS <https://github.com/mereldawu/ipyhealth/blob/master/AUTHORS.rst>`_) under the `MIT license <https://github.com/mereldawu/ipyhealth/blob/master/LICENSE>`_.

.. * Documentation: https://ipyhealth.readthedocs.io.


Installation
-------------

Install using `pip <https://pip.pypa.io/en/latest/>`_ with:

.. code-block:: bash

  pip install ipyhealth

Or install from Github using:

.. code-block:: bash

  pip install git+https://github.com/mereldawu/ipyhealth.git


Usage
------
.. code-block:: python

  from ipyhealth.parser import AppleHealthParser

  health_data = AppleHealthParser(
        in_file = '/location/to/apple_health_export',
        from_date = None, # date to start parsing, i.e. datetime(2020, 5, 1)
        verbose = True, # print extract progress and success status, i.e. True/False
        nprocs = 4 # number of CPUs to use
  )

  type(health_data.records) # pd.DataFrame
  type(health_data.workouts) # pd.DataFrame
  type(health_data.activities) #pd.DataFrame
  type(health_data.routes) #pd.DataFrame


To export Apple Health data
----------------------------

Download and extract the Apple Health data to a desired location:

1. On your iPhone, open Health App.
2. Click on your avatar > Scroll to the bottom > Export all health data (this takes some time).
3. Select Save to Files (this is only available for iOS 13 and above, for lower verions of iOS save at a location where you can read it).
4. Unzip the export.zip folder, which contains `apple_health_export` folder:

| apple_health_export
| ├── export.xml (the main file that is parsed)
| ├── export_cda.xml (the `Clinical Document Architecture <https://en.wikipedia.org/wiki/Clinical_Document_Architecture>`_ file is not used)
| ├── **workout_routes**
|    ├── route_{timestamp}.gpx (the GPS data for the associated workout)
|    ├──route_{timestamp}.gpx (these contain the location information)


Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
