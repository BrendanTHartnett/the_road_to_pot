import pandas as pd
from datetime import datetime
from geopy.distance import great_circle
import googlemaps

# Define the Google Maps API key
gmaps = googlemaps.Client(key='YOUR_KEY', retry_over_query_limit=True)

dat = pd.read_csv('https://raw.githubusercontent.com/BrendanTHartnett/the_road_to_pot/main/New_Jersey_Cannabis_Dispensaries.csv')
# Extract the latitude and longitude values from the DISPENSARY LOCATION column
dat['STORElong'] = dat['DISPENSARY LOCATION'].apply(lambda x: float(x.split(' ')[1][1:]))
dat['STORElat'] = dat['DISPENSARY LOCATION'].apply(lambda x: float(x.split(' ')[2][:-1]))

# create a boolean mask indicating which rows have 'TYPE' equal to "Medicinal cannabis only"
mask = dat['TYPE'] == "Medicinal cannabis only"
# use the mask to drop the relevant rows
dat = dat[~mask]

fdat = pd.read_csv('https://raw.githubusercontent.com/BrendanTHartnett/the_road_to_pot/main/bucksmont_subdivisons.csv')

def nearest_store(row):
    buyer_lat, buyer_long = row['BuyerLat'], row['BuyerLong']
    buyer_loc = (buyer_lat, buyer_long)
    min_dist = float('inf')
    nearest_store = None

    for _, store in dat.iterrows():
        store_lat, store_long = store['STORElat'], store['STORElong']
        store_loc = (store_lat, store_long)
        distance = great_circle(buyer_loc, store_loc).meters

        if distance < min_dist:
            min_dist = distance
            nearest_store = store

    return pd.Series([nearest_store['STORElong'], nearest_store['STORElat']])
  
# Find the nearest store for each potential customer and add the STORElong and STORELAD to fdat
fdat[['NearestStoreLong', 'NearestStoreLat']] = fdat.apply(nearest_store, axis=1)
fdat.head()

# Loop through each row in the fdat dataframe and compute the driving distance
for i in range(0, len(fdat)):
    # Define the coordinates for the two points: buyer (origin) and store (destination)
    origin = (fdat['BuyerLat'][i], fdat['BuyerLong'][i])
    destination = (fdat['NearestStoreLat'][i], fdat['NearestStoreLong'][i])

    # Find the nearest road using the Google Maps API for both the buyer and the store
    origin_geocode_result = gmaps.reverse_geocode(origin)  # get location info for the origin
    origin_nearest_road = origin_geocode_result[0]['formatted_address']  # get address of road nearest to origin
    destination_geocode_result = gmaps.reverse_geocode(destination)  # get location info for the destination
    destination_nearest_road = destination_geocode_result[0]['formatted_address']  # address of road nearest to origin

    # Find driving distance between two points using Google Maps API
    now = datetime.now()  # get the current time
    directions_result = gmaps.directions(origin,  # request driving directions from origin to destination
                                         destination,
                                         mode="driving", # can be changed to other travel form 
                                         departure_time=now)  
    # If directions result is available, calculate driving distance in miles
    if directions_result:
        distance_meters = directions_result[0]['legs'][0]['distance']['value']  # extract distance in meters
        distance_miles = distance_meters * 0.000621371  # convert meters to miles
        milage = distance_miles
    else:
        milage = None

    # Add  driving distance to fdat
    fdat.at[i, 'driving_distance'] = milage  

    # Print the current iteration number to track progress
    print(f"Completed {i+1}/{len(fdat)}")  #helpful if large N
