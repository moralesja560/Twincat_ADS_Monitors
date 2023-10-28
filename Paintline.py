import pyads
import sys
import threading
import time
import sys
from dotenv import load_dotenv
import os
from urllib.request import Request, urlopen
import json
from urllib.parse import quote
import datetime
import csv
import pandas as pd
from datetime import datetime

load_dotenv()
token_Tel = os.getenv('TOK_EN_BOT')
Jorge_Morales = os.getenv('JORGE_MORALES')

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def My_Documents(location):
	import ctypes.wintypes
		#####-----This section discovers My Documents default path --------
		#### loop the "location" variable to find many paths, including AppData and ProgramFiles
	CSIDL_PERSONAL = location       # My Documents
	SHGFP_TYPE_CURRENT = 0   # Get current, not default value
	buf= ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
	ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
	#####-------- please use buf.value to store the data in a variable ------- #####
	#add the text filename at the end of the path
	temp_docs = buf.value
	return temp_docs

def send_message(user_id, text,token):
	global json_respuesta
	url = f"https://api.telegram.org/{token}/sendMessage?chat_id={user_id}&text={text}"
	#resp = requests.get(url)
	#hacemos la petición
	try:
		respuesta  = urlopen(Request(url))
	except Exception as e:
		print(f"Ha ocurrido un error al enviar el mensaje: {e}")
	else:
		#recibimos la información
		cuerpo_respuesta = respuesta.read()
		# Procesamos la respuesta json
		json_respuesta = json.loads(cuerpo_respuesta.decode("utf-8"))
		print("mensaje enviado exitosamente")

def state_recover():
	ruta_state = resource_path("images/last_state.csv")
	file_exists = os.path.exists(ruta_state)
	if file_exists == True:
		pass
	else:
		with open(ruta_state,"w+") as f:
			f.write(f"{int(0)},{int(0)}")		

	with open(resource_path("images/last_state.csv")) as file:
		type(file)
		csvreader = csv.reader(file)
		rows2 = []
		for row in csvreader:
			rows2.append(row)
		
		fmb46_state = int(rows2[0][0])
		hora = int(rows2[0][1])

		return fmb46_state,hora

def state_save(fmb46_state,hora):
	ruta_state = resource_path("images/last_state.csv")

	with open(ruta_state, "w+") as file_object:

		file_object.write(f"{fmb46_state},{hora}")

##--------------------the thread itself--------------#

class hilo1(threading.Thread):
	#thread init procedure
	# i think we pass optional variables to use them inside the thread
	def __init__(self):
		threading.Thread.__init__(self)
		self._stop_event = threading.Event()
	#the actual thread function
	def run(self):
		#arranca los datos guardados
		contador_gancheras,hora = state_recover()
		state_hanger = False

		#inicialización de PLC
		plc.open()
		var_handle46_1 = plc.get_handle('.I_Hang_Counter')
		while True:
			try:
				#sensor
				cell1 = plc.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=var_handle46_1)
			except Exception as e:
				#send_message(Jorge_Morales,quote(f"Falla de app: {e}. Si es el 1861, por favor conectarse al PLC via Twincat System Manager. Con eso se hace la conexión ADS"),token_Tel)
				print(e)
				plc.release_handle(var_handle46_1)
				plc.close()
				break
			else:

				if state_hanger != cell1:		
					write_log(cell1)
					print(cell1)
					state_hanger = cell1
					if cell1 == True:
						contador_gancheras +=1
						print("guardado")
						state_save(contador_gancheras,hora)
						#if (contador_gancheras % 100) == 0:
						#	send_message(Jorge_Morales,quote(f"Reporte de gancheras: {contador_gancheras}"),token_Tel)
				#hourly report
				now = datetime.now()
				if hora != int(now.strftime("%H")):
					if int(hora) <= 20 and int(hora) >= 7:
						send_message(Jorge_Morales,quote(f"Reporte de Hora: {hora}-{hora+1}: {contador_gancheras}"),token_Tel)
					#reset a la variable
					contador_gancheras = 0
					#se actualiza la hora
					hora = int(now.strftime("%H"))
				

			if self._stop_event.is_set():
				# close connection
				print("saliendo")
				plc.release_handle(var_handle46_1)
				plc.close()
				break
	def stop(self):
		self._stop_event.set()

	def stopped(self):
		return self._stop_event.is_set()
#----------------------end of thread 1------------------#

#---------------Thread 2 Area----------------------#
class hilo2(threading.Thread):
	#thread init procedure
	# i think we pass optional variables to use them inside the thread
	def __init__(self,thread_name,opt_arg):
		threading.Thread.__init__(self)
		self.thread_name = thread_name
		self.opt_arg = opt_arg
		self._stop_event = threading.Event()
	#the actual thread function
	def run(self):
		#check for thread1 to keep running
		while True:
			if [t for t in threading.enumerate() if isinstance(t, hilo1)]:
				try:
					time.sleep(5)
				except:
					self._stop_event.set()
			else:
				print(f"A problem occurred... Restarting Thread 1")
				time.sleep(4)
				thread1 = hilo1()
				thread1.start()
				print(f"Thread 1 Started")
			
			if self._stop_event.is_set() == True:
				print("Thread 2 Stopped")
				break

	def stop(self):
		self._stop_event.set()

def write_log(cell1):
	now = datetime.now()
	dt_string = now.strftime("%d/%m/%Y %H:%M:%S.%f")
	#print (dt_string)
	#print("date and time =", dt_string)	
	mis_docs = My_Documents(5)
	ruta = str(mis_docs)+ r"\paintline.txt"
	pd_ruta = str(mis_docs)+ r"\paintline_df.csv"
	file_exists = os.path.exists(ruta)
	pd_file_exists = os.path.exists(pd_ruta)
	if file_exists == True:
		with open(ruta, "a+") as file_object:
			# Move read cursor to the start of file.
			file_object.seek(0)
			# If file is not empty then append '\n'
			data = file_object.read(100)
			if len(data) > 0 :
				file_object.write("\n")
				file_object.write(f" timestamp {dt_string}: Cell1: {cell1}")
	else:
		with open(ruta,"w+") as f:
				f.write(f" timestamp {dt_string}: Cell1: {cell1}")

	#check if pandas DataFrame exists to load the stuff or to create with dummy data.
	if pd_file_exists:
		pd_log = pd.read_csv(pd_ruta)
	else:
		pd_log = pd.DataFrame(pd_dict)

	new_row = {'timestamp' : [dt_string], 'Cell1' : [cell1]}
	new_row_pd = pd.DataFrame(new_row)
	pd_concat = pd.concat([pd_log,new_row_pd])
	pd_concat.to_csv(pd_ruta,index=False)


#Pandas DataFrame dictionaries
pd_dict = {'timestamp' : ['dummy'], 'Cell1' : ['dummy']}



if __name__ == '__main__':

	# connect to the PLC
	try:
		pyads.open_port()
		ams_net_id = pyads.get_local_address().netid
		print(ams_net_id)
		pyads.close_port()
		plc=pyads.Connection('10.65.96.185.1.1', 801, '10.65.96.185')
	except:
		print("No se pudo abrir la conexión")
		sys.exit()
	 #open the connection
	else:
		pass
	thread1 = hilo1()
	thread1.start()
	thread2 = hilo2(thread_name="hilo2",opt_arg="h")
	thread2.start()
	while True:
		stop_signal = input()
		if stop_signal == "T":
			thread1.stop()
			thread2.stop()
		break