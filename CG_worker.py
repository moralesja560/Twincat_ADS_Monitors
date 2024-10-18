import pyads
import sys
import os
from threading import Thread
from queue import Queue
import time
from datetime import datetime
import requests
import json
import pandas as pd
from dotenv.main import load_dotenv
import argparse
#import tensorflow as tf
#from sklearn.pipeline import Pipeline
#from sklearn.preprocessing import StandardScaler
import numpy as np
from urllib.request import Request, urlopen
import json
from urllib.parse import quote

load_dotenv()
token_Tel = os.getenv('API_KEY')
token_Tel2 = os.getenv('API_KEY2')
token_Tel = os.getenv('TOK_EN_BOT')
GIL = os.getenv('GIL')

def resource_path(relative_path):
 """ Get absolute path to resource, works for dev and for PyInstaller """
 base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
 return os.path.join(base_path, relative_path)

def My_Documents(location):
	import ctypes.wintypes
		#####-----This section discovers My Documents default path --------
		#### loop the "location" variable to find many paths, including AppData and ProgramFiles
	CSIDL_PERSONAL = location # My Documents
	SHGFP_TYPE_CURRENT = 0# Get current, not default value
	buf= ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
	ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
	#####-------- please use buf.value to store the data in a variable ------- #####
	#add the text filename at the end of the path
	temp_docs = buf.value
	return temp_docs

"""" Sends the Hour per Hour Report. """
def send_message(user_id, text,token):
	global json_respuesta
	url = f"https://api.telegram.org/{token}/sendMessage?chat_id={user_id}&text={text}"
	#resp = requests.get(url)
	#hacemos la petición
	try:
		#ruta_state = resource_path("images/tele.txt")
		#file_exists = os.path.exists(ruta_state)
		#if file_exists == False:
		#	return
		#else:
		respuesta  = urlopen(Request(url))
		#	pass
	except Exception as e:
		print(f"Ha ocurrido un error al enviar el mensaje: {e}")
	else:
		#recibimos la información
		cuerpo_respuesta = respuesta.read()
		# Procesamos la respuesta json
		json_respuesta = json.loads(cuerpo_respuesta.decode("utf-8"))
		print("mensaje enviado exitosamente")


def write_log(i_CG_err1,i_CG_err2,i_CG_err3,i_CG_broken,i_CG_disabled,i_CG_value):
	now = datetime.now()
	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
	#print("date and time =", dt_string)	
	mis_docs = My_Documents(5)
	pd_ruta = str(mis_docs)+ r"\registro_CG.csv"
	pd_file_exists = os.path.exists(pd_ruta)
	
	#check if pandas DataFrame exists to load the stuff or to create with dummy data.
	if pd_file_exists:
		pd_log = pd.read_csv(pd_ruta)
	else:
		pd_log = pd.DataFrame(pd_dict)
	

	new_row = {'timestamp' : [dt_string], 'ERROR_F1' : [i_CG_err1], 'ERROR_F2' : [i_CG_err2], 'ERROR_F3' : [i_CG_err3], 'BROKEN' : [i_CG_broken], 'DISABLED' : [i_CG_disabled], 'VALUE' : [i_CG_value]}
	new_row_pd = pd.DataFrame(new_row)
	pd_concat = pd.concat([pd_log,new_row_pd])
	pd_concat.to_csv(pd_ruta,index=False)


def write_log_pred(prediction,real):
	now = datetime.now()
	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
	#print("date and time =", dt_string)	
	mis_docs = My_Documents(5)
	pd_ruta = str(mis_docs)+ r"\registro_preds.csv"
	pd_file_exists = os.path.exists(pd_ruta)
	
	#check if pandas DataFrame exists to load the stuff or to create with dummy data.
	if pd_file_exists:
		pd_log = pd.read_csv(pd_ruta)
	else:
		pd_log = pd.DataFrame(pd_dict2)

	
	
	new_row = {'timestamp' : [dt_string], 'temp_pred' : [round(prediction,2)], 'temp_Real' : [real]}
	new_row_pd = pd.DataFrame(new_row)
	pd_concat = pd.concat([pd_log,new_row_pd])
	pd_concat.to_csv(pd_ruta,index=False)

	

