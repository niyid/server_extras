from geolib import geohash

def get_neighbouring_ring(level: int, hashes: list):
    try:
        if not isinstance(level, int) or level <= 0:
            raise ValueError("Level must be a positive integer greater than 0.")
        
        if not isinstance(hashes, list) or not all(isinstance(h, str) for h in hashes):
            raise ValueError("Hashes must be a list of strings.")

        visited = set(hashes)
        queue = hashes.copy()
        next_level_items = []

        while level > 0:
            for hash in queue:
                neighbors = geohash.neighbours(hash)
                next_level_items.extend(neighbors)
                visited.update(neighbors)

            queue = next_level_items.copy()
            next_level_items.clear()
            level -= 1

        return list(visited)

    except ValueError as e:
        print(f"Error: {e}")
        return []

# Test example:
level = 5   # input the depth of the ring
hashes = ['s14meec1']   # include only the center geohash of the ring

ring = get_neighbouring_ring(level, hashes)
print(ring)
