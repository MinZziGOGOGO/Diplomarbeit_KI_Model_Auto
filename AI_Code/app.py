from flask import Flask, Response
import cv2

app = Flask(__name__)

def gen_frames():
    camera = cv2.VideoCapture(0)  # Zugriff auf die Standard-Webcam (id=0)
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            # Frame in JPEG kodieren
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            # Ausgabe des Frames als HTTP-Response
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
