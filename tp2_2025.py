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

    # Variables u_i (orden de visita)
    nombres_u = [f"u_{i}" for i in range(1, n)]
    prob.variables.add(names=nombres_u, lb=[0] * (n - 1), ub=[float(n)] * (n - 1), types=["C"] * (n - 1))
    # variable u_0 = 0 (se empieza recorrido en deposito)
    prob.variables.add(names=["u_0"], lb=[0], ub=[0],types=["C"])
    
    # Variables delta_i (binarias, indican si una bici fue usada o no)
    nombres_delta = [f"delta_{i}" for i in range(n)]
    prob.variables.add(names=nombres_delta, types=["B"] * n)


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

    # 3. Solo se pueden hacer viajes en bici desde k si el camión llegó a k
    for k in range(n):
        bici_saliendo = [f"VB_{k}_{j}" for j in range(n) if j != k]
        camion_llega = [f"VC_{i}_{k}" for i in range(n) if i != k]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(bici_saliendo + camion_llega, [1] * len(bici_saliendo) + [-n] * len(camion_llega))],
            senses=["L"],
            rhs=[0],
            names=[f"bici_desde_k_si_camion_llega_{k}"]
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
    for j in range(n):
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
                    lin_expr=[SparsePair([f"u_{i}", f"u_{j}", f"VC_{i}_{j}"], [1.0, -1.0, float(n-1)])],
                    senses=["L"],
                    rhs=[n - 2],
                    names=[f"MTZ_{i}_{j}"]
                )
        #6.b posición de las ciudades. Agregamos cota inferior y superior si se usa, o igualamos a cero caso contrario
        nombres = []
        coefsi = []
        coefss = []
        nombres.append(f"u_{i}")
        coefsi.append(1)
        coefss.append(1)
        for j in range(n):
          if i != j:
            nombres.append(f"VC_{i}_{j}")
            coefsi.append(-1)
            coefss.append(-n+1)

        prob.linear_constraints.add(
          lin_expr=[SparsePair(nombres, coefsi)],
          senses=["G"],
          rhs=[0],
          names=[f"cota_inferior_u_{i}"]
        )
        prob.linear_constraints.add(
          lin_expr=[SparsePair(nombres, coefss)],
          senses=["L"],
          rhs=[0],
          names=[f"cota_superior_u_{i}"]
        )
    #6.c Deposito (nodo 0) visitado obligatoriamente por camión:
    nombres = [f"VC_{i}_{0}" for i in range(n) if i != (0)]
    prob.linear_constraints.add(
            lin_expr=[SparsePair(nombres, [1] * len(nombres))],
            senses=["E"],  # igual que
            rhs=[1],
            names=[f"camion_obligatorio_{0}"]
        )

    # 7. Restricción de cantidad de bicis
    for i in range(n):
        nombres=[]
        coefs=[]
        for j in refrigerados:
            if i != j:
                nombres.append(f"VB_{i}_{j}")
                coefs.append(1)
        prob.linear_constraints.add(
            lin_expr=[SparsePair(nombres,coefs)],
            senses=["L"],
            rhs = [1],
            names = [f"productos_refrigerados_{i}"]
        )

    # 8. Clientes que deben ser visitados por el camión
    for j in instancia.exclusivos:
        nombres = [f"VC_{i}_{j-1}" for i in range(instancia.cant_clientes) if i != (j - 1)]
        prob.linear_constraints.add(
            lin_expr=[SparsePair(nombres, [1] * len(nombres))],
            senses=["G"],  # Mayor o igual que
            rhs=[1],
            names=[f"camion_obligatorio_{j}"]
        )
    
    # 9. Cada bici hace a lo sumo 4 viajes
    for i in range(n):
        
        #9.1
        nombres = []
        coefs = []
        nombres.append(f"delta_{i}")
        coefs.append(-n)
        for j in range(n):
            if i != j:
                nombres.append(f"VB_{i}_{j}")
                coefs.append(1)
        
        prob.linear_constraints.add(
            lin_expr =[SparsePair(nombres,coefs)],
            senses=["L"],
            rhs = [0],
            names=[f"delta1SiHayEntrega_{i}"]
        )

        #9.2
        nombres = []
        coefs = []
        nombres.append(f"delta_{i}")
        coefs.append(-4)
        for j in range(n):
            if i != j:
                nombres.append(f"VB_{i}_{j}")
                coefs.append(1)
        
        prob.linear_constraints.add(
            lin_expr =[SparsePair(nombres,coefs)],
            senses=["G"],
            rhs = [0],
            names=[f"delta0SiNoHayEntrega_{i}"]
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
        if valor > TOLERANCE and nombre.startswith("VC"):
            i, j = map(int, nombre[3:].split("_"))
            costo = instancia.costos[i][j]
            print(f"{nombre}: {valor:.1f} costo: {costo}")

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
