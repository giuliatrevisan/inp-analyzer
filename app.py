from flask import Flask, request, render_template
import os
import wntr

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def estimar_rugosidade(diametro, material=None):
    material = (material or '').lower()
    if 'pvc' in material:
        return 130
    if 'ferro' in material or 'galv' in material:
        return 100
    if 'cobre' in material:
        return 120
    if 'amianto' in material:
        return 140

    if diametro <= 50:
        return 120
    elif diametro <= 150:
        return 110
    return 100

def preencher_rugosidade(texto_inp):
    linhas = texto_inp.splitlines()
    novas_linhas = []
    dentro_de_pipes = False

    for linha in linhas:
        original = linha.strip()
        if original.upper().startswith('[PIPES]'):
            dentro_de_pipes = True
            novas_linhas.append(linha)
            continue

        if dentro_de_pipes and original.startswith('['):
            dentro_de_pipes = False

        if dentro_de_pipes and original and not original.startswith(';'):
            partes = linha.split()
            if len(partes) >= 5:
                diametro = float(partes[4]) if partes[4].replace('.', '', 1).isdigit() else 100
            else:
                diametro = 100

            precisa_corrigir = len(partes) < 6 or not partes[5].replace('.', '', 1).isdigit()

            if precisa_corrigir:
                rug = estimar_rugosidade(diametro)
                while len(partes) < 6:
                    partes.append('')
                partes[5] = str(rug)

                linha_corrigida = '\t'.join(partes + linha.split()[len(partes):])
                novas_linhas.append(linha_corrigida)
            else:
                novas_linhas.append(linha)
        else:
            novas_linhas.append(linha)

    return '\n'.join(novas_linhas)

def calcular_rugosidade(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    conteudo_corrigido = preencher_rugosidade(conteudo)

    temp_path = filepath + "_corrigido.inp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(conteudo_corrigido)

    wn = wntr.network.WaterNetworkModel(temp_path)
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
