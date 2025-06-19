import sys
#importamos el modulo cplex
import cplex

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
        self.cantidad_clientes = int(f.readline())
        # leemos el costo por pedido del repartidor
        self.costo_repartidor = int(f.readline())
        # leemos la distamcia maxima del repartidor
        self.d_max = int(f.readline())
        
        # inicializamos distancias y costos con un valor muy grande (por si falta algun par en los datos)
        self.distancias = [[1000000 for _ in range(self.cantidad_clientes)] for _ in range(self.cantidad_clientes)]
        self.costos = [[1000000 for _ in range(self.cantidad_clientes)] for _ in range(self.cantidad_clientes)]
        
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
    nombres = []
    costos = []
    tipos = []
    lb = []
    ub = []

    n = instancia.cantidad_clientes
    dmax = instancia.d_max
    costo_rep = instancia.costo_repartidor

    # y_i: si el camión visita al cliente i
    for i in range(n):
        nombres.append(f"y_{i}")
        costos.append(0.0)  # el costo de y_i lo asumimos implícito en x o en z
        tipos.append("B")
        lb.append(0.0)
        ub.append(1.0)

    # x_ij: si el camión va de i a j 
    for i in range(n):
        for j in range(n):
            if i != j:
                nombres.append(f"x_{i}_{j}")
                costos.append(instancia.costos[i][j])  # costo del camión
                tipos.append("B")
                lb.append(0.0)
                ub.append(1.0)

    # z_ij: si cliente j es atendido por repartidor desde i
    for i in range(n):
        for j in range(n):
            if i != j and instancia.distancias[i][j] <= dmax:
                nombres.append(f"z_{i}_{j}")
                costos.append(costo_rep)  # costo por cada entrega a pie/bici
                tipos.append("B")
                lb.append(0.0)
                ub.append(1.0)

    # r_i: si hay un repartidor saliendo de i
    for i in range(n):
        nombres.append(f"r_{i}")
        costos.append(0.0)  # sin costo adicional por contratar repartidor
        tipos.append("B")
        lb.append(0.0)
        ub.append(1.0)

    prob.variables.add(
        obj=costos,
        lb=lb,
        ub=ub,
        types=tipos,
        names=nombres
    )

def agregar_restricciones(prob, instancia):
    n = instancia.cantidad_clientes
    dmax = instancia.d_max
    refrigerados = set(instancia.refrigerados)
    exclusivos = set(instancia.exclusivos)

    # 1. Cada cliente debe ser atendido (por camión o repartidor)
    for j in range(n):
        ind = [prob.variables.get_indices(f"y_{j}")]
        val = [1]

        for i in range(n):
            if i != j and instancia.distancias[i][j] <= dmax:
                try:
                    ind.append(prob.variables.get_indices(f"z_{i}_{j}"))
                    val.append(1)
                except:
                    pass  # z_{i,j} no está definida porque dist > dmax

        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=ind, val=val)],
            senses=["E"],
            rhs=[1],
            names=[f"atencion_cliente_{j}"]
        )

    # 2. Si hay un z_{i,j} activo, entonces y_i debe ser 1 (i.e., repartidor solo sale de la parada del camión)
    for i in range(n):
        for j in range(n):
            if i != j and instancia.distancias[i][j] <= dmax:
                try:
                    z_idx = prob.variables.get_indices(f"z_{i}_{j}")
                    y_idx = prob.variables.get_indices(f"y_{i}")
                    prob.linear_constraints.add(
                        lin_expr=[cplex.SparsePair(ind=[z_idx, y_idx], val=[1, -1])],
                        senses=["L"],
                        rhs=[0],
                        names=[f"repartidor_desde_parada_{i}_{j}"]
                    )
                except:
                    pass

    # 3. Refrigerados: como máximo 1 cliente refrigerado a pie/bici por parada
    for i in range(n):
        ind = []
        for j in refrigerados:
            if i != j and instancia.distancias[i][j] <= dmax:
                try:
                    ind.append(prob.variables.get_indices(f"z_{i}_{j}"))
                except:
                    pass
        if ind:
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=ind, val=[1] * len(ind))],
                senses=["L"],
                rhs=[1],
                names=[f"max_refrigerado_{i}"]
            )

    # 4. Clientes que deben ser visitados por el camión
    for i in exclusivos:
        idx = prob.variables.get_indices(f"y_{i}")
        prob.linear_constraints.add(
            lin_expr=[cplex.SparsePair(ind=[idx], val=[1])],
            senses=["E"],
            rhs=[1],
            names=[f"camion_visita_exclusivo_{i}"]
        )

   # 5. Si se contrata un repartidor en i, debe hacer al menos 4 entregas
    for i in range(n):
        ind = []
        val = []

        for j in range(n):
            if i != j and instancia.distancias[i][j] <= dmax:
                try:
                    ind.append(prob.variables.get_indices(f"z_{i}_{j}"))
                    val.append(1)
                except:
                    pass

        if ind:
            try:
                r_idx = prob.variables.get_indices(f"r_{i}")
                ind.append(r_idx)
                val.append(-4)
                prob.linear_constraints.add(
                    lin_expr=[cplex.SparsePair(ind=ind, val=val)],
                    senses=["G"],
                    rhs=[0],
                    names=[f"min_4_entregas_r_{i}"]
                )
            except:
                pass

    # 6. Solo puede haber repartidor si el camión paró
    for i in range(n):
        try:
            r_idx = prob.variables.get_indices(f"r_{i}")
            y_idx = prob.variables.get_indices(f"y_{i}")
            prob.linear_constraints.add(
                lin_expr=[cplex.SparsePair(ind=[r_idx, y_idx], val=[1, -1])],
                senses=["L"],
                rhs=[0],
                names=[f"repartidor_si_camion_para_{i}"]
            )
        except:
            pass

def armar_lp(prob, instancia):

    # Agregar las variables
    agregar_variables(prob, instancia)
   
    # Agregar las restricciones 
    agregar_restricciones(prob, instancia)

    # Setear el sentido del problema
    prob.objective.set_sense(prob.objective.sense.minimize)

    # Escribir el lp a archivo
    prob.write('recorridoMixto.lp')

def resolver_lp(prob):
    # Parámetros del solver (algunos son opcionales)
    prob.parameters.timelimit.set(60)  # Máximo 60 segundos
    prob.parameters.mip.tolerances.mipgap.set(0.01)  # 1% de gap
    prob.parameters.output.writelevel.set(0)  # Silencia la salida

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