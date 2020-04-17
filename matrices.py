import random                       # CREAR NUMEROS ALEATORIOS
from time import time               # CALCULAR TIEMPO EJECUCION
from cos_backend import COSBackend  # MANIPULACION OBJETOS EN OBJECT STORAGE
import pickle                       # MANIPULAR LISTAS
import numpy as np                  # GENERAR MATRIZ INICIALIZADA A 0
import pywren_ibm_cloud as pywren   # USO DE HERRAMIENTAS DEL CLOUD FUNCTIONS

path = 'c:/Users/iarri/OneDrive/Desktop/SD/'
config_os = {'endpoint': 'https://s3.eu-gb.cloud-object-storage.appdomain.cloud',
             'secret_key': 'a4a6ae4a4866e326ab7358b8ccf6dc291ce039e6ac0dbee0',
             'acces_key': 'ddae3ad7a436482480024fe6507f75bf'}
config_cf = {'pywren': {'storage_bucket': 'sistemasdistribuidos2'},

             'ibm_cf': {'endpoint': 'https://eu-gb.functions.cloud.ibm.com',
                        'namespace': 'inigo.arriazu@estudiants.urv.cat_dev',
                        'api_key': '67bcc1e5-6e77-4c4b-abab-4c48a5e1113d:En4tKcPGEdkkvUXGACGGFkUOpV8X6ZbRKviFVjERQhxRQBRnyyoncnzbLwz4QkKZ'},

             'ibm_cos': {'endpoint': 'https://s3.eu-gb.cloud-object-storage.appdomain.cloud',
                         'private_endpoint': 'https://s3.private.eu-gb.cloud-object-storage.appdomain.cloud',
                         'api_key': 'IJh1pZFpraju8B4zTS3Czhw7PLZ4AQKtfycjeebwStF8'}}


# Numero de Workers
W = 200
# tamaño de filas matriz 1 (M) y columnas matriz 1(N)/filas matriz 2(N)
M = 200
N = 200
# tamaño de columnas matriz 2(L)
L = 200

# Creem instancia del servidor
cos = COSBackend(config_os)
# ----------------------------------------------------------------------------
# RUTINAS PRINCIPALES
# ----------------------------------------------------------------------------


def matrizMultCloud(casilla_ini, num_casillas):
    cos = COSBackend(config_os)
    res = 0
    resultados = []
    while(num_casillas > 0):
        fila_num, col_num = CalcPosMatrix(casilla_ini, M, L)
        fila = pickle.loads(cos.get_object(
            'sistemasdistribuidos2', 'fila'+str(fila_num)))
        columna = pickle.loads(cos.get_object(
            'sistemasdistribuidos2', 'colum'+str(col_num)))
        for n in range(N):
            res += fila[n] * columna[n]
        resultados.append([fila_num, col_num, res])
        num_casillas -= 1
        casilla_ini += 1
        res = 0
    return resultados


def reunirResultados(results):
    matriz_resultado = np.zeros((M, L), dtype=int)
    for grupo_resultados in results:
        for resultado in grupo_resultados:
            fila, col, valor = resultado
            matriz_resultado[fila][col] = valor
    return matriz_resultado

# ----------------------------------------------------------------------------
# RUTINAS AUXILIARES
# ---------------------------------------------------------------------------


def inicializarMatriz(rows, cols):
    matriz = [[random.randrange(0, 100)
               for n in range(cols)] for m in range(rows)]
    return matriz


def guardarMatrices(mA, mB, filasA, columnasB):
    for fila in range(filasA):
        print(fila)
        cos.put_object('sistemasdistribuidos2', 'fila'+str(fila),
                       pickle.dumps(mA[fila]))
    for col in range(columnasB):
        print(col)
        cos.put_object('sistemasdistribuidos2', 'colum'+str(col),
                       pickle.dumps(list(row[col] for row in mB)))


def CalcPosMatrix(num_casilla, rows, columns):
    if (num_casilla < (rows*columns)):
        fila = num_casilla/columns
        col = num_casilla % columns
        return int(fila), int(col)
    else:
        return None


def CalcNumCasillas(workers):
    iterdata = []
    if workers > M*L:
        workers = M*L
    casilla_ini = int(0)
    num_casillas_pred = int((M * L)/workers)
    resto = int((M * L) % workers)
    for i in range(workers):
        if resto > 0:
            iterdata.append([int(casilla_ini), int(num_casillas_pred + 1)])
            resto -= 1
            casilla_ini += num_casillas_pred + 1
        else:
            iterdata.append([int(casilla_ini), int(num_casillas_pred)])
            casilla_ini += num_casillas_pred

    return iterdata


def sacarCasillaConcreta(fila, col):
    fil = pickle.loads(cos.get_object(
        'sistemasdistribuidos2', 'fila'+str(fila)))
    colum = pickle.loads(cos.get_object(
        'sistemasdistribuidos2', 'colum'+str(col)))
    val = 0
    for n in range(N):
        val += fil[n] * colum[n]
    return val


def mostrar_matriz(A, B, matriz):
    for a in range(A):
        print("|", end="")
        for b in range(B):
            print(matriz[a][b],   end=" ")
        print("|")


def matrizMultiplication(filas, columnas, comun):  # corregir globales
    print("multiplicacion de matrices")
    matriz_resultado = np.zeros((filas, columnas), dtype=int)
    for m in range(filas):
        for l in range(columnas):
            fila = pickle.loads(cos.get_object(
                'sistemasdistribuidos2', 'fila'+str(m)))
            columna = pickle.loads(cos.get_object(
                'sistemasdistribuidos2', 'colum'+str(l)))
            matriz_resultado[m][l] = 0
            for n in range(comun):
                matriz_resultado[m][l] += fila[n] * columna[n]
    return matriz_resultado
# ----------------------------------------------------------------------------


if __name__ == '__main__':
    # M = int(input("Escriba el numero de filas de la matriz A:"))
    # N = int(input(
    #     "Escriba el numero de columnas de la matriz A (mismo numero para filas de B):"))
    # L = int(input("Escriba el numero de columnas de la matriz B:"))
    # W = int(input("Escribe el numero de workers:"))
    matriz1 = inicializarMatriz(M, N)
    matriz2 = inicializarMatriz(N, L)
    guardarMatrices(matriz1, matriz2, M, L)
    # EJECUCION EN LA NUBE
    ibmcf = pywren.ibm_cf_executor(config=config_cf)
    iterdata = CalcNumCasillas(W)
    stime_cloud = time()
    ibmcf.map_reduce(matrizMultCloud, iterdata,
                     reunirResultados, reducer_wait_local=True)
    etime_cloud = time() - stime_cloud
    # print(ibmcf.get_result())
    print('CLOUD:'+str(etime_cloud))
    # EJECUCION LOCAL
    stime_local = time()
    # matrizMultiplication(M, L, N)
    etime_local = time() - stime_local
    print('LOCAL:'+str(etime_local))
    print("el numero de workers:" + str(W))
