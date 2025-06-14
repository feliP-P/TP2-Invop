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

    prob.variables.add(
        obj=costos,
        lb=lb,
        ub=ub,
        types=tipos,
        names=nombres
    )

def agregar_restricciones(prob, instancia):
    # Agregar las restricciones ax <= (>= ==) b:
	# funcion 'add' de 'linear_constraints' con parametros:
	# lin_expr: lista de listas de [ind,val] de a
    # sense: lista de 'L', 'G' o 'E'
    # rhs: lista de los b
    # names: nombre (como van a aparecer en el archivo .lp)

    # Notar que cplex espera "una matriz de restricciones", es decir, una
    # lista de restricciones del tipo ax <= b, [ax <= b]. Por lo tanto, aun cuando
    # agreguemos una unica restriccion, tenemos que hacerlo como una lista de un unico
    # elemento.

    ...........

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
    
    # Definir los parametros del solver
    #prob.parameters.mip.....
       
    # Resolver el lp
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

    # Mostrar las variables con valor positivo (mayor que una tolerancia)
    ..... 

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