def watchdog_t(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i):
	while True:
		stop_signal = input()
		if stop_signal == "T":
			PLC_1_queue_i.put(None)
			PLC_2_queue_i.put(None)
			shutdown_queue.put(None)
		break


def PLC_comms1(PLC_1_queue_i,PLC_1_queue_o,plc1_ip,plc1_netid):
	print('++++++++++++++++++++++++++++++++++ PLC1: Running')

	try:
		plc1=pyads.Connection(plc1_netid,801,plc1_ip)
		plc1.open()
		plc1.set_timeout(2000)

		CG_valor_handle = plc1.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

		CG_valor_max_handle = plc1.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
		CG_print_handle = plc1.get_handle('.TP_IW_Fehler_Circograph')	

		CG_label_put_handle = plc1.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

		CG_lot_handle = plc1.get_handle('.TP_IW_BatchNumber_STRING')
		CG_prod_handle = plc1.get_handle('.TP_IW_Gewicht')
		

	except Exception as e:
			print(f"Starting error 1: {e}")
			time.sleep(5)
			plc1,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle = aux_PLC_comms(plc1_ip,plc1_netid)
	while True:
		# get a unit of work
		try:
			item = PLC_1_queue_i.get(block=False)
		except:
			item='0000'
			pass

		# check for stop
		if item is None:
			#PLC release and break
			plc1.release_handle(CG_valor_handle)
			plc1.release_handle(CG_valor_max_handle)
			plc1.release_handle(CG_print_handle)
			plc1.release_handle(CG_label_put_handle)
			plc1.release_handle(CG_lot_handle)
			plc1.release_handle(CG_prod_handle)
			print(f"handles1 released")
			plc1.close()
			PLC_1_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			CG_valor= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_handle)
			CG_valor_max= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_max_handle)
			CG_printed= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_print_handle)
			CG_label_put= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_label_put_handle)
			CG_lot= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=CG_lot_handle)
			CG_prod= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_DINT,handle=CG_prod_handle)

			
			PLC_1_queue_o.put((CG_valor,CG_valor_max,CG_printed,CG_label_put,CG_lot,CG_prod))
			time.sleep(0.15)


		except Exception as e:
			print(f"Could not update in PLC1: error {e}")
			plc1,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle= aux_PLC_comms(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc1=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc1.open()
			CG_valor_handle = plc1.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

			CG_valor_max_handle = plc1.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
			CG_print_handle = plc1.get_handle('.TP_IW_Fehler_Circograph')	

			CG_label_put_handle = plc1.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

			CG_lot_handle = plc1.get_handle('.TP_IW_BatchNumber_STRING')
			CG_prod_handle = plc1.get_handle('.TP_IW_Gewicht')
		except:	
			print(f"Auxiliary PLC_1: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc1.open()
			print("Success PLC_L1")
			return plc1,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle

def PLC_comms2(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid):
	print('++++++++++++++++++++++++++++++++++ plc2: Running')

	try:
		plc2=pyads.Connection(plc2_netid,801,plc2_ip)
		plc2.open()
		plc2.set_timeout(2000)

		CG_valor_handle = plc2.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

		CG_valor_max_handle = plc2.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
		CG_print_handle = plc2.get_handle('.TP_IW_Fehler_Circograph')	

		CG_label_put_handle = plc2.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

		CG_lot_handle = plc2.get_handle('.TP_IW_BatchNumber_STRING')
		CG_prod_handle = plc2.get_handle('.TP_IW_Gewicht')
		

	except Exception as e:
			print(f"Starting error 2: {e}")
			time.sleep(5)
			plc2,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle = aux_PLC_comms2(plc2_ip,plc2_netid)
	while True:
		# get a unit of work
		try:
			item = PLC_2_queue_i.get(block=False)
		except:
			item='0000'
			pass

		# check for stop
		if item is None:
			#PLC release and break
			plc2.release_handle(CG_valor_handle)
			plc2.release_handle(CG_valor_max_handle)
			plc2.release_handle(CG_print_handle)
			plc2.release_handle(CG_label_put_handle)
			plc2.release_handle(CG_lot_handle)
			plc2.release_handle(CG_prod_handle)
			print(f"handles1 released")
			plc2.close()
			PLC_2_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			CG_valor= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_handle)
			CG_valor_max= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_max_handle)
			CG_printed= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_print_handle)
			CG_label_put= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_label_put_handle)
			CG_lot= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=CG_lot_handle)
			CG_prod= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_DINT,handle=CG_prod_handle)

			
			PLC_2_queue_o.put((CG_valor,CG_valor_max,CG_printed,CG_label_put,CG_lot,CG_prod))
			time.sleep(60)


		except Exception as e:
			print(f"Could not update in plc2: error {e}")
			plc2,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle= aux_PLC_comms2(plc2_ip,plc2_netid)
			continue


