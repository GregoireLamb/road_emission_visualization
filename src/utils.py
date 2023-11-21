from folium import Map, PolyLine
import pandas as pd
import json

def load_data(path):
    """
    Load data from csv
    :return: dataframe
    """
    data = pd.read_excel(path)
    return data


def distance_2coord(coord_A, coor_B):
    """
    Calculate distance between two coordinates
    :param coord_A: tuple of coordinates
    :param coor_B: tuple of coordinates
    :return: distance
    """
    return ((coord_A[0] - coor_B[0]) ** 2 + (coord_A[1] - coor_B[1]) ** 2) ** 0.5

def draw_poly_with_color(poly, CO2m, map, CO2m_max, CO2m_min, weight=8):
    """
    Draw polygon with color
    :param poly: polyline (list of coordinates)
    :param CO2m: CO2m (list of CO2/m between each coordinate)
    :return: map
    """
    polyline = PolyLine(locations=poly,
                        weight=weight,
                        tooltip=CO2m,
                        color=interpolate_color((CO2m-CO2m_min)/(CO2m_max-CO2m_min)))
    polyline.add_to(map)
    return map


def interpolate_color(ratio, color1="FFFF00", color2="CE0000"):
    # Conversion hex vers RGB
    r1, g1, b1 = int(color1[0:2], 16), int(color1[2:4], 16), int(color1[4:6], 16)
    r2, g2, b2 = int(color2[0:2], 16), int(color2[2:4], 16), int(color2[4:6], 16)

    # Interpolation linéaire pour chaque composante
    r = int(r1 + (r2 - r1) * ratio)
    g = int(g1 + (g2 - g1) * ratio)
    b = int(b1 + (b2 - b1) * ratio)

    # Conversion RGB vers hex
    interpolated_color = "#{:02X}{:02X}{:02X}".format(r, g, b)

    return interpolated_color

def solve_multi_poly(polylines, output_path):
    """
    Solve multi polylines
    :param polylines: list of polylines with format [(northeast, southwest, [list of points], CO2m), ...]
     """
    final_poly = [] #safe polylines
    with open(output_path, "w") as f:
        f.write("northeast;southwest;points;CO2_gr_m;distance\n")

        while len(polylines) > 0:
            print("n_poly = ",len(polylines))
            polyline = polylines.pop(0) # remove first polyline
            for potential_polyline in polylines:
                polyline, new_segments = solve_poly(polyline, potential_polyline)
                if len(new_segments) > 0:
                    polylines.remove(potential_polyline)
                for new in new_segments:
                    polylines.append(new)
                if len(polyline[2]) <= 0:
                    break
            if len(polyline[2]) >= 2:
                final_poly.append(polyline)
                # write to file
                for i, to_write in enumerate(polyline):
                    f.write(str(to_write))
                    if i < len(polyline) - 1:
                        f.write(";")
                f.write("\n")
                f.flush()
    return final_poly

def solve_poly(polyline, potential_polyline):
    """
    Solve polyline
    :param polyline:
    :param potential_polyline:
    :return: polyline, new_segments[]
    """
    if chance_of_crossing(polyline, potential_polyline):
        new_segments = []
        poly_points = polyline[2]
        potential_poly_points = potential_polyline[2]
        point_A_found = False
        point_B_found = False
        for i, point_A in enumerate(poly_points): #Searching one way
            for j, potential_point_A in enumerate(potential_poly_points):
                if same_location(point_A, potential_point_A) and not point_A_found:
                    point_A_poly_index = i
                    point_A_potential_index = j
                    point_A_found = True
                    for k, point_B in enumerate(reversed(poly_points)):#Searching the other way
                        for l, potential_point_B in enumerate(reversed(potential_poly_points)):
                            if same_location(point_B, potential_point_B) and not point_B_found:
                                point_B_poly_index = len(poly_points) - k - 1
                                point_B_potential_index = len(potential_poly_points) - l - 1
                                point_B_found = True
                                pol, new = make_segments(polyline[2], potential_polyline[2], point_A_poly_index, point_A_potential_index, point_B_poly_index, point_B_potential_index, polyline[3], potential_polyline[3])
                                break
        if point_B_found and point_A_found: # if common segment found
            polyline = [*get_northeast_southwest(pol[0]), pol[0], pol[1]]
            for new_point_segment in new:
                if len(new_point_segment[0]) > 1: # if more than a single segment
                    new_segments.append([*get_northeast_southwest(new_point_segment[0]), new_point_segment[0], new_point_segment[1]])
            return polyline, new_segments
        elif point_A_found != point_B_found:
            print("Error only one common point found, point_A_found = ", point_A_found, " point_B_found = ", point_B_found)
        else: # no common segment found
            return polyline, []
    return polyline, []

def get_northeast_southwest(poly_points):
    """
    Return northeast and southwest from poly_points
    :param poly_points:
    :return:
    """
    if len(poly_points) == 0:
        return [(0,0), (0,0)]
    northeast_lat = max([x[0] for x in poly_points])
    northeast_long = max([x[1] for x in poly_points])
    southwest_lat = min([x[0] for x in poly_points])
    southwest_long = min([x[1] for x in poly_points])
    return [(northeast_lat, northeast_long), (southwest_lat, southwest_long)]

def make_segments(polyline, potential_polyline, point_A_poly_index, point_A_potential_index, point_B_poly_index, point_B_potential_index, CO2_poly, CO2_potential):
    """
    Make segments
    :param polyline:
    :param potential_polyline:
    :param point_A_poly:
    :param point_B_poly:
    :param point_A_potential:
    :param point_B_potential:
    :return:
    """
    #TODO assert index order
    if point_A_poly_index == point_B_poly_index or point_A_potential_index == point_B_potential_index:
        return [polyline, CO2_poly], [] # just crossing no common segment
    else:
        # Up tp 4 segments
        # polyline = segment from beginning to point_A_poly
        poly_points = [polyline[point_A_poly_index:point_B_poly_index+1], CO2_poly+CO2_potential]
        new_point_segments = [[polyline[0:point_A_poly_index+1], CO2_poly],
                               [polyline[point_B_poly_index:],CO2_poly],
                               [potential_polyline[0:point_A_potential_index+1], CO2_potential],
                               [potential_polyline[point_B_potential_index:], CO2_potential]]
        return poly_points, new_point_segments

def same_location(point, potential_point, error=0.001):#Approx 250m
    """"
    Check if two points are the same
    :param point:
    :param potential_point:
    :return: boolean
    """
    if distance_2coord(point, potential_point) < error:
        return True
    return False


def chance_of_crossing(polyline, potential_polyline):
    """
    Check if there is a change of crossing
    :param polyline:
    :param potential_polyline:
    :return: boolean
    """
    poly_northeast_lat, poly_northeast_long = polyline[0]
    poly_southwest_lat, poly_southwest_long = polyline[1]
    potential_northeast_lat, potential_northeast_long = potential_polyline[0]
    potential_southwest_lat, potential_southwest_long = potential_polyline[1]

    if (poly_northeast_long < potential_southwest_long or 
            potential_northeast_long < poly_southwest_long or 
            poly_northeast_lat < potential_southwest_lat or 
            potential_northeast_lat < poly_southwest_lat):
        return False
    return True