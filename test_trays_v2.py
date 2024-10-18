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
import csv
load_dotenv()
token_trays = os.getenv('TRAYS')
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
		arr1_bool_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_2_OF_BOOL')
		arr1_int_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_5_OF_INTEGER')
		arr1_str_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_2_OF_STRING')
		hr_counter_handle = plc1.get_handle('.Test_Trays_hour_UINT')
		dai_counter_handle = plc1.get_handle('.Test_Trays_dai_UINT')
		amount_test_dai_handle = plc1.get_handle('.Test_Sent_dai_UINT')
		amount_test_hr_handle = plc1.get_handle('.Test_Sent_hour_UINT')


	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc1,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms(plc1_ip,plc1_netid)
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
			plc1.release_handle(arr1_bool_handle)
			plc1.release_handle(arr1_int_handle)
			plc1.release_handle(arr1_str_handle)		

			print(f"handles1 released")
			plc1.close()
			PLC_1_queue_i.task_done()
			break

		#it's time to work.
		try:

			bool_list = plc1.read_by_name('MAIN.Setup_Status_Array_1_2_OF_BOOL', pyads.PLCTYPE_BOOL * 2,handle=arr1_bool_handle)
			int_list = plc1.read_by_name('MAIN.Setup_Status_Array_1_5_OF_INTEGER', pyads.PLCTYPE_INT * 6,handle=arr1_int_handle)
			str_list = bytearray(plc1.read_by_name('MAIN.Setup_Status_Array_1_2_OF_STRING', pyads.PLCTYPE_BYTE * 18)).decode().replace("\x00\x00",",")

			bool_list.extend(int_list)
			bool_list.extend(str_list.split(","))

			print(bool_list)
			PLC_1_queue_o.put(((bool_list[0]),(bool_list[1]),(bool_list[2]),(bool_list[3]),(bool_list[4]),(bool_list[5]),(bool_list[6]),(bool_list[7]),(bool_list[8]),(bool_list[9])))
			time.sleep(90)


		except Exception as e:
			print(f"Could not update in PLC1: error {e}")
			plc1,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc1=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc1.open()
			arr1_bool_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_2_OF_BOOL')
			arr1_int_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_5_OF_INTEGER')
			arr1_str_handle = plc1.get_handle('MAIN.Setup_Status_Array_1_2_OF_STRING')
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
			return plc1,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle
		



def PLC_comms2(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid):
	print('++++++++++++++++++++++++++++++++++ PLC2: Running')
	try:
		plc2=pyads.Connection(plc2_netid,801,plc2_ip)
		plc2.open()
		plc2.set_timeout(2000)
		arr1_bool_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_2_OF_BOOL')
		arr1_int_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_5_OF_INTEGER')
		arr1_str_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_2_OF_STRING')
		hr_counter_handle = plc2.get_handle('.Test_Trays_hour_UINT')
		dai_counter_handle = plc2.get_handle('.Test_Trays_dai_UINT')
		amount_test_dai_handle = plc2.get_handle('.Test_Sent_dai_UINT')
		amount_test_hr_handle = plc2.get_handle('.Test_Sent_hour_UINT')


	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc2,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms2(plc2_ip,plc2_netid)
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
			plc2.release_handle(arr1_bool_handle)
			plc2.release_handle(arr1_int_handle)
			plc2.release_handle(arr1_str_handle)		

			print(f"handles2 released")
			plc2.close()
			PLC_2_queue_i.task_done()
			break

		#it's time to work.
		try:

			bool_list = plc2.read_by_name('SCADA_System.Setup_Status_Array_1_2_OF_BOOL', pyads.PLCTYPE_BOOL * 2,handle=arr1_bool_handle)
			int_list = plc2.read_by_name('SCADA_System.Setup_Status_Array_1_5_OF_INTEGER', pyads.PLCTYPE_INT * 6,handle=arr1_int_handle)
			str_list = bytearray(plc2.read_by_name('SCADA_System.Setup_Status_Array_1_2_OF_STRING', pyads.PLCTYPE_BYTE * 18)).decode().replace("\x00\x00",",")

			"""
			bool_list.append(int_list[0])
			bool_list.append(int_list[1])
			bool_list.append(int_list[2])
			bool_list.append(int_list[3])
			bool_list.append(int_list[4])
			bool_list.append(int_list[5])
			bool_list.append(str_list[0])
			bool_list.append(str_list[1])
			bool_list.append(str_list[2])
			"""
			bool_list.extend(int_list)
			bool_list.extend(str_list.split(","))
			#process a list to store the items.

			print(bool_list)
			#print(int_list)
			#print(str_list)

			PLC_2_queue_o.put(((bool_list[0]),(bool_list[1]),(bool_list[2]),(bool_list[3]),(bool_list[4]),(bool_list[5]),(bool_list[6]),(bool_list[7]),(bool_list[8]),(bool_list[9])))
			time.sleep(90)


		except Exception as e:
			print(f"Could not update in plc2: error {e}")
			plc2,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle = aux_PLC_comms2(plc2_ip,plc2_netid)
			continue