def aux_PLC_comms2(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc2=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc2.open()
			CG_valor_handle = plc2.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

			CG_valor_max_handle = plc2.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
			CG_print_handle = plc2.get_handle('.TP_IW_Fehler_Circograph')	

			CG_label_put_handle = plc2.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

			CG_lot_handle = plc2.get_handle('.TP_IW_BatchNumber_STRING')
			CG_prod_handle = plc2.get_handle('.TP_IW_Gewicht')
		except:	
			print(f"Auxiliary PLC_2: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc2.open()
			print("Success PLC_L2")
			return plc2,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle


def PLC_comms3(PLC_3_queue_i,PLC_3_queue_o,plc3_ip,plc3_netid):
	print('++++++++++++++++++++++++++++++++++ plc3: Running')

	try:
		plc3=pyads.Connection(plc3_netid,801,plc3_ip)
		plc3.open()
		plc3.set_timeout(2000)

		CG_valor_handle = plc3.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

		CG_valor_max_handle = plc3.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
		CG_print_handle = plc3.get_handle('.TP_IW_Fehler_Circograph')	

		CG_label_put_handle = plc3.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

		CG_lot_handle = plc3.get_handle('.TP_IW_BatchNumber_STRING')
		CG_prod_handle = plc3.get_handle('.TP_IW_Gewicht')
		

	except Exception as e:
			print(f"Starting error 3: {e}")
			time.sleep(5)
			plc3,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle = aux_PLC_comms3(plc3_ip,plc3_netid)
	while True:
		# get a unit of work
		try:
			item = PLC_3_queue_i.get(block=False)
		except:
			item='0000'
			pass

		# check for stop
		if item is None:
			#PLC release and break
			plc3.release_handle(CG_valor_handle)
			plc3.release_handle(CG_valor_max_handle)
			plc3.release_handle(CG_print_handle)
			plc3.release_handle(CG_label_put_handle)
			plc3.release_handle(CG_lot_handle)
			plc3.release_handle(CG_prod_handle)
			print(f"handles3 released")
			plc3.close()
			PLC_3_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			CG_valor= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_handle)
			CG_valor_max= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_valor_max_handle)
			CG_printed= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_print_handle)
			CG_label_put= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_INT,handle=CG_label_put_handle)
			CG_lot= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=CG_lot_handle)
			CG_prod= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_DINT,handle=CG_prod_handle)

			
			PLC_3_queue_o.put((CG_valor,CG_valor_max,CG_printed,CG_label_put,CG_lot,CG_prod))
			time.sleep(60)


		except Exception as e:
			print(f"Could not update in plc3: error {e}")
			plc3,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle= aux_PLC_comms3(plc3_ip,plc3_netid)
			continue


