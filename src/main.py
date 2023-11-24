import ast
import datetime
import random as rnd
from datetime import datetime

from folium import plugins

from src.config import Config
from src.maps import Maps
from src.utils import *

"""
Hypothesis: 
    - Emission same along a distance (CO2/m = const)
    - Maps API provided same path between two points 
    - Roads are founded with google maps API ("driving" mode) for a departure on the 22-11-2023 at 10:00    
"""

def raw_to_smart_data(data_path1, data_path2, output_path="./data/smart_data.csv"):
    """
    Convert raw data to raw data + google usable point
    :param data:
    :return: file with format ["Versandbhf_neu:V";"Versandbhf_neu:V_lat";"Versandbhf_neu:V_long";"Empfang";"Empfang_lat";"Empfang_long";"CO2_emission(gr)";"CO2_emission(t)"]
    -> [gareA_lat; gareA_long; gareB_lat; gareB_long; CO2_gr...]

    !!! GPS.xlsx have been added a row manually -> Bruck a. d. Mur 	47,4105556	15,2686111
    Assumption Bruck a. d. Mur = Bruck a. d. Mur Fbf

    !!! data_raw.xlsx have been eddited -> remove space before and after Kufstein line 2243
    """
    GPS = pd.read_excel(data_path2)
    GPS = GPS.set_index("Stations")

    train_lines = pd.read_excel(data_path1, header=1)
    list_dict = []

    for i, row in train_lines.iterrows():
        try:
            new_row = {'station_A_lat': GPS.loc[row["Versandbhf_neu:V"], 'Latitude'],
                       'station_A_long': GPS.loc[row["Versandbhf_neu:V"], 'Longitude'],
                       'station_B_lat': GPS.loc[row["Empfang"], 'Latitude'],
                       'station_B_long': GPS.loc[row["Empfang"], 'Longitude'],
                       'CO2': row["CO2 emission (gr)"]}
            list_dict.append(new_row)
        except:
            print("Error with row: ", row, "at index: ", i)
    data = pd.DataFrame(list_dict)
    data.to_csv(output_path, sep=';', index=False)

    return output_path

def smart_to_points_data(data_path, map, departure_date, online=True, output_path="../data/poly_points_data.csv"):
    """
    Convert smart data to list of [[n_w_point, s_e_point, [points], CO2_gr]...]
    :param data:
    :return:
    -> [[n_w_point, s_e_point, [points], CO2_gr]...]
    """
    # load data with pandas as a csv file
    data = pd.read_csv(data_path, sep=";")

    #Write in a csv file at output_path
    with open(output_path, "w") as f:
        f.write("northeast;southwest;points;CO2_gr;distance\n")
        for i, row in data.iterrows():
            if i > 7730:
                if i % 10 == 0:
                    print("i=", i, "out of", len(data))
                station_A = str(row["station_A_lat"])+","+str(row["station_A_long"])
                station_B = str(row["station_B_lat"])+","+str(row["station_B_long"])
                CO2 = float(row["CO2"])
                if online:
                    distance, decoded_polyline, northeast, southwest = map.get_directions(station_A, station_B, departure_date, mode="driving")
                else:
                    #generate random values
                    decoded_polyline = [(rnd.random()*25, rnd.random()*25) for i in range(15)]
                    northeast = (rnd.random()*25, rnd.random()*25)
                    southwest = (rnd.random()*25, rnd.random()*25)
                    distance = rnd.random()*1000
                f.write(str(northeast)+";")
                f.write(str(southwest)+";")
                f.write(str(decoded_polyline)+";")
                f.write(str(CO2)+";")
                f.write(str(distance)+"\n")
                f.flush()
    return output_path

def format_data_for_all_path(data_path="../data/poly_points_data.csv", output_path="../data/alpath.csv"):
    """
    get path info out
    :param data: list of [(northeast, southwest, [list of points], CO2m), ...]
    :return: the reduced non overlappong same set (northeast, southwest, [list of points], CO2m)
    """
    df = pd.read_csv(data_path, sep=";")
    df['northeast'] = df['northeast'].apply(ast.literal_eval)
    df['northeast'] = df['northeast'].apply(lambda x: (x['lat'], x['lng']))
    df['southwest'] = df['southwest'].apply(ast.literal_eval)
    df['southwest'] = df['southwest'].apply(lambda x: (x['lat'], x['lng']))
    df['points'] = df['points'].apply(ast.literal_eval)
    pd.to_numeric(df['CO2_gr'], errors='coerce')
    pd.to_numeric(df['distance'], errors='coerce')
    df['CO2_gr_m'] = df.apply(lambda row: row['CO2_gr']/row['distance'] if row['distance'] != 0 else 0, axis=1)

    # transform data to list of [(northeast, southwest, [list of points], CO2m), ...]
    df = df.to_dict(orient='records')
    data=[]
    print("Data transformed ")
    for record in df:
        data.append(list(record.values()))

    with open(output_path, "w") as f:
        f.write("northeast;southwest;points;CO2_gr_m;distance\n")
        for i, pol in enumerate(data):
            for j, to_write in enumerate(pol):
                f.write(str(to_write))
                if j < 4:
                    f.write(";")
            f.write("\n")
    return 0

