#!/usr/bin/env python

from shapely.geometry.polygon import Polygon, LineString
from shapely.geometry import Point
from pgairspace.utils import pp # noqa
from pgairspace.utils import read_json
from pgairspace.hun_aip import process_chapters, process_airports
from pgairspace.hun_geom import latlon_str_to_point, process_circle
from pgairspace.geom import plot_line

process_chapters()
process_airports()



from pgairspace.hun_aip import process_chapter


data = process_chapter('5.6')




def process_geometry(data):
    geom_raw = data['geom_raw']
    geom_split = [p.strip() for p in geom_raw.split('-')]

    points = list()
    for s in geom_split:
        if 'along border' in s:
            first, _ = s.split('along border')
            points.append(latlon_str_to_point(first))
            points.append('border')

        elif s.startswith('A circle'):
            assert len(geom_split) == 1
            data['geom'] = process_circle(s)
            return data

        else:
            points.append(latlon_str_to_point(s))

    assert points[0] == points[-1]

    return points

    data['geom'] = Polygon(points)
    return data



def process_border(points_with_border, border):
    new_points = list()
    for i, point in enumerate(points_with_border):
        # print i, point
        if point == 'border':
            assert i != 0 and i != len(points_with_border) - 1
            point_start = Point(points_with_border[i - 1])
            point_end = Point(points_with_border[i + 1])
            border_section = calculate_border_between_points(point_start, point_end, border)
            new_points.extend(list(border_section.coords))
        else:
            new_points.append(point)

    return new_points



def calculate_border_between_points(point_a, point_b, border):
    dists = [border.project(p) for p in [point_a, point_b]]
    dists_sorted = sorted(dists)
    points = [border.interpolate(d) for d in dists_sorted]

    segment_a, segment_bc = cut_line(points[0], border)
    segment_b, segment_c = cut_line(points[1], segment_bc)

    segment_round = LineString(list(segment_c.coords) + list(segment_a.coords))

    # selecting shorter segment
    if segment_b.length < segment_round.length:
        selected = segment_b
    else:
        selected = segment_round

    # swapping if opposite direction is required
    if dists != dists_sorted:
        selected = LineString(selected.coords[::-1])

    # returning segment without endpoints
    return LineString(selected.coords[1:-1])


def cut_line(cut_point, line, eps_mult=1e2):
    dist = line.project(cut_point)
    point = line.interpolate(dist)
    eps = line.distance(point) * eps_mult

    coords = list(line.coords)

    for i, p in enumerate(coords[:-1]):
        line_segment = LineString([coords[i], coords[i + 1]])
        line_segment_buffer = line_segment.buffer(eps, resolution=1)

        if line_segment_buffer.contains(point):
            start_segment = LineString(coords[:i + 1] + [point])
            end_segment = LineString([point] + coords[i + 1:])

            return start_segment, end_segment

    raise Exception('point not found in line, consider raising eps_mult')



from shapely.geometry import asShape

border_json = read_json('data/borders/hungary.json')
border = asShape(border_json['geometries'][0]).exterior
border = border.simplify(0.001)
border = LineString(border)



gs = [process_geometry(d) for d in data if 'border' in process_geometry(d)]

for g in gs:

    g_orig = [p for p in g if p != 'border']
    g_border = process_border(g, border)

    # plot_line(LineString(g_orig))
    plot_line(LineString(g_border))


# import geojson
# print geojson.dumps(LineString(g_border))
