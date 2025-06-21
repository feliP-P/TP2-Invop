import sys
#importamos el modulo cplex
import cplex
from cplex import SparsePair


TOLERANCE =10e-6 

class InstanciaRecorridoMixto:
    def __init__(self):
        self.cant_clientes = 0
        self.costo_repartidor = 0
        self.d_max = 0
        self.refrigerados = []
        self.exclusivos = []
        self.distancias = []        
        self.costos = []        

    def leer_datos(self,filename):
        # abrimos el archivo de datos
        f = open(filename)

        # leemos la cantidad de clientes
        self.cant_clientes = int(f.readline())
        # leemos el costo por pedido del repartidor
        self.costo_repartidor = int(f.readline())
        # leemos la distamcia maxima del repartidor
        self.d_max = int(f.readline())
        
        # inicializamos distancias y costos con un valor muy grande (por si falta algun par en los datos)
        self.distancias = [[1000000 for _ in range(self.cant_clientes)] for _ in range(self.cant_clientes)]
        self.costos = [[1000000 for _ in range(self.cant_clientes)] for _ in range(self.cant_clientes)]
        
        # leemos la cantidad de refrigerados
        cantidad_refrigerados = int(f.readline())
        # leemos los clientes refrigerados
        for i in range(cantidad_refrigerados):
            self.refrigerados.append(int(f.readline()))
        
        # leemos la cantidad de exclusivos
        cantidad_exclusivos = int(f.readline())
        # leemos los clientes exclusivos
        for i in range(cantidad_exclusivos):
            self.exclusivos.append(int(f.readline()))
        
        # leemos las distancias y costos entre clientes
        lineas = f.readlines()
        for linea in lineas:
            row = list(map(int,linea.split(' ')))
            self.distancias[row[0]-1][row[1]-1] = row[2]
            self.distancias[row[1]-1][row[0]-1] = row[2]
            self.costos[row[0]-1][row[1]-1] = row[3]
            self.costos[row[1]-1][row[0]-1] = row[3]
        
        # cerramos el archivo
        f.close()

def cargar_instancia():
    # El 1er parametro es el nombre del archivo de entrada
    nombre_archivo = sys.argv[1].strip()
    # Crea la instancia vacia
    instancia = InstanciaRecorridoMixto()
    # Llena la instancia con los datos del archivo de entrada 
    instancia.leer_datos(nombre_archivo)
    return instancia

def agregar_variables(prob, instancia):
    n = instancia.cant_clientes
    nombres_vc = []
    nombres_vb = []

    # Variables VC y VB
    for i in range(n):
        for j in range(n):
            if i != j:
                nombres_vc.append(f"VC_{i}_{j}")
                nombres_vb.append(f"VB_{i}_{j}")

    prob.variables.add(names=nombres_vc, types=['B'] * len(nombres_vc))
    prob.variables.add(names=nombres_vb, types=['B'] * len(nombres_vb))

    # Variable cant_bicis
    prob.variables.add(names=["cant_bicis"], types=["I"], lb=[0])

    # Variables u_i (orden de visita)
    nombres_u = [f"u_{i}" for i in range(1, n)]
    prob.variables.add(names=nombres_u, lb=[1.0] * (n - 1), ub=[float(n)] * (n - 1), types=["C"] * (n - 1))

