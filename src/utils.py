import folium
import pandas as pd

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