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
from urllib.parse import quote
load_dotenv()
token_trays = os.getenv('TRAYS')
token_Tel = os.getenv('TOK_EN_BOT')


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


def send_message(user_id, text,token):
	if opt.noTele:
		print("CNS: Disable Consumer Messaging Service")
		return
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


def write_log(L1_qty_hr,L1_qty_dai,L1_tests_hr,L1_tests_dai,L2_qty_hr,L2_qty_dai,L2_tests_hr,L2_tests_dai):
	now = datetime.now()
	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
	#print("date and time =", dt_string)	
	mis_docs = My_Documents(5)
	pd_ruta = str(mis_docs)+ r"\registro_trays.csv"
	pd_file_exists = os.path.exists(pd_ruta)
	
	#check if pandas DataFrame exists to load the stuff or to create with dummy data.
	if pd_file_exists:
		pd_log = pd.read_csv(pd_ruta)
	else:
		pd_log = pd.DataFrame(pd_dict)
	

	new_row = {'timestamp' : [dt_string], 'L1_qty_hr' : [L1_qty_hr],'L1_qty_dai' : [L1_qty_dai],'L1_tests_hr' : [L1_tests_hr],'L1_tests_dai' : [L1_tests_dai], 'L2_qty_hr' : [L2_qty_hr],'L2_qty_dai' : [L2_qty_dai],'L2_tests_hr' : [L2_tests_hr],'L2_tests_dai' : [L2_tests_dai]}

	new_row_pd = pd.DataFrame(new_row)
	pd_concat = pd.concat([pd_log,new_row_pd])
	pd_concat.to_csv(pd_ruta,index=False)



def watchdog_t(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i):
	while True:
		stop_signal = input()
		if stop_signal == "T":
			PLC_1_queue_i.put((None,None))
			PLC_2_queue_i.put((None,None))
			shutdown_queue.put(None)
		break