def aux_PLC_comms2(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc2=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc2.open()
			arr1_bool_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_2_OF_BOOL')
			arr1_int_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_5_OF_INTEGER')
			arr1_str_handle = plc2.get_handle('SCADA_System.Setup_Status_Array_1_2_OF_STRING')
			hr_counter_handle = plc2.get_handle('.Test_Trays_hour_UINT')
			dai_counter_handle = plc2.get_handle('.Test_Trays_dai_UINT')
			amount_test_dai_handle = plc2.get_handle('.Test_Sent_dai_UINT')
			amount_test_hr_handle = plc2.get_handle('.Test_Sent_hour_UINT')
		except:	
			print(f"Auxiliary PLC_2: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc2.open()
			print("Success PLC_L2")
			return plc2,arr1_bool_handle,arr1_int_handle,arr1_str_handle,hr_counter_handle,dai_counter_handle,amount_test_hr_handle,amount_test_dai_handle











def restore_data():

	"""Restore the integer data"""
	ruta_state = resource_path("images/backups.csv")
	file_exists = os.path.exists(ruta_state)
	if file_exists == True:
		pass
	else:
		with open(ruta_state,"w+") as f:
			f.write(f"{str('False')},{str('False')},{int(0)},{int(0)},{str('s')},{str('s')},{str('False')},{str('False')},{int(0)},{int(0)},{str('s')},{str('s')}")		
		return False,False,0,0,'s','s',False,False,0,0,'s','s'

	with open(resource_path("images/backups.csv")) as file:
		type(file)
		csvreader = csv.reader(file)
		rows2 = []
		for row in csvreader:
			rows2.append(row)
		
		i_FMB12_status = eval(str(rows2[0][0]))
		i_FUL103_status = eval(str(rows2[0][1]))
		i_FMB12_time = int(rows2[0][2])
		i_FUL103_time = int(rows2[0][3])
		i_FMB12_PN = str(rows2[0][4])
		i_FUL103_PN  = str(rows2[0][5])
		i_FMB1_status = eval(str(rows2[0][6]))
		i_FMB46_status = eval(str(rows2[0][7]))
		i_FMB1_time = int(rows2[0][8])
		i_FMB46_time = int(rows2[0][9])
		i_FMB1_PN  = str(rows2[0][10])
		i_FMB46_PN = str(rows2[0][11])

		return i_FMB12_status,i_FUL103_status,i_FMB12_time,i_FUL103_time,i_FMB12_PN,i_FUL103_PN,i_FMB1_status,i_FMB46_status,i_FMB1_time,i_FMB46_time,i_FMB1_PN,i_FMB46_PN

def save_data(i_FMB12_status,i_FUL103_status,i_FMB12_time,i_FUL103_time,i_FMB12_PN,i_FUL103_PN,i_FMB1_status,i_FMB46_status,i_FMB1_time,i_FMB46_time,i_FMB1_PN,i_FMB46_PN):
	ruta_state = resource_path("images/backups.csv")
	with open(ruta_state, "w+") as file_object:
		file_object.write(f"{str(i_FMB12_status)},{str(i_FUL103_status)},{int(i_FMB12_time)},{int(i_FUL103_time)},{str(i_FMB12_PN)},{str(i_FUL103_PN)},{str(i_FMB1_status)},{str(i_FMB46_status)},{int(i_FMB1_time)},{int(i_FMB46_time)},{str(i_FMB1_PN)},{str(i_FMB46_PN)}")		

def process_coordinator():

	
	# i_ are variables that will receive the info from the queues
	# n_ are variables that will be saved and restored, then compared with the i_ ones to look for differences and report them.
	i_FMB12_status,i_FUL103_status,i_FMB12_time,i_FUL103_time,i_FMB12_PN,i_FUL103_PN = False,False,0,0,'s','s'

	i_FMB1_status,i_FMB46_status,i_FMB1_time,i_FMB46_time,i_FMB1_PN,i_FMB46_PN = False,False,0,0,'s','s'

	n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN = False,False,0,0,'s','s'

	n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN = False,False,0,0,'s','s'

	i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai,i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai = 0,0,0,0,0,0,0,0

	n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN = restore_data()

	received_1 = False
	received_2 = False

	L1_shift_setup_time = 0
	L2_shift_setup_time = 0
	
	FUL103_time_list =[]
	FUL103_time_index =0
	
	FMB12_time_list =[]
	FMB12_time_index =0
	
	FMB46_time_list =[]
	FMB46_time_index =0
	
	FMB1_time_list =[]
	FMB1_time_index =0
		
	L1_day_setup_time = 0
	L2_day_setup_time = 0


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
			i_FMB12_status,i_FUL103_status,i_FMB12_time,i_FUL103_time,i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai,i_FMB12_PN,i_FUL103_PN = PLC_1_queue_o.get(block=False)
			PLC_1_queue_o.task_done()
			received_1 = True
			print("recibido de L1")

		if PLC_2_queue_o.qsize()>0:
			i_FMB46_status,i_FMB1_status,i_FMB46_time,i_FMB1_time,i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai,i_FMB1_PN,i_FMB46_PN = PLC_2_queue_o.get(block=False)
			PLC_2_queue_o.task_done()
			print("recibido de L2")
			received_2 = True
	
		if opt.save_data and received_1 and received_2:
			print(f"Info recibida. {i_FMB12_status},{i_FUL103_status},{i_FMB12_time},{i_FUL103_time},{i_FMB1_status},{i_FMB46_status},{i_FMB1_time},{i_FMB46_time} Remaining {PLC_1_queue_o.qsize()}/{PLC_2_queue_o.qsize()}")
			write_log(i_L1_qty_hr,i_L1_qty_dai,i_L1_tests_hr,i_L1_tests_dai,i_L2_qty_hr,i_L2_qty_dai,i_L2_tests_hr,i_L2_tests_dai)
			received_2 = False
			received_1 = False
		else:
			print("continue cycle no reads")
			time.sleep(30)
			continue
		now = datetime.now()

		if hour != int(now.strftime("%H")):
			
			total_hr = i_L1_qty_hr + i_L1_tests_hr + i_L2_qty_hr + i_L2_tests_hr

			if total_hr > 0:
				send_message(Jorge_Morales,quote(f" Reporte de Pruebas hora {hour}: \nL1 charolas: {i_L1_qty_hr} \nL1 pruebas: {i_L1_tests_hr} \n-- \nL2 charolas: {i_L2_qty_hr} \nL2 pruebas: {i_L2_tests_hr}"),token_Tel)
				send_message(Jorge_Morales,quote(f" Acumulado día: \nL1 charolas: {i_L1_qty_dai} \nL1 pruebas: {i_L1_tests_dai} \n** \nL2 charolas: {i_L2_qty_dai} \nL2 pruebas: {i_L2_tests_dai}"),token_Tel)
			# comando de borrado
			#PLC_1_queue_i.put((True,False))
			#PLC_2_queue_i.put((True,False))
			print(f"hora es {hour}")
			#Reporte de fin de turno.
			if int(now.strftime("%H")) == 7 or int(now.strftime("%H")) == 17 : 
				#Report and erase total setup
				send_message(Jorge_Morales,quote(f"Acumulado Turno {hour}:00 - {hour+1}:00  \nFMB46: {int(sum(FMB46_time_list)) + n_FMB46_time} \nFMB01: {int(sum(FMB1_time_list)) + n_FMB1_time} \nFMB12: {(int(sum(FMB12_time_list)) + n_FMB12_time)} \nFUL103: {int(sum(FUL103_time_list)) + n_FUL103_time}"),token_Tel)
				FUL103_time_list.clear()
				FMB12_time_list.clear()
				FMB46_time_list.clear()
				FMB1_time_list.clear()
		
			hour = int(now.strftime("%H"))

		if dai != int(now.strftime("%d")):
						# comando de borrado
			#PLC_1_queue_i.put((True,True))
			#PLC_2_queue_i.put((True,True))
			dai = int(now.strftime("%d"))

		#step 1: Compare the information.
		# If the n_PN is 's', then that means that is the first time this software executes and it will fill only without comparing.


		if n_FMB12_PN == 's' and received_1 and received_2:
			#updating the values:
			n_FMB12_PN = i_FMB12_status
			n_FMB12_PN = i_FMB12_PN
			n_FMB12_time = i_FMB12_time
			n_FUL103_PN = i_FUL103_status
			n_FUL103_PN = i_FUL103_PN
			n_FUL103_time = i_FUL103_time	
			n_FMB1_PN = i_FMB1_status
			n_FMB1_PN = i_FMB1_PN
			n_FMB1_time = i_FMB1_time		
			n_FMB46_PN = i_FMB46_status
			n_FMB46_PN = i_FMB46_PN
			n_FMB46_time = i_FMB46_time
			#first time
			save_data(n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN)
			continue

		# FMB-12
		if n_FMB12_status != i_FMB12_status:
			#It's different
			if i_FMB12_status:
				send_message(Jorge_Morales,quote(f"Ha iniciado el setup en FMB12 con NP {i_FMB12_PN}"), token_Tel)
			else:
				send_message(Jorge_Morales,quote(f"Ha terminado el setup en FMB12: \nNP {n_FMB12_PN} \nTiempo: {n_FMB12_time} minutos"), token_Tel)
				FMB12_time_list.append(int(n_FMB12_time))
			#update the info
			n_FMB12_status = i_FMB12_status
			n_FMB12_PN = i_FMB12_PN
			
			save_data(n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN)
		
		# FUL-103
		if n_FUL103_status != i_FUL103_status:
			#It's different
			if i_FUL103_status:
				send_message(Jorge_Morales,quote(f"Ha iniciado el setup en FUL103 con NP {i_FUL103_PN}"), token_Tel)
			else:
				send_message(Jorge_Morales,quote(f"Ha terminado el setup en FUL103: \nNP {n_FUL103_PN} \nTiempo: {n_FUL103_time} minutos"), token_Tel)
				FUL103_time_list.append(int(n_FUL103_time))
			#update the info
			n_FUL103_status = i_FUL103_status
			n_FUL103_PN = i_FUL103_PN
			
			save_data(n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN)

		# FMB1
		if n_FMB1_status != i_FMB1_status:
			#It's different
			if i_FMB1_status:
				send_message(Jorge_Morales,quote(f"Ha iniciado el setup en FMB1 con NP {i_FMB1_PN}"), token_Tel)
			else:
				send_message(Jorge_Morales,quote(f"Ha terminado el setup en FMB1: \nNP {n_FMB1_PN} \nTiempo: {n_FMB1_time} minutos"), token_Tel)
				FMB1_time_list.append(int(n_FMB1_time))
			#update the info
			n_FMB1_status = i_FMB1_status
			n_FMB1_PN = i_FMB1_PN
			
			save_data(n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN)

		# FMB46
		if n_FMB46_status != i_FMB46_status:
			#It's different
			#print(f"n {n_fmb4}")
			if i_FMB46_status:
				send_message(Jorge_Morales,quote(f"Ha iniciado el setup en FMB46 con NP {i_FMB46_PN}"), token_Tel)
			else:
				send_message(Jorge_Morales,quote(f"Ha terminado el setup en FMB46: \nNP {n_FMB46_PN} \nTiempo: {n_FMB46_time} minutos"), token_Tel)
				FMB46_time_list.append(int(n_FMB46_time))
			#update the info
			n_FMB46_status = i_FMB46_status
			n_FMB46_PN = i_FMB46_PN
			
			save_data(n_FMB12_status,n_FUL103_status,n_FMB12_time,n_FUL103_time,n_FMB12_PN,n_FUL103_PN,n_FMB1_status,n_FMB46_status,n_FMB1_time,n_FMB46_time,n_FMB1_PN,n_FMB46_PN)
		
		time.sleep(60)

		n_FMB12_time = i_FMB12_time
		n_FUL103_time = i_FUL103_time
		n_FMB1_time = i_FMB1_time
		n_FMB46_time = i_FMB46_time
		




if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('--save_data', action='store_true', help='write_log_enabled')
	parser.add_argument('--debug', action='store_true', help='write_log_enabled')
	parser.add_argument('--noTele', action='store_true', help='Disable Telegram messaging')
	opt = parser.parse_args()

	send_message(Jorge_Morales,quote(f"Test Reporter ON"),token_Tel)

	#
	pd_dict = {'timestamp' : ['0'], 'L1_qty_hr' : ['0'],'L1_qty_dai' : ['0'],'L1_tests_hr' : ['0'],'L1_tests_dai' : ['0'], 'L2_qty_hr' : ['0'],'L2_qty_dai' : ['0'],'L2_tests_hr' : ['0'],'L2_tests_dai' : ['0']}

	

# The three queues:
	PLC_1_queue_i = Queue()
	PLC_2_queue_i = Queue()
	
	PLC_1_queue_o = Queue()
	PLC_2_queue_o = Queue()
	
	shutdown_queue = Queue()

	# Var definition:
	plc1_netid =  '10.65.96.38.1.1'
	plc2_netid =  '10.65.96.102.1.1'
	plc1_ip =  '10.65.96.38'
	plc2_ip =  '10.65.96.102'
	
	
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

	PLC_thread1.start()
	PLC_thread2.start()

	monitor_thread = Thread(target=watchdog_t, args=(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i),daemon=True)
	monitor_thread.start()

	process_coordinator()

	monitor_thread.join()
	PLC_thread1.join()
	PLC_thread2.join()

	