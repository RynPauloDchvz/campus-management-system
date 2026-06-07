import base64
import os
import tempfile
import cv2
import numpy as np
from deepface import DeepFace
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER
analyzer = SentimentIntensityAnalyzer()

def base64_to_cv2(b64_string):
    """Converts a base64 string (with or without prefix) to a CV2 image."""
    if "," in b64_string:
        b64_string = b64_string.split(",")[1]
    
    img_data = base64.b64decode(b64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

def verify_face(live_base64, anchor_base64):
    """
    Verifies if the face in live_base64 matches anchor_base64 using DeepFace.
    Returns (True/False, distance)
    """
    try:
        # Save to temporary files because DeepFace handles paths better
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f1, \
             tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as f2:
            
            img1 = base64_to_cv2(live_base64)
            img2 = base64_to_cv2(anchor_base64)
            
            cv2.imwrite(f1.name, img1)
            cv2.imwrite(f2.name, img2)
            
            # DeepFace Verification
            # We use 'Facenet' or 'VGG-Face' which are generally reliable.
            # enforce_detection=False allows processing even if face detector is unsure.
            result = DeepFace.verify(
                img1_path=f1.name, 
                img2_path=f2.name, 
                enforce_detection=False,
                model_name='VGG-Face',
                detector_backend='opencv'
            )
            
            # Clean up temp files
            os.unlink(f1.name)
            os.unlink(f2.name)
            
            return result['verified'], result['distance']
            
    except Exception as e:
        print(f"DeepFace Error: {str(e)}")
        return False, 1.0

def get_sentiment(text):
    """
    Analyzes text and returns a sentiment breakdown.
    Returns {compound, pos, neg, neu, label}
    """
    if not text or text.strip() == "":
        return {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1, 'label': 'neutral'}
    
    vs = analyzer.polarity_scores(text)
    
    # Labeling based on compound score
    if vs['compound'] >= 0.05:
        label = 'positive'
    elif vs['compound'] <= -0.05:
        label = 'negative'
    else:
        label = 'neutral'
    
    vs['label'] = label
    return vs

def get_rating_sentiment(rating_1_to_5):
    """
    Maps a numerical rating (1-5) to a synthetic sentiment score (-1 to 1).
    Used to normalize ratings for charting with VADER scores.
    """
    try:
        r = float(rating_1_to_5)
        # Map 1-5 to -1 to 1
        # 1 -> -1, 3 -> 0, 5 -> 1
        compound = (r - 3) / 2
        
        if compound >= 0.05: label = 'positive'
        elif compound <= -0.05: label = 'negative'
        else: label = 'neutral'
        
        return {
            'compound': compound,
            'label': label
        }
    except:
        return {'compound': 0, 'label': 'neutral'}
