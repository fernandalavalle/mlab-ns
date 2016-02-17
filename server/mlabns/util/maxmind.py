from google.appengine.ext import db

from mlabns.db import model
from mlabns.third_party import ipaddr
from mlabns.util import constants

import logging
import os
import socket
import string
import sys

sys.path.insert(1, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../third_party/pygeoip')))
import pygeoip


class GeoRecord:

    def __init__(self, city=None, country=None, latitude=None, longitude=None):
        self.city = city
        self.country = country
        self.latitude = latitude
        self.longitude = longitude

    def __eq__(self, other):
        return ((self.city == other.city) and
                (self.country == other.country) and
                (self.latitude == other.latitude) and
                (self.longitude == other.longitude))

    def __ne__(self, other):
        return not self.__eq__(other)


def get_ip_geolocation(ip_address):
    """Returns the geolocation data associated with an IP address from MaxMind.

    Args:
        ip_address: A string describing an IP address (v4 or v6).

    Returns:
        A populated GeoRecord if matching geolocation data is found for the
        IP address. Otherwise, an empty GeoRecord.
    """

    try:
        # Code relies on modules for input validation, which throws one of two
        # Exceptions for invalid input:
        # 1.) socket.error: Generated by pygeoip in parsing addresses from test
        #     to binary form while searching the MaxMind database; and,
        # 2.) TypeError: Passed a non-string IP address, such as None.
        geo_city_block = pygeoip.GeoIP(
            constants.GEOLOCATION_MAXMIND_CITY_FILE,
            flags=pygeoip.const.STANDARD).record_by_addr(ip_address)
    except (socket.error, TypeError) as e:
        logging.error('MaxMind Geolocation failed on query (%s) with error: %s',
                      ip_address, e)
        return GeoRecord()

    if not geo_city_block:
        logging.error('IP %s not found in the MaxMind database.', ip_address)
        return GeoRecord()

    return GeoRecord(city=geo_city_block['city'],
                     country=geo_city_block['country_code'],
                     latitude=geo_city_block['latitude'],
                     longitude=geo_city_block['longitude'])


def get_country_geolocation(country, country_table=model.CountryCode):
    """Returns the geolocation data associated with a country code.

    Args:
        country: A string describing a two alphanumeric country code.

    Returns:
        A GeoRecord containing the geolocation data if found,
        otherwise an empty GeoRecord.
    """
    geo_record = GeoRecord()

    logging.info('Retrieving geolocation info for country %s.', country)
    location = country_table.get_by_key_name(country)
    if location is not None:
        geo_record.city = constants.UNKNOWN_CITY
        geo_record.country = location.alpha2_code
        geo_record.latitude = location.latitude
        geo_record.longitude = location.longitude
    return geo_record


def get_city_geolocation(city, country, city_table=model.MaxmindCityLocation):
    """Returns the geolocation data associated with a city and country code.

    Args:
        city: A string specifying the name of the city.
        country: A string describing a two alphanumeric country code.

    Returns:
        A GeoRecord containing the geolocation data if found,
        otherwise an empty GeoRecord.
    """
    geo_record = GeoRecord()

    logging.info('Retrieving geolocation info for country %s, city %s.', city,
                 country)
    location = city_table.gql('WHERE city = :city AND country = :country',
                              city=city,
                              country=country).get()
    if location is None:
        logging.error('%s, %s not found in the database.', city, country)
        return geo_record

    geo_record.city = location.city
    geo_record.country = location.country
    geo_record.latitude = location.latitude
    geo_record.longitude = location.longitude
    return geo_record
