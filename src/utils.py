import folium
from folium import PolyLine
import pandas as pd
from branca.colormap import LinearColormap
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

def draw_stations(data_path, map):
    """
    Draw stations on map
    :param data_path: path to data
    :param map: map
    :return: map
    """
    data =  pd.read_excel(data_path)
    for i, row in data.iterrows():
        map = draw_station(row["Latitude"], row["Longitude"], row["Stations"], map)
    return map

def draw_station(station_lat, station_lng, name, map):
    """
    Draw station on map
    :param station: station (dict)
    :param map: map
    :return: map
    """
    folium.Circle(
        location=[station_lat, station_lng],
        radius=250,
        color='gray',
        fill=True,
        fill_color='gray',
        fill_opacity=1,
        tooltip="Station: " + name,
        popup="Station: " + name,
    ).add_to(map)

    return map

def draw_poly_with_color(poly, CO2m, map, CO2m_max, CO2m_min, weight=5, CO2_no_m=False):
    """
    Draw polygon with color
    :param poly: polyline (list of coordinates)
    :param CO2m: CO2m (list of CO2/m between each coordinate)
    :return: map
    """
    if CO2_no_m:
        polyline = PolyLine(locations=poly,
                            weight=weight,
                            tooltip="can add edge info",
                            color="orange")
        polyline.add_to(map)
        return map

    polyline = PolyLine(locations=poly,
                        weight=weight,
                        tooltip=str(CO2m)+"t_CO2/km",
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

def add_poly_to_solution(polyline_long, solution: list):
    """
    Add polyline to solution
    :return:
    [] ASTUCE: les polyline dans solution ne se superposent pas
    """
    if len(solution) == 0:
        return [polyline_long]

    list_of_sub_candidates = [polyline_long]
    while len(list_of_sub_candidates) > 0:
        counter_potential_polyline = 0
        match = False
        polyline = list_of_sub_candidates.pop(0)
        while counter_potential_polyline < len(solution) and match == False:
            potential_polyline = solution[counter_potential_polyline]
            counter_potential_polyline += 1
            match, segments = solve_poly(polyline, potential_polyline)
            if match:
                solution.remove(potential_polyline)
                if segments[0][3] != -1:
                    list_of_sub_candidates.append(segments[0])
                if segments[1][3] != -1:
                    # print("len common path", len(segments[1][2]))
                    solution.append(segments[1])
                if segments[2][3] != -1:
                    list_of_sub_candidates.append(segments[2])
                if segments[3][3] != -1:
                    solution.append(segments[3])
                if segments[4][3] != -1:
                    solution.append(segments[4])
                counter_potential_polyline = len(solution)+1
        if not match:
            solution.append(polyline)
    return solution

def solve_multi_poly(polylines, output_path):
    """
    Solve multi polylines
    :param polylines: list of polylines with format [(northeast, southwest, [list of points], CO2m), ...]
     """
    final_poly = [] #not final till the end
    initial_length = len(polylines)

    while len(polylines) > 0:
        if len(polylines)%10 == 0:
            print("n_poly = ",len(polylines), "len solution", len(final_poly))
        polyline = polylines.pop(0) # remove first polyline
        final_poly = add_poly_to_solution(polyline, final_poly)

        if len(polylines) == 7000 or len(polylines) == 6000 or len(polylines) == 5000 or len(polylines) == 4000 or len(polylines) == 2000:
            print("saving")
            with open(output_path+"_step_"+str(len(polylines))+".csv", "w") as f:
                f.write("northeast;southwest;points;CO2_gr_m;distance\n")
                for i, pol in enumerate(final_poly):
                    for j, to_write in enumerate(pol):
                        f.write(str(to_write))
                        if j < 4:
                            f.write(";")
                    f.write("\n")
    return final_poly

def solve_poly(polyline, potential_polyline):
    """
    Solve polyline
    :param polyline:
    :param potential_polyline:
    :return: polyline, new_segments[]
    """
    match = False
    if chance_of_crossing(polyline, potential_polyline):
        new_segments = []
        poly_points = polyline[2]
        potential_poly_points = potential_polyline[2]
        point_A_found = False
        point_B_found = False
        for point_A_poly_index, point_A in enumerate(poly_points): #Searching one way
            for point_A_potential_index, potential_point_A in enumerate(potential_poly_points):
                if same_location(point_A, potential_point_A) and not point_A_found:
                    point_A_found = True
                    for k, point_B in enumerate(reversed(poly_points)):#Searching the other way
                        for l, potential_point_B in enumerate(reversed(potential_poly_points)):
                            if same_location(point_B, potential_point_B) and not point_B_found:
                                point_B_poly_index = len(poly_points) - k - 1
                                point_B_potential_index = len(potential_poly_points) - l - 1
                                point_B_found = True
                                segments = make_segments(polyline[2], potential_polyline[2], point_A_poly_index, point_A_potential_index, point_B_poly_index, point_B_potential_index, polyline[3], potential_polyline[3])
                                break
        if point_B_found and point_A_found: # if common segment found
            if len(segments) == 5 and len(segments[1][0])>2:#Real matching and a real segment is shared
                match = True
                for new_segment in segments:
                    #check if new_segment[0] is of type None
                    if len(new_segment[0]) > 2: # if more than a single point
                        new_segments.append([*get_northeast_southwest(new_segment[0]), new_segment[0], new_segment[1]])
                    else:
                        new_segments.append([(0,0), (0,0), [], -1])
                return match, new_segments
        elif point_A_found != point_B_found:
            print("Error only one common point found, point_A_found = ", point_A_found, " point_B_found = ", point_B_found)
        else: # no common segment found
            return match, polyline
    return match, polyline

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
    reverse_index_poly = False
    reverse_index_potential = False

    if point_A_poly_index == point_B_poly_index or point_A_potential_index == point_B_potential_index:
        return [polyline, CO2_poly] # just crossing no common segment
    else: #make ---A---B--->
        if point_A_poly_index > point_B_poly_index:
            reverse_index_poly = True
            point_A_poly_index, point_B_poly_index = point_B_poly_index, point_A_poly_index
        if point_A_potential_index > point_B_potential_index:
            reverse_index_potential = True
            point_A_potential_index, point_B_potential_index = point_B_potential_index, point_A_potential_index

        seg0, seg2, seg2, seg3, seg4 = [[0], -1], [[0], -1], [[0], -1], [[0], -1], [[0], -1]
        if (point_B_poly_index-point_A_poly_index > point_B_potential_index-point_A_potential_index): #Common is polyline
            if point_A_poly_index > 0:
                point_A_poly_index -= 1
            if point_A_poly_index < 10:
                point_A_poly_index = 0

            if point_B_poly_index < len(polyline)-2:
                point_B_poly_index += 1
            if point_B_poly_index > len(polyline)-10:
                point_B_poly_index = len(polyline)-1

            point_A = polyline[point_A_poly_index]
            point_B = polyline[point_B_poly_index]

            seg0 = [polyline[:point_A_poly_index], CO2_poly]
            seg1 = [polyline[point_A_poly_index:point_B_poly_index], CO2_poly+CO2_potential]
            seg2 = [polyline[point_B_poly_index:], CO2_poly]

            if point_A_potential_index > 0:
                point_A_potential_index -= 1
            if point_A_potential_index < 10:
                point_A_potential_index = 0
            if point_B_potential_index < len(potential_polyline)-2:
                point_B_potential_index += 1
            if point_B_potential_index > len(potential_polyline)-10:
                point_B_potential_index = len(potential_polyline)-1

            if reverse_index_potential != reverse_index_poly:
                point_A, point_B = point_B, point_A

            seg3_points = potential_polyline[:point_A_potential_index]
            if not isinstance(seg3_points, list):
                seg3_points = [seg3_points]
            seg3_points.append(point_A)

            seg4_points = potential_polyline[point_B_potential_index]
            if not isinstance(seg4_points, list):
                seg4_points = [seg4_points]
            seg4_points.append(point_B)

            seg3 = [seg3_points, CO2_potential]
            seg4 = [seg4_points, CO2_potential]
        else: #Common is potential
            if point_A_potential_index > 0:
                point_A_potential_index -= 1
            if point_A_potential_index < 10:
                point_A_potential_index = 0
            if point_B_potential_index < len(potential_polyline)-2:
                point_B_potential_index += 1
            if point_B_potential_index > len(potential_polyline)-10:
                point_B_potential_index = len(potential_polyline)-1

            point_A = potential_polyline[point_A_potential_index]
            point_B = potential_polyline[point_B_potential_index]

            seg1 = [potential_polyline[point_A_potential_index:point_B_potential_index], CO2_poly+CO2_potential]
            seg3 = [potential_polyline[:point_A_potential_index], CO2_potential]
            seg4 = [potential_polyline[point_B_potential_index:], CO2_potential]

            if point_A_poly_index > 0:
                point_A_poly_index -= 1
            if point_A_poly_index < 10:
                point_A_poly_index = 0

            if point_B_poly_index < len(polyline)-2:
                point_B_poly_index += 1
            if point_B_poly_index > len(polyline)-10:
                point_B_poly_index = len(polyline)-1


            if reverse_index_potential != reverse_index_poly:
                point_A, point_B = point_B, point_A

            seg0_points = polyline[:point_A_poly_index]
            if not isinstance(seg0_points, list):
                seg0_points = [seg0_points]
            seg0_points.append(point_A)

            seg2_points = polyline[point_B_poly_index]
            if not isinstance(seg2_points, list):
                seg2_points = [seg2_points]
            seg2_points.append(point_B)

            seg0 = [seg0_points, CO2_poly]
            seg2 = [seg2_points, CO2_poly]
    return [seg0, seg1, seg2, seg3, seg4]

def same_location_point(point, potential_point, error):#Approx 2km
    """"
    Check if two points are the same
    :param point:
    :param potential_point:
    :return: boolean
    """
    # print(point, potential_point)
    point_A = (point[0], point[1])
    point_B = (potential_point[0], potential_point[1])
    if distance_2coord(point_A, point_B) < error:
        return True
    return False
def same_location(point, potential_point, error):#Approx 2km
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


def solve_multi_point(polylines, output_path):
    """
    Solve multi polylines
    :param polylines: list of polylines with format [[lat; long; val], ...]
     """
    final_points = [] #not final till the end
    initial_length = len(polylines)

    while len(polylines) > 0:
        polyline = polylines.pop(0) # remove first polyline
        final_points = add_poly_to_point_solution(polyline, final_points, error=0.015)

        if len(polylines) % 100 == 0:
            print("n_poly = ", len(polylines), "len solution", len(final_points))
        if len(polylines)%1000 ==0:
            print("saving")
            with open(output_path+"_step_"+str(len(polylines))+".csv", "w") as f:
                f.write("lat;long;CO2_gr_m;\n")
                for i, pol in enumerate(final_points):
                    for j, to_write in enumerate(pol):
                        f.write(str(to_write))
                        if j < 4:
                            f.write(";")
                    f.write("\n")
    return final_points

def add_poly_to_point_solution(polyline, solution: list, error):
    """
    PER POLYLINE
    Add polyline to solution Index(['points', 'CO2_gr', 'distance', 'CO2_gr_m'], dtype='object')
    :return:
    [] ASTUCE: les points dans solution ne se déplacent pas
    """
    if len(solution) == 0:
        for point in polyline[0]:
            solution.append([point[0], point[1], polyline[3]])
        return remove_too_close_point(solution, error=error)

    list_of_candidates = [[point[0], point[1], polyline[3]] for point in polyline[0]]
    point_to_update = []
    point_to_add_list = []
    while len(list_of_candidates) > 0:
        match = False
        point_to_add = list_of_candidates.pop(0)
        for index, existing_point in enumerate(solution):
            if same_location_point(existing_point, point_to_add, error=error): #TODO remove +5
                point_to_update.append(index)
                match = True
        if not match:
            point_to_add_list.append(point_to_add)

    return update_solution(point_to_update, point_to_add_list, solution, polyline[3], error=error)

def update_solution(point_to_update, point_to_add, solution, new_emission, error):
    """
    Update solution
    :param point_to_udate:
    :param point_to_add:
    :param solution:
    :return:
    """
    # make point_to_update value unique
    point_to_update = set(point_to_update)
    # print("point_to_update", len(point_to_update))
    # print("point_to_add", len(point_to_add))
    for index in point_to_update:
        solution[index][2] += new_emission
    point_to_add = remove_too_close_point(point_to_add, error=error)
    for point_to_add in point_to_add:
        solution.append(point_to_add)
    return solution

def remove_too_close_point(point_to_add, error):
    """
    Remove too close point
    :param point_to_add:
    :param error:
    :return:
    """
    for i, point in enumerate(point_to_add):
        for j, point2 in enumerate(point_to_add):
            if i != j:
                if same_location_point(point, point2, error):
                    point_to_add.remove(point2)
    return point_to_add



def draw_point_with_color(lat, long, CO2m, map, CO2m_max, CO2m_min, weight=5, CO2_no_m=False, radius=500, color1="", color2=""):
    """
    Draw point with color
    :param poly: polyline
    :param CO2m: CO2m (list of CO2/m between each coordinate)
    :return: map
    """
    # print CO2m
    if CO2_no_m:
        return map

    color = interpolate_color((CO2m-CO2m_min)/(CO2m_max-CO2m_min), color1=color1, color2=color2)

    folium.Circle(
        location=[lat, long],
        radius=radius,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        tooltip=str(CO2m)+"t_CO2/km",
    ).add_to(map)
    return map