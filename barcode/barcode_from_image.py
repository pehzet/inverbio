from pyzbar.pyzbar import decode
from PIL import Image

# Bild einlesen
images = ["nutella_barcode_close.jpeg", "nutella_barcode_far.jpg", "nutella_barcode_3.jpg", "xucker_barcode.jpg"]

for image_file in images:
    img = Image.open(image_file)
    # Alle erkannten Codes als Liste von pyzbar.Decoded objects
    codes = decode(img)
    print(f"PYZ: Erkannte Codes in '{image_file}': {len(codes)}")
    for c in codes:
        print("Typ :", c.type)         # z. B. 'EAN13'
        print("Daten:", c.data.decode())# Byte-String → Text
        # Koordinaten des Umrisses (4-Eck):
        print("Ecken:", c.polygon)      
        print("-" * 40)

    import cv2

    detector = cv2.barcode.BarcodeDetector()
    # Für QR nur: detector = cv2.QRCodeDetector()

    img = cv2.imread(image_file)

    ok, decoded_info, corners = detector.detectAndDecode(img)
    if not ok:
        print(f"OpenCV: Keine Codes erkannt in '{image_file}'")
    else:
        print(f"OpenCV: Erkannte Codes in '{image_file}': {len(decoded_info)}")
        for i, info in enumerate(decoded_info):

            print("Daten:", info)
            print("Ecken:", corners[i].tolist() if corners is not None else "Keine Ecken")
            print("-" * 40)

