import cv2
from src.models.page import PageImages
from .orientation import normalize_orientation
from .deskew import deskew

def create_variants(image,config)->PageImages:
    original=image.copy(); work=normalize_orientation(image,config.get("orientation_detection",True))
    if config.get("deskew",True): work=deskew(work,float(config.get("max_skew_degrees",5.0)))
    gray=cv2.cvtColor(work,cv2.COLOR_BGR2GRAY)
    binary=cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,41,15)
    return PageImages(original,work,binary)