def points_to_smart_points(data_path="../data/poly_points_data.csv", output_path="../data/final_points.csv"):
    """
    Convert points data to list of acctual point to draw (with info)
    :param data: list of [(northeast, southwest, [list of points], CO2m), ...]
    :return: the reduced non overlappong same set (northeast, southwest, [list of points], CO2m)
    """
    df = pd.read_csv(data_path, sep=";")
    df.drop(columns=["northeast", "southwest"], inplace=True)
    df['points'] = df['points'].apply(ast.literal_eval)
    pd.to_numeric(df['CO2_gr'], errors='coerce')
    pd.to_numeric(df['distance'], errors='coerce')
    df['CO2_gr_m'] = df.apply(lambda row: row['CO2_gr']/row['distance'] if row['distance'] != 0 else 0, axis=1)

    # transform data to list of [(northeast, southwest, [list of points], CO2m), ...]
    df = df.to_dict(orient='records')
    data=[]
    for record in df:
        data.append(list(record.values()))
    print("Data transformed ")

    final_points = solve_multi_point(data, output_path=output_path[:-4])

    with open(output_path, "w") as f:
        f.write("lat;long;CO2_gr_m\n")
        for i, pt in enumerate(final_points):
            f.write(str(pt[0])+";"+str(pt[1])+";"+str(pt[2])+"\n")
    return 0

def draw_points(data_path, map, radius=500, scale=1, split=100, split2=15):
    df = pd.read_csv(data_path, sep=";")
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['long'] = pd.to_numeric(df['long'], errors='coerce')
    df["CO2_gr_m"] = (df['CO2_gr_m'] / 1e3).round(decimals=2)  # convert to t_CO2/km
    max_CO2m = df["CO2_gr_m"].max()
    min_CO2m = df["CO2_gr_m"].min()

    if scale == 1:
        if max_CO2m == min_CO2m:
            max_CO2m += 1

        for i, row in df.iterrows():
            map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=min_CO2m, CO2m_max=max_CO2m, radius = radius)

        map = draw_legend(min_val=min_CO2m, max_val= max_CO2m, my_map=map)

    elif scale ==2: #if scale ==2
        for i, row in df.iterrows():
            yellow, orange, red = "FFC000", "FF6600" , "990000" #, "F10F0F""F10F0F"
            if row["CO2_gr_m"] > split: # high CO2m
                map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=split, CO2m_max=max_CO2m, radius = radius, color1=orange, color2=red)
            else:
                map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=min_CO2m, CO2m_max=split, radius = radius, color1=yellow, color2=orange)#color1="FFFF00", color2="CE0000"

        map = draw_legend(min_val=min_CO2m, max_val= split, my_map=map, color1=yellow, color2=orange, second=True)
        map = draw_legend(min_val=split, max_val= max_CO2m, my_map=map, color1=orange, color2=red)
    else: #if scale ==3
        for i, row in df.iterrows():
            light, yellow, orange, red = "FFF59B", "FFD700", "FF6600" , "990000"
            if row["CO2_gr_m"] > split: # high CO2m
                map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=split, CO2m_max=max_CO2m, radius = radius, color1=orange, color2=red)
            elif row["CO2_gr_m"] > split2: # medium CO2m
                map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=split2, CO2m_max=split, radius = radius, color1=yellow, color2=orange)#color1="FFFF00", color2="CE0000"
            else: # low CO2m
                map = draw_point_with_color(lat=row["lat"], long=row["long"], CO2m=float(row["CO2_gr_m"]), map=map, CO2m_min=0, CO2m_max=split2, radius = radius, color1=light, color2=yellow)

        map = draw_legend(min_val=0, max_val=split2, my_map=map, color1=light, color2=yellow)
        map = draw_legend(min_val=split2, max_val=split, my_map=map, color1=yellow, color2=orange)
        map = draw_legend(min_val=split, max_val=max_CO2m, my_map=map, color1=orange, color2=red)
    return map

def draw_legend(min_val, max_val, my_map, title="Treibhausgasemissionen ", unit="Tonnen/Km", color1="FFFF00", color2="CE0000"):
    color1 = "#" + color1
    color2 = "#" + color2
    gradient_colormap = LinearColormap([color1, color2], vmin=min_val, vmax=max_val).to_step(25)
    gradient_colormap.caption = f'{title} ({unit})'

    gradient_colormap.add_to(my_map)

    return my_map

def main():
    GO_ONLINE = False # Prevent abusive usage of google maps API

    """
    Prepare object and environment
    """
    print("Starting ...")
    config = Config()
    result_path = config.RESULTS_PATH
    data_path = config.DATA_PATH
    map = Maps(config.MAPS_API_KEY)
    date_string = '2023-11-23 10:00:00.00'
    date_format = '%Y-%m-%d %H:%M:%S.%f'
    departure_date = datetime.strptime(date_string, date_format)
    map_vis = folium.Map(location=[47.654534189215525, 14.234224037285491], zoom_start=7, tiles="cartodbpositron")

    """
    Execute
    """
    raw_to_smart_data(data_path1=data_path+"data_raw.xlsx", data_path2=data_path+"GPS.xlsx", output_path=data_path+"smart_data.csv")
    smart_to_points_data(data_path=data_path+"smart_data.csv", map=map, departure_date=departure_date, online=GO_ONLINE, output_path=data_path+"/poly_points_data_to_add.csv" )
    format_data_for_all_path(data_path=data_path+"poly_points_data.csv", output_path=data_path+"all_path.csv")
    points_to_smart_points(data_path=data_path+"poly_points_data.csv", output_path=data_path+"smart_points_data_d0015.csv")
    map_vis = draw_points(data_path=data_path+"smart_points_data_d0015.csv", map=map_vis, scale=3, split=100, split2=15)
    map_vis = draw_stations(data_path=data_path+"GPS.xlsx", map=map_vis)
    minimap = plugins.MiniMap(toggle_display=True, position='bottomright')
    map_vis.add_child(minimap)

    # save the map
    map_vis.save(result_path+"final_v3.html")


if __name__ == "__main__":
    main()
