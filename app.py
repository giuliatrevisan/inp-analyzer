from flask import Flask, request, render_template
import os
import wntr

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def calcular_rugosidade(filepath):
    wn = wntr.network.WaterNetworkModel(filepath)
    rugosidades = [
        wn.get_link(name).roughness
        for name in wn.pipe_name_list
        if wn.get_link(name).roughness is not None
    ]
    return round(sum(rugosidades) / len(rugosidades), 2) if rugosidades else None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.inp'):
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)
            rug = calcular_rugosidade(path)
            return render_template('index.html', resultado=rug)
        return render_template('index.html', erro="Arquivo inválido")
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
