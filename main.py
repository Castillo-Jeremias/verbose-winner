# This Python file uses the following encoding: utf-8
# Developed by Jeremías Castillo

# Modulo que permite la incorporación de timers.
import time

# Modulo que incorpora utilidades para comunicación serie.
import serial

# Modulo "os" brinda utilidades vinculadas con el sistema operativo de la computadora
# Modulo "datetime" contiene funciones vinculadas fechas.
# Modulo "getpass" brinda funciones para acceder a datos del usuario del sistema que corre el código (nombre)
# Modulo "sys" contiene funciones que se encarga del estado de la aplicación, entre otras cosas...

import os
import sys
import datetime
import getpass
import serial.tools.list_ports

from pathlib import Path

from PySide2.QtGui import QGuiApplication
from PySide2.QtQml import QQmlApplicationEngine
from PySide2.QtCore import QObject, Signal, Slot, QTimer, QUrl
from datetime import datetime

# ---------- Nombre de usuario de la computadora para poder crear archivo de LOG --------------
Name_User = getpass.getuser()

# ---------- Ruta por defecto para almacenar el archivo de LOG auto guardado --------------
DEFAULT_URL_LOG = "file:///C:/Users/"+Name_User+"/Desktop/Ground_Station_Log.txt"

# ---------- Auto guardado cada 60 seg (Si hay cambios) --------------
Tiempo_AutoSave = 60000

# ---------- Timer de chequeo de puerto serie cada 15 seg --------------
Tiempo_Check_Ports = 15000

# ---------- Timer de chequeo de tracking cada 60 seg --------------
Tiempo_Tracking = 60000

# ---------- Timer de actualizacion de graficos cada 30 seg --------------
#Tiempo_Actualizacion_Graf = 30000

# ---------- Conexión con el puerto serie --------------
#Serial_PORT = serial.Serial()
Flag_recep = False
data_acimut = -99       # Valor no valido
data_elevacion = -99    # Valor no valido

