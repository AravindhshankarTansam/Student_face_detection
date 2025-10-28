import cv2

print("🔍 Trying to open camera...")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Failed to open camera on index 0, trying index 1...")
    cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("❌ No camera found! Check if another app is using it.")
else:
    print("✅ Camera opened successfully! Press Q to quit.")
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ No frame captured! Retrying...")
            continue
        cv2.imshow("Camera Test", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

cap.release()
cv2.destroyAllWindows()
print("Camera test ended.")
