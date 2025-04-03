from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Tuple
import uuid

app = FastAPI()

# Adiciona o middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelo para registro de navio
class NavioRegistro(BaseModel):
    nome: str = Field(..., max_length=20)
    posicao_central: Tuple[int, int]  # (x, y)
    orientacao: Literal["vertical", "horizontal"]
    correlation_id: str

# Classe que representa o navio
class Navio:
    def __init__(self, nome: str, posicao_central: Tuple[int, int], orientacao: str, correlation_id: str):
        self.nome = nome
        self.posicao_central = posicao_central
        self.orientacao = orientacao
        self.correlation_id = correlation_id
        self.posicoes = self.calcular_posicoes()
        self.pontos = 100  # Pontuação inicial
        self.chave = uuid.uuid4().hex  # Chave de criptografia única

    def calcular_posicoes(self):
        x, y = self.posicao_central
        if self.orientacao == "horizontal":
            # Posição central é a 3ª casa; posições: [x-2, x-1, x, x+1, x+2]
            return [(x - 2, y), (x - 1, y), (x, y), (x + 1, y), (x + 2, y)]
        else:
            # Orientação vertical: variações em y
            return [(x, y - 2), (x, y - 1), (x, y), (x, y + 1), (x, y + 2)]

# Armazenamento dos navios registrados (em memória, para testes)
navios_registrados = {}

@app.post("/registrar")
def registrar_navio(registro: NavioRegistro):
    x, y = registro.posicao_central
    # Valida se a posição central está dentro do campo 100x30
    if not (0 <= x < 100 and 0 <= y < 30):
        raise HTTPException(status_code=400, detail="Posição central fora do campo de batalha.")

    # Verifica se o nome do navio já foi utilizado
    if registro.nome in navios_registrados:
        raise HTTPException(status_code=400, detail="Nome do navio já utilizado.")

    navio = Navio(
        nome=registro.nome,
        posicao_central=registro.posicao_central,
        orientacao=registro.orientacao,
        correlation_id=registro.correlation_id
    )
    navios_registrados[registro.nome] = navio

    return {
        "message": "Navio registrado com sucesso.",
        "chave": navio.chave,
        "posicoes": navio.posicoes,
        "correlation_id": navio.correlation_id
    }

# Modelo para realizar um ataque
class Ataque(BaseModel):
    atacante: str
    alvo: str
    posicao_ataque: Tuple[int, int]
    correlation_id: str  # Deve ser o mesmo que foi liberado pelo controlador

@app.post("/atacar")
def atacar(ataque: Ataque):
    # Verifica se os navios existem
    if ataque.atacante not in navios_registrados or ataque.alvo not in navios_registrados:
        raise HTTPException(status_code=400, detail="Navio atacante ou alvo não registrado.")

    navio_atacante = navios_registrados[ataque.atacante]
    navio_alvo = navios_registrados[ataque.alvo]

    # Valida o CorrelationId para autorização do ataque
    if ataque.correlation_id != navio_atacante.correlation_id:
        navio_atacante.pontos -= 10  # Penalidade por ataque sem permissão
        raise HTTPException(status_code=403, detail="Ataque não autorizado: correlation_id inválido.")

    # Valida se a posição de ataque está dentro do campo
    x, y = ataque.posicao_ataque
    if not (0 <= x < 100 and 0 <= y < 30):
        navio_atacante.pontos -= 10  # Penalidade por ataque fora do campo
        raise HTTPException(status_code=400, detail="Ataque fora do campo de batalha.")

    # Verifica se o ataque atinge o navio adversário
    acertou = ataque.posicao_ataque in navio_alvo.posicoes

    # Calcula a distância mínima (usando distância Manhattan) entre a posição de ataque e as posições do navio adversário
    distancia_minima = min(abs(x - px) + abs(y - py) for (px, py) in navio_alvo.posicoes)
    
    resultado = {"acertou": acertou, "distancia_minima": distancia_minima}

    # Penalidade se atacar o próprio navio
    if ataque.atacante == ataque.alvo:
        navio_atacante.pontos -= 30

    # Se acertou, aplica dano de acordo com a posição atingida
    if acertou:
        indice = navio_alvo.posicoes.index(ataque.posicao_ataque)
        if indice in [0, 4]:
            dano = 15
        elif indice in [1, 3]:
            dano = 45
        else:  # Posição 3
            dano = 100
        navio_alvo.pontos -= dano

    return {
        "message": "Ataque processado.",
        "resultado": resultado,
        "pontos_restantes_alvo": navio_alvo.pontos,
        "correlation_id": ataque.correlation_id
    }
