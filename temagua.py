import requests
import json
import os
from datetime import datetime, timezone

def buscar_calendario_compesa(nome_bairro_usuario, jaPerguntou=False):
    caminho_json = os.path.join(os.path.dirname(__file__), 'bairros.json')
    with open(caminho_json, 'r', encoding='utf-8') as f:
        mapa_bairros = json.load(f)

    bairro_chave = nome_bairro_usuario.upper().strip()
    
    opcoes = [k for k in mapa_bairros.keys() if k.startswith(bairro_chave) and k != bairro_chave]
    
    id_area = None
    
    if (opcoes or bairro_chave in mapa_bairros) and not jaPerguntou:
        candidatos = [bairro_chave] + opcoes if bairro_chave in mapa_bairros else opcoes
        ids_vistos = {}
        
        for nome in candidatos:
            id_val = mapa_bairros.get(nome)
            if id_val and id_val not in ids_vistos.values():
                ids_vistos[nome] = id_val
                

        if len(ids_vistos) > 1:
          sugestoes = sorted([nome.title() for nome in ids_vistos.keys()])
          texto_opcoes = ", ".join(sugestoes[:-1]) + " ou " + sugestoes[-1]
          return f"MULTIPLO|Encontrei variações para esse nome. Você se refere a: {texto_opcoes}?"
        elif len(ids_vistos) == 1:
          nome = list(ids_vistos.keys())[0]
          id_area = ids_vistos[nome]
          nome_bairro_usuario = nome
    
    if not id_area:
      id_area = mapa_bairros.get(bairro_chave)
    
    if not id_area:
        return f"Desculpe, eu ainda não encontrei o {nome_bairro_usuario.title()} na minha lista."
    
    agora_utc = datetime.now(timezone.utc)
    hoje = agora_utc.date()
    mes_atual = hoje.strftime('%m')
    ano_atual = hoje.strftime('%Y')

    url_manutencao = f"https://geo.compesa.com.br:6443/arcgis/rest/services/Calendario/Calendario/MapServer/2/query?f=json&where=ID_AREA_ABASTECIMENTO='{id_area}'&outFields=INICIO_PREVISTO,TERMINO_PREVISTO,DESCRICAO_SERVICO"
    
    url_calendario = (
        f"https://geo.compesa.com.br:6443/arcgis/rest/services/Calendario/Calendario/MapServer/5/query?f=json"
        f"&where=(ID='{id_area}')%20AND%20(DATEPART(MONTH,Inicio)='{mes_atual}'%20OR%20DATEPART(MONTH,Termino)='{mes_atual}')"
        f"%20AND%20(DATEPART(YEAR,Inicio)='{ano_atual}')"
        f"&outFields=Inicio,Termino"
    )

    try:
        res_m = requests.get(url_manutencao, timeout=10).json()
        res_a = requests.get(url_calendario, timeout=10).json()

        manutencao_msg = ""
        for f in res_m.get("features", []):
            at = f["attributes"]
            dt_m_ini = datetime.fromtimestamp(at["INICIO_PREVISTO"] / 1000, tz=timezone.utc)
            if dt_m_ini.date() == hoje:
                manutencao_msg = f"consta uma manutenção para {at['DESCRICAO_SERVICO'].lower()}. "
                break

        eventos = res_a.get("features", [])
        eventos.sort(key=lambda e: e["attributes"]["Inicio"])

        selecionado = None
        tipo = ""

        for f in eventos:
            at = f["attributes"]
            dt_ini = datetime.fromtimestamp(at["Inicio"] / 1000, tz=timezone.utc)
            dt_fim = datetime.fromtimestamp(at["Termino"] / 1000, tz=timezone.utc)

            if dt_fim > agora_utc:
                selecionado = (dt_ini, dt_fim)
                if dt_ini <= agora_utc:
                    tipo = "rolando"
                elif dt_ini.date() == hoje:
                    tipo = "futuro_hoje"
                else:
                    tipo = "futuro_proximo"
                break

        if not selecionado:
            return f"Em {nome_bairro_usuario.title()}, o calendário não possui previsões para este mês."

        dt_ini, dt_fim = selecionado
        hora_ini = dt_ini.strftime("%H:%M")
        hora_fim = dt_fim.strftime("%H:%M")

        MESES ={
          1: "janeiro",
          2: "fevereiro",
          3: "março",
          4: "abril",
          5: "maio",
          6: "junho",
          7: "julho",
          8: "agosto",
          9: "setembro",
          10: "outubro",
          11: "novembro",
          12: "dezembro"
        }
        data_ini = f"{dt_ini.day} de {MESES[dt_ini.month]}"
        data_fim = f"{dt_fim.day} de {MESES[dt_fim.month]}"

        status_manut = manutencao_msg if manutencao_msg else "não há manutenção hoje. "
        
        if tipo == "rolando":
            status_agua = f"o abastecimento está normal e vai até às {hora_fim} do dia {data_fim}."
        elif tipo == "futuro_hoje":
            status_agua = f"terá água hoje, começando às {hora_ini} e indo até dia {data_fim} às {hora_fim}."
        else:
            status_agua = f"a próxima previsão é de {data_ini} às {hora_ini} até o dia {data_fim} às {hora_fim}."

        return f"Em {nome_bairro_usuario.title()}, {status_manut}No calendário, {status_agua}"

    except Exception as e:
        print(f"Erro técnico: {e}")
        
        return "Desculpe, não consegui acessar o sistema da Compesa agora."
