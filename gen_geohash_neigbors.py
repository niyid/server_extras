from geolib import geohash
import inspect

from geopy.distance import geodesic

def calculate_distance(geohash_a, geohash_b):
    """
    Calculate the distance between the centers of two geohashes using the Haversine formula.
    """
    bbox1 = geohash.bounds(geohash_a)
    bbox2 = geohash.bounds(geohash_b)
    
    # Print the contents and types of bbox1 and bbox2 for debugging
    #print("bbox1:", bbox1, type(bbox1))
    #print("bbox2:", bbox2, type(bbox2))
    
    # Extract latitude and longitude values from the bounds
    lat1 = (bbox1.sw.lat + bbox1.ne.lat) / 2  # Calculate the average latitude
    lon1 = (bbox1.sw.lon + bbox1.ne.lon) / 2  # Calculate the average longitude
    lat2 = (bbox2.sw.lat + bbox2.ne.lat) / 2
    lon2 = (bbox2.sw.lon + bbox2.ne.lon) / 2
    
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def generate_geohashes_within_annuli(reference_geohash, max_radius_km):
    """
    Generate geohashes within annuli of increasing radii around the reference geohash.
    """
    geohashes_within_annuli = {}
    inner_radius_km = 0  # Start from the center
    while inner_radius_km < max_radius_km:
        outer_radius_km = min(inner_radius_km + 3, max_radius_km)  # Increment outer radius by 3 km or set it to max radius

        geohashes_within_annulus = set()
        queue = [reference_geohash]
        visited = set()

        while queue:
            current_geohash = queue.pop(0)
            if current_geohash not in visited:
                visited.add(current_geohash)
                distance = calculate_distance(reference_geohash, current_geohash)
                if inner_radius_km <= distance < outer_radius_km:  # Check if the distance falls within the annulus range
                    geohashes_within_annulus.add(current_geohash)
                    neighbors = geohash.neighbours(current_geohash)
                    queue.extend(neighbors)

        geohashes_within_annuli[outer_radius_km] = geohashes_within_annulus
        inner_radius_km = outer_radius_km  # Move to the next annulus

    return geohashes_within_annuli


# Example reference geohash and max radius
reference_geohash = 's14meec1'
max_radius_km = 198

# Generate geohashes within annuli
geohashes_within_annuli = generate_geohashes_within_annuli(reference_geohash, max_radius_km)

# Print the geohashes within each annulus
for outer_radius, geohashes_within_radius in geohashes_within_annuli.items():
    print(f"Annulus {outer_radius-3}km to {outer_radius}km:")
    for geohash in geohashes_within_radius:
        print(geohash)

