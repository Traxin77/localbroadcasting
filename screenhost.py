from flask import Flask, render_template, Response, request, redirect, url_for,send_from_directory
import cv2
from PIL import ImageGrab
import numpy as np
from datetime import datetime,timezone
import pyautogui as py
import os
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
app = Flask(__name__)
x,y = py.size()
x,y = int(str(x)),int(str(y))
fourcc = cv2.VideoWriter_fourcc(*'avc1')
out = cv2.VideoWriter('output.mp4', fourcc, 60.0, (x,y))

streaming_enabled=True
UPLOAD_FOLDER = 'uploads'
STDUPLOAD_FOLDER = 'submission'

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'exe','docx'}


app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STDUPLOAD_FOLDER'] = STDUPLOAD_FOLDER

app.config['MYSQL_HOST'] = 'localhost'  
app.config['MYSQL_USER'] = 'root'  
app.config['MYSQL_PASSWORD'] = ''  
app.config['MYSQL_DB'] = 'broadcast'  
mysql = MySQL(app)


def get_user_info():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM user_info")
    data = cur.fetchall()
    cur.close()
    return data

def gen_frames():
        while streaming_enabled:
            # Capture screenshot
            img = ImageGrab.grab(bbox=(0, 0, x,y))
            frame = np.array(img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            out.write(frame)

            # Display the resulting frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')    
        end_img = cv2.imread('streamended.jpg')
        ret, buffer = cv2.imencode('.jpg', end_img)
        end_frame = buffer.tobytes()
        yield (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + end_frame + b'\r\n')
        out.release()
            
        
    

def record_user_info(name):
    user_ip = request.remote_addr  # Get the user's IP address
    cur = mysql.connection.cursor()
    date = datetime.now(timezone.utc).astimezone()
    cur.execute("INSERT INTO user_info (name, ip_address,login_time) VALUES (%s, %s,%s)", (name, user_ip,date))
    mysql.connection.commit()
    cur.close()
    
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def stop_stream():
    global streaming_enabled
    streaming_enabled = False
    out.release()
    
@app.route('/delete1',methods=['POST'])
def delete():
    cur = mysql.connection.cursor()
    cur.execute("TRUNCATE TABLE user_info")
    cur.close()
    return render_template('admin1.html')
    
@app.route('/upload', methods=['POST'])
def upload_file():
    file_input = request.files['fileInput']

    if file_input and allowed_file(file_input.filename):
        filename = secure_filename(file_input.filename)
        file_input.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    return redirect(url_for('admin'))

@app.route('/stdupload', methods=['POST'])
def upload_stdfile():
    file_input = request.files['fileInput']

    if file_input and allowed_file(file_input.filename):
        filename = secure_filename(file_input.filename)
        file_input.save(os.path.join(app.config['STDUPLOAD_FOLDER'], filename))
    return redirect(url_for('view'))

@app.route('/video_feed', methods=['GET', 'POST'])
def video_feed():
    if request.method == 'POST':
        name = request.form['name']
        record_user_info(name)

    # Video streaming route. 
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/', methods=['GET', 'POST'])
def login():
    return render_template('login.html')

@app.route('/view',methods=['GET', 'POST'])
def view():
    if request.method == 'POST':
        name = request.form['name']
        record_user_info(name)
        if name.lower() == 'admin':
            return redirect(url_for('admin'))
        """Video streaming home page."""
        
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    return render_template('screen.html',uploaded_files=uploaded_files)

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    user_info_data = get_user_info()
    uploaded_files = os.listdir(app.config['UPLOAD_FOLDER'])
    st_uploaded_files = os.listdir(app.config['STDUPLOAD_FOLDER'])
    # Pass the data to the template
    return render_template('admin1.html', user_info_data=user_info_data, uploaded_files=uploaded_files,st_uploaded_files=st_uploaded_files)

@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Redirect to the admin page after deletion
    return redirect(url_for('admin'))

@app.route('/stop_stream', methods=['POST'])
def stop_stream_endpoint():
    stop_stream()
    return redirect(url_for('admin'))
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True,port=8080)