# Tutorial: Using Google Maps to calculate driving distance between two points in Python 

Geospacial analysis has entered the social science [mainstream](https://twitter.com/KhoaVuUmn/status/1648715231609200640). [Spacial economics](https://www.nature.com/articles/s41598-023-29189-5) and [political geography](https://www.routledge.com/Geographies-of-the-2020-US-Presidential-Election/Warf-Heppen/p/book/9781032197821) are trending thanks to the availability of accessible and user-friendly geospacial analysis software.

As geographic distance is an increasingly popular dependent variable in social science, this tutorial explains how to use the Google Maps API to find driving distance in miles between locations. We simply start with two dataframes containing geocordinates: one with origins, and another with destinations. 

This tutorial specifically will teach you to calculate the driving distance between the origin and the _nearest_ possible destination — assuming the dataframe containing destinations has more than one observation — which can be used to find the driving distance between survey respondents and their nearest polling place, government officials and 311 calls, or even customers and stores in a commercial chain. 

To begin, let's load the required packages: [pandas](https://pandas.pydata.org/docs/), [datetime](https://docs.python.org/3/library/datetime.html), [geopy.distance](https://geopy.readthedocs.io/en/stable/) and [googlemaps](https://googlemaps.github.io/google-maps-services-python/docs/).


```python
import pandas as pd
from datetime import datetime
from geopy.distance import great_circle
import googlemaps
```

Next, we need to define the Google Maps API. To do this, you first need to obtain an API key, which you can obtain [here](https://www.googleadservices.com/pagead/aclk?sa=L&ai=DChcSEwjwwamR-L7-AhWpJrMAHZlUCA4YABAAGgJ5bQ&ohost=www.google.com&cid=CAESauD2F9xG-BTugnGXBtxD34m4pcVNz7LhxNWL6IFNyyD2PWw0ELKVAalJEvYOqJJC1RXQZcnzjQdy1EBeGAtUQ1tfvfEXXN0h8jlt6W6yQWRQ0whYB30n5kCC5--Gf7TlfG6DeaQUO5f7f_A&sig=AOD64_3tt6NuN8koeNb2VirhID9T_luJ_Q&q&adurl&ved=2ahUKEwjmhKCR-L7-AhVDFlkFHXFDA_gQ0Qx6BAgGEAE&nis=8).


```python
# Define the Google Maps API key
gmaps = googlemaps.Client(key='YOUR_KEY', retry_over_query_limit=True)
```

The Google Maps API has usage limits. We can set *retry_over_query_limit* to "True" to avoid rate limit errors when we make our calls to the API. 

### Finding the nearest adult-use cannabis dispensary 

We can now get to work. For this tutorial, I will be calculating the distance between towns in the Philadelphia suburbs and recreational marijuana dispensaries in New Jersey. New Jersey [legalized](https://www.nj.gov/cannabis/adult-personal/) adult-use cannabis in 2022 Despite U.S. Senator and former-Lieutenant Governor John Fetterman's [outspoken support](https://www.politico.com/news/2022/05/17/fetterman-weed-legalization-00032792) for legalization of recreational marijuana, it has yet to occur in Pennsylvania. 

Yet, it has been [well-documented](https://www.wnep.com/article/news/local/pot-now-legal-in-nj-drawing-in-folks-from-pa-easton-philipsburg-recreational-marijuana-adult-use/523-0df177a3-367a-4f0f-b4ee-3713bfcd38b2) that Pennsylvanians in the Philadelphia suburbs have been traveling to New Jersey to [purchase legal pot](https://www.lehighvalleylive.com/phillipsburg/2022/04/legal-recreational-weed-in-nj-draws-pennsylvania-residents-to-phillipsburg-apothecarium.html). The _Philadelphia Inquirerer_ even [published](https://www.inquirer.com/business/weed/pennsylvania-residents-buying-legal-nj-marijuana-weed.html) an article about what Pennsylvanians should know before traveling to New Jersey to purchase cannabis. One [dispensary](https://apothecarium.com/dispensaries/phillipsburg/) in Phillipsburg, New Jersey faces directly across the Delaware River into Easton — it's a modern day Washington's crossing!

We will calculate the driving distance from the centroid of each designated census place in Bucks and Montgomery County to their nearest New Jersey recreational marijuana dispensary!

We can import our dispensary locations from New Jersey's [NJOIT Open Data Center](https://data.nj.gov/Reference-Data/New-Jersey-Cannabis-Dispensary-List/p3ry-ipie/data), a cleaned version of which I have posted on my [GitHub](https://github.com/BrendanTHartnett).


```python
dat = pd.read_csv('https://raw.githubusercontent.com/BrendanTHartnett/the_road_to_pot/main/New_Jersey_Cannabis_Dispensaries.csv')
# Extract the latitude and longitude values from the DISPENSARY LOCATION column
dat['STORElong'] = dat['DISPENSARY LOCATION'].apply(lambda x: float(x.split(' ')[1][1:]))
dat['STORElat'] = dat['DISPENSARY LOCATION'].apply(lambda x: float(x.split(' ')[2][:-1]))
```

Given that medicinal marijuana has been legal in Pennsylvania [since 2016](https://www.pa.gov/guides/pennsylvania-medical-marijuana-program/#:~:text=Governor%20Wolf%20legalized%20medical%20marijuana,patients%20with%20serious%20medical%20conditions.), and our dataframe contains dispensaries in New Jersey which are either medicainal and recreational or just medicinal, we should remove dispensaries which only sell medical marijuana.  


```python
# create a boolean mask indicating which rows have 'TYPE' equal to "Medicinal cannabis only"
mask = dat['TYPE'] == "Medicinal cannabis only"

# use the mask to drop the relevant rows
dat = dat[~mask]
```

Next, import our "customer" data — a dataframe containing the geocoordinates of each Census designated place in Bucks and Montgomery County.


```python
fdat = pd.read_csv('https://raw.githubusercontent.com/BrendanTHartnett/the_road_to_pot/main/bucksmont_subdivisons.csv')
```

Now, with our two dataframes, we need to first match each town with its nearest store. While we could do this using the Google Maps API, the rate limit causes this to be slow and computationally intensive process — and with more observations, these issues will only compound. Instead, we can just find the nearest store by linear distance. There are limitations to doing this, which our region of focus speaks to. 

Given all Pennsylvanians must travel via bridge to New Jersey, this algorithm could misidentify the nearest dispensary to each town based on the [location of bridges](https://www.drjtbc.org). Ultimately, the trade-off between run time and accuracy forces researchers to make a choice based on what they are willing to sacrifice. 

We will define a function to find each town's (in dataframe _fdat_) linear distance to the nearest dispensary (in dataframe _dat_).


```python
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
```

We can then run the function and append the longitude and latitude of the nearest dispensary to the corresponding Pennsylvania town. 


```python
# Find the nearest store for each potential customer and add the STORElong and STORELAD to fdat
fdat[['NearestStoreLong', 'NearestStoreLat']] = fdat.apply(nearest_store, axis=1)
```


```python
fdat.head()
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>GEOID</th>
      <th>NAMELSAD</th>
      <th>BuyerLat</th>
      <th>BuyerLong</th>
      <th>NearestStoreLong</th>
      <th>NearestStoreLat</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>4201704976</td>
      <td>Bedminster township</td>
      <td>40.426614</td>
      <td>-75.188230</td>
      <td>-75.201923</td>
      <td>40.690754</td>
    </tr>
    <tr>
      <th>1</th>
      <td>4201705616</td>
      <td>Bensalem township</td>
      <td>40.106196</td>
      <td>-74.943689</td>
      <td>-74.912595</td>
      <td>40.040754</td>
    </tr>
    <tr>
      <th>2</th>
      <td>4201708592</td>
      <td>Bridgeton township</td>
      <td>40.552842</td>
      <td>-75.121723</td>
      <td>-75.201923</td>
      <td>40.690754</td>
    </tr>
    <tr>
      <th>3</th>
      <td>4201708760</td>
      <td>Bristol borough</td>
      <td>40.102767</td>
      <td>-74.852347</td>
      <td>-74.912595</td>
      <td>40.040754</td>
    </tr>
    <tr>
      <th>4</th>
      <td>4201708768</td>
      <td>Bristol township</td>
      <td>40.123638</td>
      <td>-74.867385</td>
      <td>-74.912595</td>
      <td>40.040754</td>
    </tr>
  </tbody>
</table>
</div>



### Finding driving distances to weed stores

Now we can run a loop that calculates the driving distance from the road nearest the origin (BuyerLat, BuyerLong) and the destination (NearestStoreLat, NearestStoreLat). 

One thing to remember is that the coordinates we are working with may not all be accessible via road — particularly the origin, the coordinates of which simply correspond to the centroids of designated Census places. Therefore, we will find the nearest roadway to the listed coordinates before finding the riving distance between the two locations. Then we simply call the Google Maps API and specify that we want the _driving_ distance between the two points. After getting the distance in meters, we can convert to miles and append the value to our dataframe.


```python
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
    # print(f"Completed {i+1}/{len(fdat)}")  #helpful if large N
```

![ ](https://raw.githubusercontent.com/BrendanTHartnett/the_road_to_pot/main/distances_to_dispensaries.png)

And there you have it. Use this tutorial to calculate accessibility of public services, locate new customers or simply plan a road trip! Enjoy!  