def agregar_restricciones(prob, instancia):
    n = instancia.cant_clientes
    d = instancia.distancias
    dist_max = instancia.d_max
    refrigerados = instancia.refrigerados

    # 1. Conservación de flujo del camión
    for k in range(1, n):
        entrada = [f"VC_{i}_{k}" for i in range(n) if i != k]
        salida = [f"VC_{k}_{j}" for j in range(n) if j != k]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(entrada + salida, [1] * len(entrada) + [-1] * len(salida))],
            senses=["E"],
            rhs=[0],
            names=[f"flujo_camion_{k}"]
        )

    # 2. El camión pasa a lo sumo una vez por cliente
    for k in range(n):
        nombres = [f"VC_{k}_{j}" for j in range(n) if j != k]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(nombres, [1] * len(nombres))],
            senses=["L"],
            rhs=[1],
            names=[f"camion_una_vez_{k}"]
        )

    # 3. Bicicleta solo si el cliente fue atendido por camión
    for k in range(n):
        izquierda = [f"VB_{i}_{k}" for i in range(n) if i != k]
        derecha = [f"VC_{k}_{j}" for j in range(n) if j != k]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(izquierda + derecha, [1] * len(izquierda) + [-1] * len(derecha))],
            senses=["L"],
            rhs=[0],
            names=[f"bici_si_camion_{k}"]
        )

    # 4. Distancia máxima bici
    for i in range(n):
        for j in range(n):
            if i != j and d[i][j] > dist_max:
                prob.linear_constraints.add(
                    lin_expr=[SparsePair([f"VB_{i}_{j}"], [1])],
                    senses=["E"],
                    rhs=[0],
                    names=[f"dist_max_bici_{i}_{j}"]
                )

    # 5. Cada cliente es visitado una sola vez (camión o bici)
    for j in range(1, n):
        nombres = [f"VC_{i}_{j}" for i in range(n) if i != j] + [f"VB_{i}_{j}" for i in range(n) if i != j]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(nombres, [1] * len(nombres))],
            senses=["E"],
            rhs=[1],
            names=[f"visita_unica_{j}"]
        )

    # 6. MTZ: evitar ciclos disjuntos
    for i in range(1, n):
        for j in range(1, n):
            if i != j:
                prob.linear_constraints.add(
                    lin_expr=[SparsePair([f"u_{i}", f"u_{j}", f"VC_{i}_{j}"], [1.0, -1.0, float(n)])],
                    senses=["L"],
                    rhs=[n - 1],
                    names=[f"MTZ_{i}_{j}"]
                )

    # 7. Restricción de cantidad de bicis
    nombres = []
    coefs = []
    for i in range(n):
        for j in refrigerados:
            if i != j:
                nombres.append(f"VB_{i}_{j}")
                coefs.append(1)
    nombres.append("cant_bicis")
    coefs.append(-1)
    prob.linear_constraints.add(
        lin_expr=[SparsePair(nombres, coefs)],
        senses=["L"],
        rhs=[0],
        names=["cantidad_bicis"]
    )

def agregar_funcion_objetivo(prob, instancia):
    n = instancia.cant_clientes
    obj_names = []
    obj_coefs = []

    for i in range(n):
        for j in range(n):
            if i != j:
                obj_names.append(f"VC_{i}_{j}")
                obj_coefs.append(instancia.costos[i][j])

                obj_names.append(f"VB_{i}_{j}")
                obj_coefs.append(instancia.costo_repartidor)

    obj_names.append("cant_bicis")
    obj_coefs.append(0.0)  # no tiene costo

    prob.objective.set_sense(prob.objective.sense.minimize)
    prob.objective.set_linear(list(zip(obj_names, obj_coefs)))

def armar_lp(prob, instancia):

    # Agregar las variables
    agregar_variables(prob, instancia)
   
    # Agregar las restricciones 
    agregar_restricciones(prob, instancia)

    # Setear el sentido del problema
    agregar_funcion_objetivo(prob,instancia)

    # Escribir el lp a archivo
    prob.write('recorridoMixto.lp')

def resolver_lp(prob):

    # Resolver el problema
    prob.solve()

def mostrar_solucion(prob,instancia):
    
    # Obtener informacion de la solucion a traves de 'solution'
    
    # Tomar el estado de la resolucion
    status = prob.solution.get_status_string(status_code = prob.solution.get_status())
    
    # Tomar el valor del funcional
    valor_obj = prob.solution.get_objective_value()
    
    print('Funcion objetivo: ',valor_obj,'(' + str(status) + ')')
    
    # Tomar los valores de las variables
    x  = prob.solution.get_values()
    nombres = prob.variables.get_names()

    # Mostrar las variables con valor positivo (mayor que una tolerancia)
    print("🔍 Variables activas:")

    for nombre, valor in zip(nombres, x):
        if valor > TOLERANCE:
            print(f"  {nombre}: {valor:.1f}")

def main():
    
    # Lectura de datos desde el archivo de entrada
    instancia = cargar_instancia()
    
    # Definicion del problema de Cplex
    prob = cplex.Cplex()
    
    # Definicion del modelo
    armar_lp(prob,instancia)

    # Resolucion del modelo
    resolver_lp(prob)

    # Obtencion de la solucion
    mostrar_solucion(prob,instancia)

if __name__ == '__main__':
    main()