#!/usr/bin/python
# coding: utf8

from __future__ import absolute_import
import subprocess
import click
import os
import requests
from click import BadOptionUsage
from PIL import Image

@click.command()
@click.option('--filename', default='temp', help='Output filename to SVG')
@click.option('--lat', type=click.FloatRange(-90, 90), help='latitude for the center point of the static map; number between  -90 and  90')
@click.option('--lng', type=click.FloatRange(-180, 180), help='longitude for the center point of the static map; number between  -180 and  180')
@click.option('--zoom', type=click.FloatRange(0, 22), help='zoom level; number between  0 and  22 . Fractional zoom levels will be rounded to two decimal places.')
@click.option('--width', type=click.IntRange(1, 1280), default=1280, help='width of the image in pixels')
@click.option('--height', type=click.IntRange(1, 1280), default=1280, help='height of the image in pixels')
@click.option('--style', default='mapbox://styles/addxy/cilvkyu6100129om1f5aw1kl7', help='mapbox://styles/{username}/{style_id}')
@click.option('--access_token', default='pk.eyJ1IjoiYWRkeHkiLCJhIjoiY2lsdmt5NjZwMDFsdXZka3NzaGVrZDZtdCJ9.ZUE-LebQgHaBduVwL68IoQ', help='Mapbox access token')
@click.option('--bearing', type=click.FLOAT, default=0, help='bearing; number between  0 and  360 . Defaults to  0 .')
@click.option('--pitch', type=click.FLOAT, default=0, help='pitch; number between  0 and  60 . Defaults to  0 .')
@click.option('--retina', is_flag=True, default=True, help='If  @2x is added to request a retina 2x image will be returned')
@click.option('--attribution', is_flag=True, default=False, help='boolean value controlling whether there is attribution on the image; defaults to  false')
@click.option('--logo', is_flag=True, default=False, help='boolean value controlling whether there is a Mapbox logo on the image; defaults to  false')
@click.option('--upload', is_flag=True, default=False)
@click.option('--delete', type=click.BOOL, default=True)

def cli(filename, **kwargs):
    print('Building: {}...'.format(filename))
    check_options(**kwargs)
    create_png(filename, **kwargs)
    create_svg(filename, **kwargs)
    upload_aws_s3(filename, **kwargs)

def get_mapbox_static(**kwargs):
    """ Connect to Mapbox Static API
    https://www.mapbox.com/api-documentation/#retrieve-a-static-map-from-a-style

    Input: HTTP API parameters
    Output: raw Image
    """
    username, style_id = parse_style(kwargs['style'])
    params = {
    'access_token': kwargs['access_token'],
    'logo': str(kwargs['logo']).lower(),
    'attribution': str(kwargs['attribution']).lower()
    }
    url = 'https://api.mapbox.com/styles/v1/{username}/{style_id}/static/{lng},{lat},{zoom},{bearing},{pitch}/{width}x{height}{retina}'
    url = url.format(
    username=username,
    style_id=style_id,
    lng=kwargs['lng'],
    lat=kwargs['lat'],
    zoom=kwargs['zoom'],
    bearing=kwargs['bearing'],
    pitch=kwargs['pitch'],
    width=kwargs['width'],
    height=kwargs['height'],
    retina=parse_retina(kwargs['retina'])
    )
    response = requests.get(url, params=params, stream=True)
    response.raw.decode_content = True
    return response.raw

def create_png(filename, **kwargs):
    """Create PNG
    Connects to Mapbox's Static API
    Output: PNG <filename>
    """
    mapbox_static = get_mapbox_static(**kwargs)
    image = Image.open(mapbox_static)
    image.save('{}.png'.format(filename))

def create_svg(filename, **kwargs):
    """Create SVG
    Input: PNG <filename>
    Output: SVG <filename>
    """
    # ImageMagick 6.8.9 - convert
    # Usage: convert [options ...] file [ [options ...] file ...] [options ...] file
    subprocess.call(['convert', '{}.png'.format(filename), '{}.pnm'.format(filename)])

    # potrace 1.12. Transforms bitmaps into vector graphics.
    # <filename>                 - an input file
    # -s, --svg                  - SVG backend (scalable vector graphics)
    # -o, --output <filename>    - write all output to this file
    subprocess.call(['potrace', '--svg', '--output', '{}.svg'.format(filename), '{}.pnm'.format(filename)])

    # Remove extra files that are not needed anymore
    if kwargs['delete']:
        os.remove('{}.png'.format(filename))
        os.remove('{}.pnm'.format(filename))

def upload_aws_s3(filename, **kwargs):
    """ Upload AWS S3 bucket """

    if kwargs['upload']:
        filename = '{}.svg'.format(filename)
        s3_bucket = 'kratelabs.com'
        s3_path = 's3://{}/{}'.format(s3_bucket, filename)
        command = ['aws', 's3', 'cp', filename , s3_path, '--acl', 'public-read-write']
        print(' '.join(command))
        output = subprocess.call(command)
        print('https://{}.s3.amazonaws.com/{}'.format(s3_bucket, kwargs['upload']))

def parse_retina(retina):
    if retina:
        return '@2x'
    return ''

def parse_style(style):
    """Parse Style
    Input: mapbox://styles/{username}/{style_id}
    Output: username, style_id
    """
    if 'mapbox://styles/' in style:
        style = style.split('mapbox://styles/', 1)[-1]
        username, style_id = style.split('/')
        return  username, style_id

def check_options(**kwargs):
    lat, lng, zoom = kwargs['lat'], kwargs['lng'], kwargs['zoom']

    if not lat and not lng:
        raise BadOptionUsage('lat', 'Missing latitude & longitude')
    if not lat:
        raise BadOptionUsage('lat', 'Missing latitude')
    if not lng:
        raise BadOptionUsage('lng', 'Missing longitude')
    if not zoom:
        raise BadOptionUsage('zoom', 'Missing zoom level')

if __name__ == '__main__':
    cli()