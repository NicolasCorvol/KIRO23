from classes import *

instances_size = ['toy', 'small', 'medium', 'large', 'huge']

size = instances_size[0]

pathfile = f'./instances/{size}.json'

f = open(pathfile)
 
# returns JSON object as 
# a dictionary
data = json.load(f)

len(data['substation_location'])