# -*- coding: utf-8 -*-
# pylint: disable=logging-fstring-interpolation
"""
Extract data from Apple Health App's export.xml as pandas dataframe.
"""

import os
import re
import math
import json
import string
import logging
from typing import Union
from datetime import datetime
from inspect import currentframe
from unicodedata import normalize
from xml.etree import ElementTree
from multiprocessing import Process
from collections import ChainMap
from tqdm import tqdm
from pytz import timezone
from dateutil.parser import parse

import gpxpy
import gpxpy.gpx
import pandas as pd
from inflection import underscore

from . import templates

try:
    import importlib.resources as pkg_resources
except ImportError:
    import importlib_resources as pkg_resources

PUNC = string.punctuation.replace('.', '')
template = pkg_resources.read_text(templates, 'activity_format.json')
NODES = json.loads(template)


class AppleHealthFormatter():
    """The Formatter object formats the Apple Health data records."""

    def __init__(self, node_tag: str, node: dict):
        """The Formatter object formats the Apple Health data records.

        Args:
            node_tag: the tag of the element,
                i.e. ['Workout', 'Record', 'ActivitySummary]
            node: the child of the root node, corresponding to the node_tag
        """
        self.node_tag = node_tag
        self.attributes = node
        self.values = self.format_values()

    @staticmethod
    def format_type(inputs: tuple) -> dict:
        """Format the type activity type based on the regex pattern provided

        Args:
            inputs[0] (str): the regex pattern for identifying the type of
                activity, such as r"^HK(.+)ActivityType(.+)$"
            inputs[1] (str): the activity attribute, such as HKWorkoutTypeYoga

        Returns:
            {activity_type, activity}: a dictionary on the activity attribute
        """
        activity_type, activity = re.findall(inputs[0], inputs[1])[0]
        return {'activity_type': activity_type, 'activity': activity}

    @staticmethod
    def format_string(inputs: (str, str)) -> (str, str):
        """Return snake style column name and format unicode strings by
        changing both original and length"""
        return underscore(inputs[0]), normalize("NFKD", inputs[1])

    @staticmethod
    def format_numerics(inputs: (str, str)) -> (str, float):
        """Return snake style column name and format string input into numeric
         output"""
        return underscore(inputs[0]), float(inputs[1])

    @staticmethod
    def format_no_format(inputs: (str, str)) -> (str, str):
        """Return the snake style column name without formattng the values"""
        return underscore(inputs[0]), inputs[1]

    @staticmethod
    def format_date(inputs: (str, str)) -> (str, datetime):
        """Return the snake style column name and format string input to
        date object"""
        return underscore(inputs[0]), parse(inputs[1])

    @staticmethod
    def format_device(device_string: (str, str)) -> dict:
        """Return the snake style column names and format device string input
        to multiple device values"""

        def clean_device_info(device):
            info = device.split(":")
            key = f"device_{info[0].strip(PUNC).strip().lower()}"
            val = ':'.join(info[1:]).strip(PUNC).strip()
            return {key: val}

        devices = [d for d in device_string.split(',') if ':' in d]

        return dict(ChainMap(*map(clean_device_info, devices)))

    @staticmethod
    def format_standard(inputs: (str, str)) -> (str, float):
        """Return the snake style column names and standardize duration,
        distance and energy burned into the same unit (minute, km and kcal)"""

        st_key, st_val, unit_val = inputs
        st_key = underscore(st_key.replace('total', ''))
        outputs = None

        if st_key in ['duration']:
            col_name = f'{st_key}_min'

            if unit_val == "min":
                outputs = col_name, float(st_val)
            elif unit_val == "sec":
                outputs = col_name, float(st_val) / 60
            else:
                raise NotImplementedError("Unit {unit} not implemented.")

        elif st_key in ['distance', 'energy_burned']:
            col_name = f'{st_key}_{unit_val}' \
                if unit_val.startswith('k') else f'{st_key}_k{unit_val}'

            if unit_val in ("km", "kcal"):
                outputs = col_name, float(st_val)
            elif unit_val in ("m", "cal"):
                outputs = col_name, float(st_val) / 1000
            else:
                raise NotImplementedError("Unit {unit} not implemented.")

        else:
            raise NotImplementedError("Unit {unit} not implemented.")

        return outputs

    def format_values(self) -> dict:
        """Return the attributes as dictionary, formatted based on the
        attribute type, such as date, string, device, etc. """

        formatted_vals = {}

        for ftype, attr_names in NODES[self.node_tag]['formats'].items():

            if ftype != 'standard':

                attr_vals = []
                for aname in attr_names:
                    try:
                        attr_vals.append(self.attributes[aname])
                    except KeyError:
                        pass

                if ftype == 'type':
                    patterns = [
                        NODES[self.node_tag]['pattern']
                    ]*len(attr_names)
                    d = list(
                        map(self.format_type, zip(patterns, attr_vals))
                    )[0]

                elif ftype == 'string':
                    d = map(self.format_string, zip(attr_names, attr_vals))

                elif ftype == 'no_format':
                    d = map(self.format_no_format, zip(attr_names, attr_vals))

                elif ftype == 'device':
                    if attr_vals:
                        d = list(map(self.format_device, attr_vals))[0]

                elif ftype == 'date':
                    d = map(self.format_date, zip(attr_names, attr_vals))

                elif ftype == 'numerics':
                    d = map(self.format_numerics, zip(attr_names, attr_vals))
                else:
                    raise NotImplementedError(f"{self.attributes} not\
                implemented.")

            else:
                attr_type = [attr_type for attr_type, attr_unit in attr_names]
                attr_vals = [self.attributes[an] for an, _ in attr_names]
                attr_units = [self.attributes[au] for _, au in attr_names]
                d = map(
                    self.format_standard,
                    zip(attr_type, attr_vals, attr_units)
                )

            formatted_vals = {**formatted_vals, **dict(d)}

        return formatted_vals