def PLC_comms1(PLC_1_queue_i,PLC_1_queue_o,plc1_ip,plc1_netid):
	print('++++++++++++++++++++++++++++++++++ PLC1: Running')
	try:
		plc1=pyads.Connection(plc1_netid,801,plc1_ip)
		plc1.open()
		plc1.set_timeout(2000)
		hr_counter_handle = plc1.get_handle('.Test_Trays_hour_UINT')
		dai_counter_handle = plc1.get_handle('.Test_Trays_dai_UINT')
		amount_test_dai_handle = plc1.get_handle('.Test_Sent_dai_UINT')
		amount_test_hr_handle = plc1.get_handle('.Test_Sent_hour_UINT')


	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc1,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms(plc1_ip,plc1_netid)
	while True:
		# get a unit of work
		try:
			item,item2 = PLC_1_queue_i.get(block=False)
		except:
			item='0000'
			item2 = '0000'
		else:
			if item == True:
				#Reset H vars
				plc1.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=hr_counter_handle)
				plc1.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_hr_handle)
			if item2 == True:
				#Reset D vars
				plc1.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=dai_counter_handle)
				plc1.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_dai_handle)

		# check for stop
		if item is None:
			#PLC release and break
			plc1.release_handle(hr_counter_handle)
			plc1.release_handle(dai_counter_handle)
			plc1.release_handle(amount_test_hr_handle)
			plc1.release_handle(amount_test_dai_handle)

			print(f"handles1 released")
			plc1.close()
			PLC_1_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			PLC_trays_hr = plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=hr_counter_handle)
			PLC_trays_dai = plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=dai_counter_handle)
			PLC_tests_hr = plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_hr_handle)
			PLC_tests_dai = plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_dai_handle)
			
			PLC_1_queue_o.put((PLC_trays_hr,PLC_trays_dai,PLC_tests_hr,PLC_tests_dai))
			time.sleep(90)


		except Exception as e:
			print(f"Could not update in PLC1: error {e}")
			plc1,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc1=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc1.open()
			hr_counter_handle = plc1.get_handle('.Test_Trays_hour_UINT')
			dai_counter_handle = plc1.get_handle('.Test_Trays_dai_UINT')
			amount_test_dai_handle = plc1.get_handle('.Test_Sent_dai_UINT')
			amount_test_hr_handle = plc1.get_handle('.Test_Sent_hour_UINT')
		except:	
			print(f"Auxiliary PLC_1: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc1.open()
			print("Success PLC_L1")
			return plc1,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle
		



def PLC_comms2(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid):
	print('++++++++++++++++++++++++++++++++++ plc2: Running')
	try:
		plc2=pyads.Connection(plc2_netid,801,plc2_ip)
		plc2.open()
		plc2.set_timeout(2000)
		hr_counter_handle = plc2.get_handle('.Test_Trays_hour_UINT')
		dai_counter_handle = plc2.get_handle('.Test_Trays_dai_UINT')
		amount_test_dai_handle = plc2.get_handle('.Test_Sent_dai_UINT')
		amount_test_hr_handle = plc2.get_handle('.Test_Sent_hour_UINT')


	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc2,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms2(plc2_ip,plc2_netid)
	while True:
		# get a unit of work
		try:
			item,item2 = PLC_2_queue_i.get(block=False)
		except:
			item='0000'
			item2 = '0000'
		else:
			if item == True:
				#Reset H vars
				plc2.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=hr_counter_handle)
				plc2.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_hr_handle)
			if item2 == True:
				#Reset D vars
				plc2.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=dai_counter_handle)
				plc2.write_by_name("", int(0), plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_dai_handle)

		# check for stop
		if item is None:
			#PLC release and break
			plc2.release_handle(hr_counter_handle)
			plc2.release_handle(dai_counter_handle)
			plc2.release_handle(amount_test_hr_handle)
			plc2.release_handle(amount_test_dai_handle)

			print(f"handles1 released")
			plc2.close()
			PLC_2_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			PLC_trays_hr = plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=hr_counter_handle)
			PLC_trays_dai = plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=dai_counter_handle)
			PLC_tests_hr = plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_hr_handle)
			PLC_tests_dai = plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=amount_test_dai_handle)
			
			PLC_2_queue_o.put((PLC_trays_hr,PLC_trays_dai,PLC_tests_hr,PLC_tests_dai))
			time.sleep(90)


		except Exception as e:
			print(f"Could not update in plc2: error {e}")
			plc2,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms2(plc2_ip,plc2_netid)
			continue


