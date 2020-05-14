# pylint: disable=redefined-outer-name, missing-function-docstring
import json
from datetime import datetime
from collections import Counter
from xml.etree import ElementTree
from inflection import underscore

import pytest
from ipyhealth.parser import AppleHealthFormatter, AppleHealthParser

from . import templates


@pytest.fixture
def nodes_template():
    '''Returns the template data'''
    try:
        import importlib.resources as pkg_resources
    except ImportError:
        import importlib_resources as pkg_resources

    template = pkg_resources.read_text(templates, 'activity_format.json')
    nodes_template = json.loads(template)

    return nodes_template


@pytest.fixture
def health_data():
    '''Returns the example apple_health_data parser'''

    in_file = 'tests/data/apple_health_export/'
    health_data = AppleHealthParser(in_file=in_file)
    return health_data


@pytest.fixture
def workout_node():
    '''Returns an example of workout attributes'''

    in_file = 'tests/data/apple_health_export/export.xml'
    workout_node = ElementTree.parse(in_file)._root.find('Workout')
    return workout_node


@pytest.fixture
def record_node():
    '''Returns an example of workout attributes'''

    in_file = 'tests/data/apple_health_export/export.xml'
    record_node = ElementTree.parse(in_file)._root.find('Record')
    return record_node


@pytest.fixture
def formatter(workout_node):
    '''Returns an example formatter using the workout attrib'''
    formatter = AppleHealthFormatter('Workout', workout_node.attrib)
    return formatter


def test_get_data():

    d = datetime(2020, 4, 12)
    in_file = 'tests/data/apple_health_export/'
    health_data = AppleHealthParser(in_file=in_file, from_date=d)

    assert len(health_data.records) == 1456
    assert len(health_data.workouts) == 11
    assert len(health_data.activities) == 6
    assert len(health_data.routes) == 0


def test_get_nodes(health_data):
    nodes1 = health_data.get_nodes('Workout')
    nodes2 = health_data.get_nodes(['Workout', 'ActivitySummary'])
    assert len(nodes1) == 16
    assert len(nodes2) == 24


def test_get_export_data(health_data):

    assert health_data.info.get('export_date').date() == \
        datetime(2020, 4, 17).date()


def test_get_logger_with_name():

    in_file = 'tests/data/apple_health_export/'
    ahd = AppleHealthParser(in_file=in_file, logger_name='test')

    assert ahd.logger.name == 'test'


def test_get_logger_without_name(health_data):

    assert health_data.logger.name == 'test_parser'


def test_personal_info(health_data):

    assert health_data.info.get('DateOfBirth') == '1989-04-24'


def test_format_date(formatter, workout_node):

    name, val = formatter.format_date(
        ('creationDate', workout_node.attrib['creationDate'])
    )

    assert name == 'creation_date'
    assert val.date() == datetime(2020, 4, 6).date()


def test_format_type(formatter, workout_node, nodes_template):

    activity_dict = formatter.format_type(
        (nodes_template['Workout']['pattern'],
         workout_node.attrib['workoutActivityType'])
    )

    assert activity_dict['activity_type'] == 'Workout'
    assert activity_dict['activity'] == 'Yoga'


def test_format_string(formatter, workout_node):

    name, value = formatter.format_string(
        ('sourceName', workout_node.attrib['sourceName']))

    assert name == 'source_name'
    assert value == "User’s Apple Watch"


@pytest.mark.parametrize(
    "a_type, value, o_name, o_val",
    [
        ('sourceVersion', '6.1.3', 'source_version', '6.1.3'),
        ('unit', 'sec', 'unit', 'sec'),
        ('value', '500', 'value', '500')
    ]
)
def test_format_no_format(formatter, a_type, value, o_name, o_val):

    name, output = formatter.format_string(
        (a_type, value)
    )

    assert name == o_name
    assert output == o_val


def test_format_device(formatter, workout_node):

    device_dict = formatter.format_device(workout_node.attrib['device'])

    assert device_dict == {
        'device_hardware': 'Watch5',
        'device_hkdevice': '0x',
        'device_model': 'Watch',
        'device_manufacturer': 'Apple Inc.',
        'device_name': 'Apple Watch',
        'device_software': '6.1.3'
        }


@pytest.mark.parametrize(
    "a_type, value, unit, o_name, o_val",
    [
        ('duration', 600, 'sec', 'duration_min', 10.0),
        ('totalDistance', 2.5, 'km', 'distance_km', 2.5),
        ('totalEnergyBurned', 2500, 'cal', 'energy_burned_kcal', 2.5)
    ]
)
def test_format_standard(formatter, a_type, value, unit, o_name, o_val):

    name, val = formatter.format_standard((
        a_type,
        value,
        unit
    ))

    assert name == o_name
    assert val == o_val


@pytest.mark.parametrize(
    "a_type, value, unit",
    [
        ('totalDistance', 25000, 'cm'),
        ('a', 25000, 'random')
    ]
)
def test_standardize_unit_error(formatter, a_type, value, unit):

    with pytest.raises(NotImplementedError):
        _, _ = formatter.format_standard((
            a_type,
            value,
            unit
        ))


@pytest.mark.parametrize(
    "a_type, value, o_name, o_value",
    [
        ('activeEnergyBurned', '408.302', 'active_energy_burned', 408.302),
        ('appleStandHoursGoal', '12', 'apple_stand_hours_goal', 12)
    ]
)
def test_format_numerics(formatter, a_type, value, o_name, o_value):

    name, val = formatter.format_numerics((a_type, value))

    assert name == o_name
    assert val == o_value


def test_format_values(formatter, nodes_template):

    values = formatter.format_values()

    assert values['creation_date'].date() == datetime(2020, 4, 6).date()
    for atype in nodes_template['Workout']['formats']['date']:
        values.pop(underscore(atype))
    assert values == {
        'activity_type': 'Workout',
        'activity': 'Yoga',
        'source_name': 'User’s Apple Watch',
        'source_version': '6.1.3',
        'device_manufacturer': 'Apple Inc.',
        'device_hardware': 'Watch5',
        'device_hkdevice': '0x',
        'device_model': 'Watch',
        'device_software': '6.1.3',
        'device_name': 'Apple Watch',
        'duration_min': 55.46542123357455,
        'distance_km': 0.0,
        'energy_burned_kcal': 158.9423116574216
    }


def test_create_dataframe(health_data):

    assert len(health_data.workouts) == 16
    assert Counter(health_data.workouts.activity) ==\
           Counter({'Yoga': 8, 'MindAndBody': 1, 'CrossTraining': 7})
    assert len(health_data.records) == 1862
    assert Counter(health_data.records.activity).get('StepCount') == 37
    assert len(health_data.activities) == 8
    assert health_data.activities.loc[0, 'active_energy_burned'] == \
        408.302


def test_create_routes_dataframe(health_data):

    assert len(health_data.routes.time.dt.date.unique()) == 2
    assert len(health_data.routes) == 35008
