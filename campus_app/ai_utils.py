import base64
import os
import tempfile
import cv2
import numpy as np
# pyrefly: ignore [missing-import]
from deepface import DeepFace
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer, NEGATE, BOOSTER_DICT

# Initialize VADER
analyzer = SentimentIntensityAnalyzer()

# 🇵🇭 TAGALOG/TAGLISH ENHANCEMENT 🇵🇭
tagalog_lexicon = {
    # Positive
    'maganda': 3.0, 'mahusay': 3.0, 'sulit': 2.5, 'salamat': 2.0, 'naintindihan': 2.0,
    'masaya': 2.5, 'nakatulong': 2.5, 'ayos': 2.0, 'lodi': 2.0, 'petmalu': 2.5,
    'mabait': 2.0, 'mabilis': 1.5, 'malinis': 1.5, 'organisado': 2.0, 'ganap': 1.5,
    'da best': 3.0, 'astig': 2.5, 'panalo': 3.0, 'good job': 2.5, 'nice': 2.0,
    'maraming natutunan': 3.0, 'helpful': 2.5, 'enjoy': 2.5, 'best': 3.0,
    
    # Negative
    'pangit': -3.0, 'sayang': -2.5, 'mabagal': -2.0, 'maingay': -1.5, 'gulo': -2.0,
    'hindi maganda': -3.0, 'failed': -3.0, 'boring': -2.5, 'panget': -3.0,
    'wala': -1.5, 'hindi helpful': -2.5, 'nakakaantok': -2.0, 'mahirap': -1.5,
    'magulo': -2.5, 'bulok': -3.5, 'bad': -2.5, 'late': -1.5,
    'walang kwenta': -3.5, 'sayang oras': -3.0, 'not helpful': -2.5, 'nothing': -1.5,
    'none': -1.5, 'disorganized': -2.0, 'waste': -2.5,
}

# Update constants
NEGATE.extend(['hindi', 'wala', 'huwag', 'di', 'hindi masyadong'])
BOOSTER_DICT.update({
    'sobra': 0.293, 'masyadong': 0.293, 'talaga': 0.293, 'napaka': 0.366,
    'super': 0.366, 'mas': 0.293
})

analyzer.lexicon.update(tagalog_lexicon)
analyzer.lexicon.update({
    'improvement': 0.5,
    'not helpful': -2.5,
    'not helpful at all': -3.0,
})

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
    Updated to ArcFace for better accuracy and RetinaFace for robust detection.
    """
    try:
        img1 = base64_to_cv2(live_base64)
        img2 = base64_to_cv2(anchor_base64)
        
        # 🟢 ArcFace provides superior accuracy for face recognition
        # 🟢 Switched to 'opencv' detector backend for 10x faster processing on CPU (fixes minute-long delays)
        # DeepFace supports direct numpy array passing (img1/img2)
        result = DeepFace.verify(
            img1_path=img1, 
            img2_path=img2, 
            enforce_detection=False,
            model_name='ArcFace', 
            detector_backend='opencv'
        )
        
        return result['verified'], result['distance']
    except Exception as e:
        print(f"DeepFace ArcFace Error: {str(e)}")
        return False, 1.0

def get_sentiment(text):
    """
    Analyzes text and returns a sentiment breakdown.
    Specially handles structured feedback (Learning, Impact, Suggestions).
    """
    if not text or text.strip() == "":
        return {'compound': 0, 'pos': 0, 'neg': 0, 'neu': 1, 'label': 'neutral'}
    
    if "Learning:" in text and "Impact:" in text:
        lines = text.split('\n')
        section_compounds = []
        for line in lines:
            if ":" in line:
                parts = line.split(":", 1)
                label = parts[0].strip().lower()
                content = parts[1].strip() if len(parts) > 1 else ""
                
                neg_placeholders = ['nothing', 'none', 'n/a', 'ni', 'wala', 'no', 'not helpful', 'negative', 'not helpful at all', 'walang natutunan']
                if label in ['learning', 'impact'] and (content.lower() in neg_placeholders or not content):
                    section_compounds.append(-0.7)
                else:
                    section_compounds.append(analyzer.polarity_scores(content)['compound'])
            elif line.strip():
                section_compounds.append(analyzer.polarity_scores(line)['compound'])
        
        if section_compounds:
            avg_compound = sum(section_compounds) / len(section_compounds)
            min_compound = min(section_compounds)
            if min_compound <= -0.5:
                avg_compound = (avg_compound + min_compound) / 2
            vs = {'compound': round(avg_compound, 4), 'pos': 0, 'neg': 0, 'neu': 0}
        else:
            vs = analyzer.polarity_scores(text)
    else:
        vs = analyzer.polarity_scores(text)
    
    if vs['compound'] >= 0.05: label = 'positive'
    elif vs['compound'] <= -0.05: label = 'negative'
    else: label = 'neutral'
    vs['label'] = label
    return vs

def get_rating_sentiment(rating_1_to_5):
    try:
        r = float(rating_1_to_5)
        compound = (r - 3) / 2
        if compound >= 0.05: label = 'positive'
        elif compound <= -0.05: label = 'negative'
        else: label = 'neutral'
        return {'compound': compound, 'label': label}
    except:
        return {'compound': 0, 'label': 'neutral'}