class AppleHealthParser():
    """Creates pandas dataframes of activities, workouts and records based on
    the Apple Health data records."""

    def __init__(
            self,
            in_file: str,
            from_date: datetime = None,
            logger_name: str = None,
            verbose: bool = True,
            nprocs: int = 4,
        ):
        """The Parser object creates pandas dataframes of activities,
        workouts and records based on the Apple Health data records.

        Args:
            in_file: the full filepath and filename of the xml data
            logger_name: the name of the logger, if not provided will be the
                script name that instantiates the object
            verbose: whether to print the statistics of the data, default True
            nprocs: the number of processes to use, default to 4
        """

        self.export_path = in_file
        self.logger = self.get_logger(logger_name, verbose)
        try:
            os.makedirs(os.path.join(in_file, 'tmp'))
        except FileExistsError:
            pass

        self.logger.info('Start extracting health info from export.xml.')

        health_file = os.path.join(in_file, 'export.xml')
        with open(health_file) as ifile:
            self.logger.info(f"Read Apple Health data from {in_file}...")
            self.data = self.get_data(ifile, from_date)
            self.gpx_files = self.get_gpx_files(from_date)
            self.info = self.get_info()
            self.activities = self.create_dataframe('ActivitySummary', nprocs)
            self.workouts = self.create_dataframe('Workout', nprocs)
            self.records = self.create_dataframe('Record', nprocs)

        self.logger.info('Start extracting workout routes.')
        self.routes = self.create_routes_dataframe()

        if verbose:
            self.report_stats()

    def get_file_date(self, filename: str) -> datetime:
        """Find the date that is in the filename of the workout routes file.

        Args:
            filename: the workout routes filename
        Returns:
            date: the date of the workout routes file created
        """

        try:
            date = re.search(r'(\d{4}-\d{2}-\d{2})', filename).group(1)

        except AttributeError:
            self.logger.info('No date found in filename {filename}.')
            date = '2099-01-01'

        return parse(date)

    def filter_nodes(
            self,
            node: ElementTree.Element,
            from_date: datetime) -> Union[ElementTree.Element, None]:
        """Return node if it is created after from date, else return None

        Args:
            node: the element node
            from_date: return node if node is created after this date
        """

        filtered = None

        if node.tag in ['Record', 'Workout', 'WorkoutRoute']:
            if parse(node.attrib['creationDate']) >= from_date:
                filtered = node

        elif node.tag == 'ActivitySummary':
            from_date_local = from_date.replace(tzinfo=None)

            if parse(node.attrib['dateComponents']) >= from_date_local:
                filtered = node

        elif node.tag == 'FileReference':

            file_date = self.get_file_date(node.attrib['path'])
            from_date_local = from_date.replace(tzinfo=None)

            if file_date >= from_date_local:
                filtered = node

        else:
            filtered = node

        return filtered

    def get_gpx_files(self, from_date: datetime) -> list:
        """Get the routes (.gpx) data from apple health zip file, then
        filter by from_date.

        Args:
            from_date: to return on gpx files after this date

        Returns:
            gpx_files: the .gpx files filtered by date
        """

        filepath = os.path.join(self.export_path, 'workout-routes')
        gpx_files = [f for f in os.listdir(filepath) if f.endswith('.gpx')]
        filtered_gpx_files = []

        if from_date:
            from_date_local = from_date.replace(tzinfo=None)

            for gpx_file in gpx_files:
                file_date = self.get_file_date(gpx_file)

                if file_date >= from_date_local:
                    filtered_gpx_files.append(gpx_file)

            return filtered_gpx_files
        return gpx_files

    def get_data(self, ifile: str, from_date: datetime = None) -> list:
        """Get data from xml, then filter with from_date and the node tags
        specified in activity_format.json file.

        Args:
            ifile: the directory path where apple health data is stored.
            from_date: to only parase health data after this date

        Returns:
            filtere_nodes: list of nodes filtere by date and node tag
        """

        data = ElementTree.parse(ifile)
        nodes = []
        filtered_nodes = []

        for tag in list(NODES.keys()):
            nodes += data.findall(tag)

        if from_date:
            self.logger.info(f'Filter data to from date: {from_date}')
            jhb = timezone('Africa/Johannesburg')
            from_date = jhb.localize(from_date)

            for node in tqdm(nodes, total=len(nodes)):
                filtered_node = self.filter_nodes(node, from_date)
                if filtered_node is not None:
                    filtered_nodes.append(filtered_node)

        else:
            filtered_nodes = nodes

        return filtered_nodes

    def get_nodes(self, tags: Union[str, list]) -> list:
        """Get nodes from element tree based on node tag"""

        if isinstance(tags, str):
            tags = [tags]

        nodes = [node.attrib for node in self.data if node.tag in tags]

        return nodes

    def get_logger(self, logger_name: str, verbose: bool = True):
        """Get the logger by the logger name

        Args:
            logger_name: if not provided, will be the script name that calls
                the object.
            verbose: the logging level sets on info if verbose, else warning
        """

        if logger_name is None:
            frame = currentframe().f_back.f_back
            while frame.f_code.co_filename.startswith("<frozen"):
                frame = frame.f_back
            logger_name = os.path.splitext(
                os.path.basename(frame.f_code.co_filename)
                )[0]

        if verbose:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.WARNING)

        logger = logging.getLogger(logger_name)

        return logger

    def get_info(self) -> dict:
        """Get the metadata of the exported data, using the node tag Me and
        ExportDate

        Returns:
            cleaned: cleaned metadata
        """

        attributes = self.get_nodes('Me')[0]
        cleaned = {
            'export_date': self.get_export_date(
                self.get_nodes('ExportDate')[0])
            }

        for key, val in attributes.items():
            key = key.replace('HKCharacteristicTypeIdentifier', '')
            val = val.replace(key, '').replace('HK', '')
            cleaned[key] = val

        return cleaned

    def get_export_date(self, export_date: str) -> datetime:
        """Parse the export date string to obtain a datetime object

        Returns:
            export_date: the apple health data export date
        """

        try:
            export_date = parse(export_date["value"])
        except AttributeError:
            self.logger.warning("Export date not available.")
            export_date = None

        return export_date

    def report_stats(self):
        """Report the number of records extracted from the apple health data,
        and raise warning if extraction is incomplete."""

        used_tags = [
            'Record', 'Workout', 'ActivitySummary', 'Me', 'ExportDate'
        ]

        n_nodes = len(
            [node for node in list(self.data)
             if node.tag in used_tags]
        )

        date = datetime.strftime(
            self.info['export_date'],
            '%Y-%m-%d %H:%M:%S'
        )

        self.logger.info(
            f"Apple Health data exported on {date} has {n_nodes} records."
        )

        len_w = len(self.workouts)
        len_r = len(self.records)
        len_a = len(self.activities)
        len_routes = len(self.gpx_files)
        len_total = len_w + len_r + len_a

        self.logger.info(f'Routes has {len_routes} records.')
        self.logger.info(f'Records has {len_r} records.')
        self.logger.info(f'Workouts has {len_w} records.')
        self.logger.info(f'ActivitySummary has {len_a} records.')

        if len_total + 2 == n_nodes:
            self.logger.info('Extraction completed.')
        else:
            self.logger.warning(
                f'There are {n_nodes-2-len_total} number of records '
                'not extracted properly. Please investigate.'
            )

    def create_dataframe(self, node_tag: str, nprocs: int) -> pd.DataFrame:
        """Create a pandas dataframe based on the node_tag

        Args:
            node_tag: the node, such as Workout, Record, ActivitySummary
            nprocs: the number of processes to use, default to 4

        Returns:
            df: a pandas dataframe summarizing the apple health
                data, depending on the node tag.
        """

        def worker(node_tag, node_chunks, export_name):
            cleaned_vals = []
            for node in tqdm(node_chunks, total=len(node_chunks)):
                formatter = AppleHealthFormatter(node_tag, node)
                cleaned_vals.append(formatter.values)
            pd.DataFrame(cleaned_vals).to_pickle(export_name)

        procs = []
        names = []

        nodes = self.get_nodes(node_tag)
        chunksize = int(math.ceil(len(nodes) / float(nprocs)))

        for i in range(nprocs):
            export_name = os.path.join(
                self.export_path, 'tmp', f'{node_tag}{i}.pkl')
            names.append(export_name)

            proc = Process(
                target=worker,
                args=(
                    node_tag,
                    nodes[chunksize*i: chunksize*(i+1)],
                    export_name)
            )
            procs.append(proc)
            proc.start()

        for proc in procs:
            proc.join()

        df = pd.DataFrame()

        for name in names:
            tmp = pd.read_pickle(name)
            df = pd.concat([df, tmp])
            os.remove(name)

        date_col = underscore(NODES[node_tag]['formats']['date'][0])
        df = df.sort_values(by=date_col).reset_index(drop=True)

        return df

    def create_routes_dataframe(self) -> pd.DataFrame:
        """Create workout routes dataframe with the gpx data.

        Returns:
            df: a pandas dataframe summarizing the workout routes, including
                latitude, longitude, elevation and time of the route logged.
        """

        def create_routes_base_df():

            file_ref = pd.DataFrame(self.get_nodes('FileReference'))
            route = pd.DataFrame(self.get_nodes('WorkoutRoute'))

            return file_ref.merge(route, left_index=True, right_index=True)

        base_df = create_routes_base_df()

        df = pd.DataFrame()
        filepath = os.path.join(self.export_path, 'workout-routes')

        for fname in tqdm(self.gpx_files, total=len(self.gpx_files)):

            gpx = gpxpy.parse(open(os.path.join(filepath, fname), 'r'))

            tmp = pd.DataFrame([{
                'filename': os.path.join('/workout-routes', fname),
                'latitude': point.latitude,
                'lonitude': point.longitude,
                'elevation': point.elevation,
                'time': point.time
            } for point in gpx.tracks[0].segments[0].points])

            df = pd.concat([df, tmp])

        if len(base_df) > 0:
            df = base_df.merge(df, left_on='path', right_on='filename')
        else:
            self.logger.warning(
                'There is no WorkoutRoute available in health data.'
            )

        return df
