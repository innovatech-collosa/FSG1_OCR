import numpy as np

def normalize_orientation(image:np.ndarray, enabled:bool=True)->np.ndarray:
    # V2.0.0 deliberately conservative. Rotation inference will be hardened later.
    return image.copy()