# ======================================== TO DO ======================================== #
'''
   Nota: Mientra más asteriscos tengo más importante es la cosa


    * Modificar la función statusPortCOM de manera que solo modifique el color (signal to frontend) cuando se detecte que
     el puerto serie "desaparecio". Hay que sacar todos los comentarios y esas boludeces más que nada. (*DONE*)

    ** Continuación con la parte gráfica, borrar la pestaña de settings y colocar una pestaña de ayuda para generar el 
        el archivo de texto y color medianamente hacer las cosas para no manquearla.
    
    ** Definir como hacer la parte del stop del tracking enviado por la parte gráfica.

    *** Testar la recepción de datos del MCU y el envió a la PC ante una solicitud de ángulos
'''
# ======================================================================================= #
class VentanaPrincipal(QObject):

    # String que almacena datos enviados desde la ventana de LOG
    DataToSave = ""

    # String que almacena datos enviados desde la ventana de LOG
    DataSaved = ""

    # ======================================== Señales a emitir ======================================== #

    # Creación de la señal que se encarga de actualizar datos en la interface cada 1 segundo, no envia datos. (podría hacerlo)
    actualizarDataToSave = Signal()

    # Señal enviada a la UI para notificar que los datos fueron guardados y puede borrar lo que tenga el LOG
    cleanLogAvalible = Signal()

    # Señal donde se envia el puerto serie a la UI
    setPortCOM = Signal(str)

    #Señal de error de envio por puerto serie
    commSerieFailed = Signal(str)

    # Señal de actualizacion de los grados graficos
    #Actual_graf_grados_signal = Signal(str,str)

    # Señal simple (envió de string) hacia la parte gráfica de la aplicación
    signal_To_FrontEnd = Signal(str, str)

    # ==================================== Fin de señales a emitir ==================================== #

    def __init__(self):
        QObject.__init__(self)

        self.timerautosave = QTimer()
        self.timercheckports = QTimer()
        self.timertracking = QTimer()
        #self.timer_actual_graf = QTimer()

        # Ejecución de Actualizar_Interface cada vez que desborde el timer
        self.timerautosave.timeout.connect(lambda: self.autoGuardadoLog())

        # Chequeo de status de puerto de comunicaciones
        self.timercheckports.timeout.connect(lambda: self.statusPortCOM())

        # Ejecución de tracking
        self.timertracking.timeout.connect(lambda: self.Control_autonomo())

        # Ejecucion de actualizacion grafica grados
        #self.timer_actual_graf.timeout.connect(lambda: self.Actualizacion_Grafica_Grados())

        # Recarga de timer asociados
        self.timerautosave.start(Tiempo_AutoSave)
        self.timercheckports.start(Tiempo_Check_Ports)
        self.timertracking.start(Tiempo_Tracking)
        #self.timer_actual_graf.start(Tiempo_Actualizacion_Graf)

    # No es necesario un slot por que no recibimos datos desde UI, ni tampoco una signal dado que no mandamos nada
    # La lógica de esta combinación es necesaria ya que si no puede generarse discrepancia de los datos guardados.

    # Orden de ejecución:
    #  - Timer desborda -> Ejecuta autoGuardadoLog()
    #  - autoGuardadoLog -> Envia signal a la UI
    #  - UI responde y ejecuta saveDataLog() Y si hay datos distintos en el LOG
    #  de los que ya se tenian en un princpio en DataToSave se guardan

    def autoGuardadoLog(self):
        self.actualizarDataToSave.emit()
        if(self.DataSaved != self.DataToSave):
            file = open(QUrl(DEFAULT_URL_LOG).toLocalFile(), "a")
            file.write(self.DataToSave + "\n")
            self.DataSaved = self.DataToSave
            file.close()
            print("saved")

    @Slot(str)
    def saveDataLog(self,dataLog):
        if(self.DataToSave != dataLog):
            self.DataToSave = dataLog

    # Guardado de LOG en una dirección determinada por el usuario a gusto.
    @Slot(str)
    def saveFile(self,filePath):
        file = open(QUrl(filePath).toLocalFile(), "a")
        file.write(self.DataToSave)
        file.close()

    @Slot(str)
    def openFile(self,filePath):
      file = open(QUrl(filePath).toLocalFile(), "r")
      Data = file.readlines()
      print(Data)
      print(type(Data))
      file.close()
    #############################################################################################################
    # Hay diferencia entre el autoGuardadoLog() y cleanLog() ya que aca la ejecución de esta última esta función
    # es por la UI y en el caso anterior se necesita saber desde la UI cuando desborda el Timer,
    # por ello se utiliza la signal en la primera.
    #############################################################################################################

    @Slot(str)
    def cleanLog(self, dataReadLog):
        if(dataReadLog != self.DataToSave):
            file = open(QUrl(DEFAULT_URL_LOG).toLocalFile(), "a")
            file.write(dataReadLog + "\n")
            file.close()
            print("Limpiando ventana de LOG")

        self.cleanLogAvalible.emit()

    #############################################################################################################
    #                                    Actualizacion grafica de los grados                                   #
    #############################################################################################################

    @Slot()
    def Actualizacion_Grafica_Grados(self):

        if Serial_PORT.in_waiting > 0:  # if incoming bytes are waiting to be read from the serial input buffer
            Data_From_MCU = Serial_PORT.read(Serial_PORT.inWaiting()).decode('ascii')  # read the bytes and convert from binary array to ASCII
            Data_Angulos = Data_From_MCU.split(',')

            if Data_Angulos[len(Data_Angulos)-1] == "\r\n":
                if (Data_Angulos[0] == ("A" or "a")) and (Data_Angulos[2] == ("E" or "e")):
                    Raw_acimut = Data_Angulos[1]
                    Raw_elevacion = Data_Angulos[3]
                    self.Actual_graf_grados_signal.emit(Raw_acimut,Raw_elevacion)

    def Recepcion_datos(self):
        if Serial_PORT.in_waiting > 0:  # if incoming bytes are waiting to be read from the serial input buffer

            Data_From_MCU = Serial_PORT.read(Serial_PORT.inWaiting()).decode('ascii')  # read the bytes and convert from binary array to ASCII

            if Data_From_MCU == '\r\n':
                return 1
            elif Data_From_MCU == "?>\r\n":
                return 0
            else:
                return -1   # Levantamos verdura (Podríamos usarlo para debugear nosotros y ver que hacer si pasa en un futuro)

    #############################################################################################################
    #                                   Fin funciones de puerto serie                                           #
    #############################################################################################################

    #############################################################################################################
    #                                    Funciones de puerto serie                                              #
    #############################################################################################################

    def statusPortCOM(self):
        # Deben de ser ingresado en formato hexadecimal (sin 0x), sino no podran ser encontrados
        # ID: 0x6860 (o ID: 27620) -> 6860 (HEXADECIMAL)
        list_PID = ['6860','6001']
        list_VID = ['04E8','0403']

        # Recorremos la lista de PID ingresados
        for Index in range(len(list_PID)):

            # Procedemos a buscar el dispositivo que contenga PID en su descriptor de HW
            # Si la lista es de longitud distinta de cero es por que hay un dispositivo que matcheo con el PID ingresado
            Device_To_Found = list(serial.tools.list_ports.grep(list_VID[Index] + ':' + list_PID[Index]))

            if (len(Device_To_Found) != 0):
                for USB_Port in list(serial.tools.list_ports.grep(list_VID[Index] + ':' + list_PID[Index])):
                    print('\n* =================================== Puerto Encontrado =================================== *')
                    print('\t\t\tCOM Utilizado: ' + USB_Port.device)
                    VID = '0x' + USB_Port.hwid[12:16]
                    PID = '0x' + USB_Port.hwid[17:21]
                    print('\t\t\tVID: ' + VID)
                    print('\t\t\tPID: ' + PID)
                    print('\t\t\t' + USB_Port.description)
                    print('* ========================================================================================= *')
                    if (VID == '0x0403' and PID == '0x6001'):  # Parche para que no genere bardo con mi telefono xd
                        try:
                            if(Serial_PORT.is_open == False):
                                print("Intentando Conectar con " + USB_Port.device + "...")
                                Serial_PORT.port = USB_Port.device
                                #Serial_PORT.port = "COM2"  # Debug con termite y VSPE para virtualizar puertos
                                Serial_PORT.baudrate = 9600
                                Serial_PORT.open()
                                print("¡" + USB_Port.device + " Conectado Correctamente!")
                                self.signal_To_FrontEnd.emit("USB","Good")
                        except(serial.SerialException):
                            if(Serial_PORT.is_open == True):
                                print("* ==== Error ==== * - Se Detecto un Problema en el Puerto " + USB_Port.device + "Cuyo VID:PID es 0x" + list_VID[Index] + ":0x" + list_PID[Index])
                                self.signal_To_FrontEnd.emit("USB","Problem")
                                Serial_PORT.close()
                            if(Serial_PORT.is_open == False):
                                print("* ==== Error ==== * - El Puerto " + USB_Port.device + "no se Encuentra Abierto...")
                                self.signal_To_FrontEnd.emit("USB","Bad")
            else:
                print('\n* =================================== Notificación =================================== *')
                print("\t No se Encontro Ningún Dispositivo Cuyo par VID:PID sea 0x" + list_VID[Index] + ':0x' + list_PID[Index])
                print('* =================================================================================== *')
                if(Serial_PORT.is_open == True):
                    self.signal_To_FrontEnd.emit("USB","Bad")
                    Serial_PORT.close()

    #############################################################################################################
    #                                   Fin funciones de puerto serie                                           #
    #############################################################################################################

    #############################################################################################################
    #                                      Comando manuales                                                     #
    #############################################################################################################

    # U // UP Direction Rotation
    @Slot()
    def moveUp(self):
        #comando a enviar: "U\r"
        texto = b'U\r'
        try:
            Serial_PORT.write(texto)
        except(serial.SerialException):
            self.commSerieFailed.emit("[Mov. Arriba]: Falla de Envió por Puerto Serie")
            self.signal_To_FrontEnd.emit("USB","Bad")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Mov. Arriba]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    # D // DOWN Direction Rotation
    @Slot()
    def moveDown(self):
        #comando a enviar: "D\r"
        texto = b'D\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Mov. Abajo]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Mov. Abajo]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    #R // Clockwise Rotation
    @Slot()
    def moveToRight(self):
        #comando a enviar: "R\r"
        texto = b'R\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Mov. Drcha]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Mov. Drcha]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    #L// Counter Clockwise Rotation
    @Slot()
    def moveToLeft(self):
        #comando a enviar: "L\r"
        texto = b'L\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Mov. Izq]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Mov. Izq]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    # A // CW/CCW Rotation Stop
    @Slot()
    def stopAcimut(self):
        #comando a enviar: "A\r"
        texto = b'A\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Stop Acimut]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Stop Acimut]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    # E // UP/DOWN Direction Rotation Stop
    @Slot()
    def stopElevacion(self):
        #comando a enviar: "E\r"
        texto = b'E\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Stop Elevación]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Stop Elevación]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    # E // UP/DOWN Direction Rotation Stop
    @Slot()
    def stopEverthing(self):
        #comando a enviar: "S\r"
        texto = b'S\r'
        try:
           Serial_PORT.write(texto)
           self.signal_To_FrontEnd.emit("USB","Good")
        except(serial.SerialException):
           self.commSerieFailed.emit("[Stop Global]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB", "Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Stop Global]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")

    #############################################################################################################
    #                                         Fin comando manuales                                              #
    #############################################################################################################

    #############################################################################################################
    #                                   Funciones vinculadas con el tracking                                    #
    #############################################################################################################

    def Control_autonomo(self):
       global data_acimut
       global data_elevacion
       global Flag_Enable_Send

       hora_actual = time.strftime('%H:%M')
       """ -------- Solicito fecha y la genero al formato para comparar con el archivo ----------"""
       fecha_sin_analizar = time.strftime('%m/%d/%y')
       objDate = datetime.strptime(fecha_sin_analizar,'%m/%d/%y')
       fecha = datetime.strftime(objDate, '%Y-%b-%d')

       try:
           file = open("comandos4.txt",'r')
       except:
           print("No Se Encontro el Archivo de Comandos")
           file.close()
           return
       else:
           total_lines = sum(1 for line in file)
           file.seek(0)

       linea = file.readline()
       while len(linea) > 0:
           dato1 = linea.split(',')
           if dato1[0] != '\n':
               if fecha == dato1[0] and dato1[1] == hora_actual:
                  data_acimut = dato1[2]
                  data_elevacion = dato1[3]
                  parametros = "P" + str(float(dato1[2])) + " " + str(float(dato1[3]))
                  Serial_PORT.write(parametros.encode('ascii')+ b'\r')
                  if self.Recepcion_datos() == 1:
                      self.signal_To_FrontEnd.emit("Tracking", "Good")
                      file.close()
                      break
                  elif self.Recepcion_datos() == 0:
                      self.signal_To_FrontEnd.emit("Tracking", "Problem")
                      file.close()
                      break
           elif dato1[0] == '':     # Fin de archivo detectado
                   self.signal_To_FrontEnd.emit("Tracking","Off")
                   file.close()
           linea = file.readline()
    #############################################################################################################
    #                                   Fin funciones vinculadas con el tracking                                #
    #############################################################################################################

    #############################################################################################################
    #                                 Funciones vinculadas con solicitud de ángulos                             #
    #############################################################################################################

    def Actualizacion_Posicion(self):
        #comando a enviar: "B\r"
        texto = b'B\r'
        try:
           Serial_PORT.write(texto)
        except(serial.SerialException):
           self.commSerieFailed.emit("[Act. Posición]: Falla de Envió por Puerto Serie")
           self.signal_To_FrontEnd.emit("USB","Problem")
        else:
            if(self.Recepcion_datos() == 1):
                self.signal_To_FrontEnd.emit("USB","Good")
            elif(self.Recepcion_datos() == 0):
                self.commSerieFailed.emit("[Act. Posición]: Comando No Renocido")
                self.signal_To_FrontEnd.emit("USB","Problem")
    #############################################################################################################
    #                                 Fin funciones vinculadas con solicitud de ángulos                         #
    #############################################################################################################

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    #Obtención del contexto del objeto desde la interface gráfica
    ventana = VentanaPrincipal()
    engine.rootContext().setContextProperty("backendPython",ventana)

    #Carga del archivo QML
    engine.load(os.fspath(Path(__file__).resolve().parent / "qml\main.qml"))

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec_())