def aux_PLC_comms3(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc3=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc3.open()
			CG_valor_handle = plc3.get_handle('.TP_Prueftechnik_Flaw_Value_INT')

			CG_valor_max_handle = plc3.get_handle('.TP_Prueftechnik_Highest_Flaw_Value_INT')
			CG_print_handle = plc3.get_handle('.TP_IW_Fehler_Circograph')	

			CG_label_put_handle = plc3.get_handle('.TP_IW_Anzahl_Etiketten_Scan')

			CG_lot_handle = plc3.get_handle('.TP_IW_BatchNumber_STRING')
			CG_prod_handle = plc3.get_handle('.TP_IW_Gewicht')
		except:	
			print(f"Auxiliary PLC_3: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc3.open()
			print("Success PLC_L3")
			return plc3,CG_valor_handle,CG_valor_max_handle,CG_print_handle,CG_label_put_handle,CG_lot_handle,CG_prod_handle






def weather_data(PLC_5_queue_i,PLC_5_queue_o):
	print('++++++++++++++++++++++++++++++++++ Weather_Report: Running')
	# base URL
	#lat=26.8802393&lon=-101.4611757
	BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
	#LAT
	#CITY = "Saltillo"
	LAT = '26.8802393'
	LON = '-101.4611757'
	# API key 
	API_KEY = token_Tel
	offset=0
	prev_temp = 0
	prev_hum = 0
	prev_pressure = 0

	while True:
		try:
			item5 = PLC_5_queue_i.get(block=False)
		except:
			item5='0000'
		if item5 is None:
			print("Weather closing")
			break

		offset +=1
		if offset % 4 ==0 or offset ==1:
			# HTTP request
			# upadting the URL
			URL = BASE_URL + "lat=" + LAT + "&lon=" + LON + "&appid=" + API_KEY
			response = []
			try:
				response = requests.get(URL)
			except:
				print("Error connecting to weather service")
				time.sleep(2)
				continue
			else:
				# checking the status code of the request
				if response.status_code == 200:
					data = []
					# getting data in the json format
					data = response.json()
					# getting the main dict block
					main = data['main']
					# getting temperature
					temperature = main['temp']
					# getting the humidity
					humidity = main['humidity']
					# getting the pressure
					pressure = main['pressure']
					# weather report
					report = data['weather']
					prev_temp = 0
					prev_hum = 0
					prev_temp = temperature
					prev_hum = humidity
					#print("updated weather")
				else:
					data = []
					temperature = 0
					humidity =0 
					prev_temp = 0
					prev_hum = 0
					# showing the error message
					print("Error in the HTTP request")
					if API_KEY == token_Tel:
						API_KEY = token_Tel2
					else:
						API_KEY = token_Tel
					time.sleep(2)
					continue
		
				PLC_5_queue_o.put((prev_temp,prev_hum))
				print(f"{prev_temp,prev_hum}")
				time.sleep(4)



def process_coordinator():

	i_CG_valor1,i_CG_valor_max1,i_CG_printed1,i_CG_put1,i_CG_lot1,i_GC_prod1 = 0,0,0,0,'s',0
	i_CG_valor2,i_CG_valor_max2,i_CG_printed2,i_CG_put2,i_CG_lot2,i_GC_prod2 = 0,0,0,0,'s',0
	i_CG_valor3,i_CG_valor_max3,i_CG_printed3,i_CG_put3,i_CG_lot3,i_GC_prod3 = 0,0,0,0,'s',0
	
	while True:
		
		
		time.sleep(5)
		try:
			item = shutdown_queue.get(block=False)
		except:
			pass
		else:
			if item == None:
				print("Closing thread")
				shutdown_queue.task_done()
				break
		if PLC_1_queue_o.qsize()>0:
			i_CG_valor1,i_CG_valor_max1,i_CG_printed1,i_CG_put1,i_CG_lot1,i_GC_prod1 = PLC_1_queue_o.get(block=False)
			PLC_1_queue_o.task_done()
		print(f"recibido de L1: {PLC_1_queue_o.qsize()}")
		
		
		if PLC_2_queue_o.qsize()>0:
			i_CG_valor2,i_CG_valor_max2,i_CG_printed2,i_CG_put2,i_CG_lot2,i_GC_prod2 = PLC_2_queue_o.get(block=False)
			PLC_2_queue_o.task_done()
			print(f"recibido de L2: {PLC_2_queue_o.qsize()}")
		
		if PLC_3_queue_o.qsize()>0:
			i_CG_valor3,i_CG_valor_max3,i_CG_printed3,i_CG_put3,i_CG_lot3,i_GC_prod3 = PLC_3_queue_o.get(block=False)
			PLC_3_queue_o.task_done()
			print(f"recibido de L3: {PLC_3_queue_o.qsize()}")
		"""
		if PLC_4_queue_o.qsize()>0:
			i_temp_torre,i_bomba1,i_bomba2 = PLC_4_queue_o.get(block=hilo_block)
			PLC_4_queue_o.task_done()
			print("recibido de L4")
		
		if PLC_5_queue_o.qsize()>0:
			i_temp,i_humidity = PLC_5_queue_o.get(block=hilo_block)
			PLC_5_queue_o.task_done()
			print("recibido de L5")
		"""
		print(f"Info recibida: CG1{i_CG_valor1}, CG2{i_CG_valor2}, CG3{i_CG_valor3}")
		#print(f"Stats de las queue output {PLC_1_queue_o.qsize()}, {PLC_2_queue_o.qsize()},{PLC_3_queue_o.qsize()},{PLC_4_queue_o.qsize()},{PLC_5_queue_o.qsize()}")

		#if opt.save_data:
			#write_log(i_CG_err1,i_CG_err2,i_CG_err3,i_CG_broken,i_CG_disabled,i_CG_value)


if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--pred', action='store_true', help='Enable prediction mode')
	parser.add_argument('--save_data', action='store_true', help='write_log_enabled')
	parser.add_argument('--debug', action='store_true', help='write_log_enabled')
	
	
	opt = parser.parse_args()

	#send_message(GIL,quote(f"CG1 Software Working"),token_Tel)

	if opt.pred:
		#print(" +++++++++++++ MODO PREDICCION")
		#X_train = pd.read_csv(resource_path('resources\X_train_load.csv'),index_col=False)
		#scaler = StandardScaler()
		#X_train_scaled = scaler.fit_transform(X_train)
		#saved_model = tf.keras.models.load_model(resource_path('TF_model_prototipe'))
		#hilo_block=True
		pass
	#else
	#hilo_block = False


	pd_dict = {'timestamp' : ['0'], 'ERROR_F1' : ['0'], 'ERROR_F2' : ['0'], 'ERROR_F3' : ['0'], 'BROKEN' : ['0'], 'DISABLED' : ['0'], 'VALUE' : ['0']}


# The three queues:
	PLC_1_queue_i = Queue()
	PLC_2_queue_i = Queue()
	PLC_3_queue_i = Queue()
	PLC_4_queue_i = Queue()
	PLC_5_queue_i = Queue()

	PLC_1_queue_o = Queue()
	PLC_2_queue_o = Queue()
	PLC_3_queue_o = Queue()
	PLC_4_queue_o = Queue()
	PLC_5_queue_o = Queue()

	shutdown_queue = Queue()

	# Var definition:
	plc1_netid =  '10.65.96.73.1.1'
	plc2_netid =  '10.65.96.70.1.1'
	plc3_netid =  '10.65.96.88.1.1'
	plc1_ip =  '10.65.96.73'
	plc2_ip =  '10.65.96.70'
	plc3_ip =  '10.65.96.88'
	#plc_torre_ip = '10.65.68.130'
	
	
	try:
		plc0=pyads.Connection(plc1_netid,801,plc1_ip)
		plc0.open()
		plc0.close()
		print("PLC1 OK")
		plc0=pyads.Connection(plc2_netid,801,plc2_ip)
		plc0.open()
		plc0.close()		
		print("PLC2 OK")
		plc0=pyads.Connection(plc3_netid,801,plc3_ip)
		plc0.open()
		plc0.close()
		print("PLC3 OK")
	except:
		print("Failed to open ADS router, verify that you have installed TwinCAT")
		sys.exit()
		
	PLC_thread1 = Thread(name="hilo_PLC1",target=PLC_comms1, args=(PLC_1_queue_i,PLC_1_queue_o,plc1_ip,plc1_netid),daemon=True)
	PLC_thread2 = Thread(name="hilo_PLC2",target=PLC_comms2, args=(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid),daemon=True)
	PLC_thread3 = Thread(name="hilo_PLC3",target=PLC_comms3, args=(PLC_3_queue_i,PLC_3_queue_o,plc3_ip,plc3_netid),daemon=True)
	#PLC_thread4 = Thread(name="hilo_PLC4",target=PLC_comms4, args=(PLC_4_queue_i,PLC_4_queue_o,plc_torre_ip,plc_torre_netid),daemon=True)
	#weather_thread = Thread(name="clima",target=weather_data, args=(PLC_5_queue_i,PLC_5_queue_o),daemon=True)
	
	PLC_thread1.start()
	PLC_thread2.start()
	PLC_thread3.start()
	#PLC_thread4.start()
	#weather_thread.start()

	monitor_thread = Thread(target=watchdog_t, args=(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i),daemon=True)
	monitor_thread.start()

	process_coordinator()

	monitor_thread.join()
	PLC_thread1.join()
	PLC_thread2.join()
	PLC_thread3.join()
	#PLC_thread4.join()
	#weather_thread.join()

	