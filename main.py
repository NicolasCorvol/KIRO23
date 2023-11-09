from classes import *

instances_size = ['toy', 'small', 'medium', 'large', 'huge']

size = instances_size[0]

pathfile = f'./instances/{size}.json'

instance = Instance(filepath)

open_stations = instance.stations

# Calcul de distances
distances = np.zeros(shape=(len(instance.turbines), len(open_stations)))
for i, station in enumerate(open_stations):
    for j, turbine in enumerate(instance.turbines):
        distances[j,i] = station.distance(turbine)

print(distances)