def aux_PLC_comms2(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc2=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc2.open()
			hr_counter_handle = plc2.get_handle('.Test_Trays_hour_UINT')
			dai_counter_handle = plc2.get_handle('.Test_Trays_dai_UINT')
			amount_test_dai_handle = plc2.get_handle('.Test_Sent_dai_UINT')
			amount_test_hr_handle = plc2.get_handle('.Test_Sent_hour_UINT')
		except:	
			print(f"Auxiliary PLC_1: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc2.open()
			print("Success PLC_L1")
			return plc2,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle




def process_coordinator():

	i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai,i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai = 0,0,0,0,0,0,0,0
	hour = 0
	dai = 0
	total_hr = 0
	received_1 = False
	received_2 = False
	now = datetime.now()
	hour = int(now.strftime("%H"))
	dai = int(now.strftime("%d"))

	while True:

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
			i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai = PLC_1_queue_o.get(block=False)
			PLC_1_queue_o.task_done()
			received_1 = True
			print("recibido de L1")
			
		if PLC_2_queue_o.qsize()>0:
			i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai = PLC_2_queue_o.get(block=False)
			PLC_2_queue_o.task_done()
			print("recibido de L2")
			received_2 = True


		print(f"Info recibida {i_L1_qty_hr} {i_L2_qty_hr} Remaining {PLC_1_queue_o.qsize()}/{PLC_2_queue_o.qsize()}")
	
		if opt.save_data and received_1 and received_2:
			write_log(i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai,i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai)
			received_2 = False
			received_1 = False

	
		now = datetime.now()

		if hour != int(now.strftime("%H")):
			
			total_hr = i_L1_qty_hr + i_L1_tests_hr + i_L2_qty_hr + i_L2_tests_hr

			if total_hr > 0:
				send_message(token_trays,quote(f" Reporte de Pruebas hora {hour}: \nL1 charolas: {i_L1_qty_hr} \nL1 pruebas: {i_L1_tests_hr} \n-- \nL2 charolas: {i_L2_qty_hr} \nL2 pruebas: {i_L2_tests_hr}"),token_Tel)
			
			send_message(token_trays,quote(f" Acumulado día: \nL1 charolas: {i_L1_qty_dai} \nL1 pruebas: {i_L1_tests_dai} \n** \nL2 charolas: {i_L2_qty_dai} \nL2 pruebas: {i_L2_tests_dai}"),token_Tel)
			# comando de borrado
			PLC_1_queue_i.put((True,False))
			PLC_2_queue_i.put((True,False))
			hour = int(now.strftime("%H"))

		if dai != int(now.strftime("%d")):
						# comando de borrado
			PLC_1_queue_i.put((True,True))
			PLC_2_queue_i.put((True,True))
			dai = int(now.strftime("%d"))

		time.sleep(60)




if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--save_data', action='store_true', help='write_log_enabled')
	parser.add_argument('--debug', action='store_true', help='write_log_enabled')
	parser.add_argument('--noTele', action='store_true', help='Disable Telegram messaging')
	opt = parser.parse_args()

	send_message(token_trays,quote(f"Test Reporter ON"),token_Tel)

	pd_dict = {'timestamp' : ['0'], 'L1_qty_hr' : ['0'],'L1_qty_dai' : ['0'],'L1_tests_hr' : ['0'],'L1_tests_dai' : ['0'], 'L2_qty_hr' : ['0'],'L2_qty_dai' : ['0'],'L2_tests_hr' : ['0'],'L2_tests_dai' : ['0']}


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
	plc1_netid =  '10.65.96.38.1.1'
	plc2_netid =  '10.65.96.102.1.1'
	#plc3_netid =  '10.65.96.88.1.1'
	#plc_torre_netid = '10.65.68.130.1.1'
	plc1_ip =  '10.65.96.38'
	plc2_ip =  '10.65.96.102'
	#plc3_ip =  '10.65.96.88'
	#plc_torre_ip = '10.65.68.130'
	
	
	try:
		pyads.open_port()
		ams_net_id = pyads.get_local_address().netid
		print(ams_net_id)
		pyads.close_port()
	except:
		print("Failed to open AMD router, verify that you have installed TwinCAT")
		sys.exit()
		
	PLC_thread1 = Thread(name="hilo_PLC1",target=PLC_comms1, args=(PLC_1_queue_i,PLC_1_queue_o,plc1_ip,plc1_netid),daemon=True)
	PLC_thread2 = Thread(name="hilo_PLC2",target=PLC_comms2, args=(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid),daemon=True)
	#PLC_thread3 = Thread(name="hilo_PLC3",target=PLC_comms3, args=(PLC_3_queue_i,PLC_3_queue_o,plc3_ip,plc3_netid),daemon=True)
	#PLC_thread4 = Thread(name="hilo_PLC4",target=PLC_comms4, args=(PLC_4_queue_i,PLC_4_queue_o,plc_torre_ip,plc_torre_netid),daemon=True)
	#weather_thread = Thread(name="clima",target=weather_data, args=(PLC_5_queue_i,PLC_5_queue_o),daemon=True)
	
	PLC_thread1.start()
	PLC_thread2.start()
	#PLC_thread3.start()
	#PLC_thread4.start()
	#weather_thread.start()

	monitor_thread = Thread(target=watchdog_t, args=(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i),daemon=True)
	monitor_thread.start()

	process_coordinator()

	monitor_thread.join()
	PLC_thread1.join()
	PLC_thread2.join()
	#PLC_thread3.join()
	#PLC_thread4.join()
	#weather_thread.join()

	