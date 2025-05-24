from flask import Flask, request, render_template
import os
import wntr
import numpy as np

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
    linhas = texto_inp.replace(',', '.').splitlines()
    novas_linhas = []
    dentro_de_pipes = False

    for linha in linhas:
        original = linha.strip()

        if original.upper().startswith('[PIPES]'):
            dentro_de_pipes = True
            novas_linhas.append(original)
            continue

        if dentro_de_pipes and original.startswith('['):
            dentro_de_pipes = False

        if dentro_de_pipes and original and not original.startswith(';'):
            partes = linha.split()
            while len(partes) < 5:
                partes.append('0')

            try:
                diametro = float(partes[4])
            except ValueError:
                diametro = 100.0

            if len(partes) < 6 or not partes[5].replace('.', '', 1).isdigit():
                rug = estimar_rugosidade(diametro)
                if len(partes) < 6:
                    partes.append(str(rug))
                else:
                    partes[5] = str(rug)
            if len(partes) < 7:
                partes.append('0')
            if len(partes) < 8:
                partes.append('Open')

            linha_corrigida = '{:<15}\t{:<15}\t{:<15}\t{:<10}\t{:<10}\t{:<10}\t{:<10}\t{}'.format(
                partes[0], partes[1], partes[2], partes[3], partes[4], partes[5], partes[6], partes[7]
            )
            novas_linhas.append(linha_corrigida)
        else:
            novas_linhas.append(original)

    return '\n'.join(novas_linhas)

def calcular_rugosidade(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    conteudo = conteudo.replace(',', '.')
    conteudo_corrigido = preencher_rugosidade(conteudo)

    temp_path = filepath + "_corrigido.inp"
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(conteudo_corrigido + '\n')  # garante \n final

    wn = wntr.network.WaterNetworkModel(temp_path)
    rugosidades = [
        wn.get_link(name).roughness
        for name in wn.pipe_name_list
        if wn.get_link(name).roughness is not None
    ]
    return round(sum(rugosidades) / len(rugosidades), 2) if rugosidades else None

def calcular_rugosidade_por_simulacao(filepath):
    wn = wntr.network.WaterNetworkModel(filepath)
    sim = wntr.sim.EpanetSimulator(wn)
    results = sim.run_sim()

    rugosidades = []

    for pipe_name in wn.pipe_name_list:
        pipe = wn.get_link(pipe_name)
        diameter = pipe.diameter
        length = pipe.length

        flow_series = results.link['flowrate'].loc[:, pipe_name]
        headloss_series = results.link['headloss'].loc[:, pipe_name]

        flow = abs(flow_series.mean())
        headloss = headloss_series.mean()

        if all(v > 0 for v in [flow, headloss, diameter, length]):
            try:
                numerator = 10.67 * length * flow**1.852
                denominator = headloss * diameter**4.87
                C = (numerator / denominator)**(1/1.852)
                rugosidades.append(C)
            except:
                continue

    return round(np.mean(rugosidades), 2) if rugosidades else None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith('.inp'):
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)

            rug_entrada = calcular_rugosidade(path)
            rug_simulada = calcular_rugosidade_por_simulacao(path)

            return render_template('index.html', resultado=rug_entrada, resultado_simulado=rug_simulada)

        return render_template('index.html', erro="Arquivo inválido")
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
