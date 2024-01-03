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
from dotenv import load_dotenv

load_dotenv()
token_Tel = os.getenv('API_KEY')

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


def write_log(i_gwk_temp,i_part_number,i_part_number2,i_part_number3,status1,status2,status3,i_temp_torre,i_bomba1,i_bomba2,i_temp,i_humidity,i_pressure):
	now = datetime.now()
	dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
	#print("date and time =", dt_string)	
	mis_docs = My_Documents(5)
	pd_ruta = str(mis_docs)+ r"\registro_agua.csv"
	pd_file_exists = os.path.exists(pd_ruta)
	
	#check if pandas DataFrame exists to load the stuff or to create with dummy data.
	if pd_file_exists:
		pd_log = pd.read_csv(pd_ruta)
	else:
		pd_log = pd.DataFrame(pd_dict)

	new_row = {'timestamp' : [dt_string], 'temp_adentro' : [i_gwk_temp], 'ITW1_PN' : [i_part_number], 'ITW2_PN' : [i_part_number2], 'ITW3_ON' : [i_part_number3], 'ITW1_Auto' : [status1], 'ITW2_Auto' : [status2], 'ITW3_Auto' : [status3],'Temp_Torre' : [i_temp_torre], 'Bomba_1' : [i_bomba1], 'Bomba_2' : [i_bomba2], 'Clima_Temp' : [i_temp], 'Clima_Humedad' : [i_humidity], 'Clima_Presion' : [i_pressure]}
	new_row_pd = pd.DataFrame(new_row)
	pd_concat = pd.concat([pd_log,new_row_pd])
	pd_concat.to_csv(pd_ruta,index=False)

		

def watchdog_t(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i,PLC_3_queue_i,PLC_4_queue_i):
	while True:
		stop_signal = input()
		if stop_signal == "T":
			PLC_1_queue_i.put(None)
			PLC_2_queue_i.put(None)
			PLC_3_queue_i.put(None)
			PLC_4_queue_i.put(None)
			PLC_5_queue_i.put(None)
			shutdown_queue.put(None)
		break


def PLC_comms1(PLC_1_queue_i,PLC_1_queue_o,plc1_ip,plc1_netid):
	print('++++++++++++++++++++++++++++++++++ PLC1: Running')

	try:
		plc1=pyads.Connection(plc1_netid,801,plc1_ip)
		plc1.open()
		plc1.set_timeout(2000)
		gwk_temp = plc1.get_handle('.GWK_Tank1_Temperature_d_degree')
		part_number = plc1.get_handle('.TP_IW_Recipe_name')
		status_handle = plc1.get_handle('.Running_Automatic_SCADA')

	
	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc1,gwk_temp,part_number,status_handle = aux_PLC_comms(plc1_ip,plc1_netid)
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
			plc1.release_handle(gwk_temp)
			plc1.release_handle(part_number)
			plc1.release_handle(status_handle)
			print(f"handles1 released")
			plc1.close()
			PLC_1_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			plc1_num_parte= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=part_number)
			plc1_temp= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=gwk_temp)
			plc1_stat= plc1.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=status_handle)
			
			# send the data over the queue
			PLC_1_queue_o.put((plc1_temp,plc1_num_parte,plc1_stat))
			time.sleep(4)


		except Exception as e:
			print(f"Could not update in PLC: error {e}")
			plc1,gwk_temp,part_number,status_handle = aux_PLC_comms(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc1=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc1.open()
			gwk_temp = plc1.get_handle('.GWK_Tank1_Temperature_d_degree')
			part_number = plc1.get_handle('.TP_IW_Recipe_name')
			status_handle = plc1.get_handle('.Running_Automatic_SCADA')
		except:	
			print(f"Auxiliary PLC_1: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc1.open()
			print("Success PLC_L1")
			return plc1,gwk_temp,part_number,status_handle





def PLC_comms2(PLC_2_queue_i,PLC_2_queue_o,plc2_ip,plc2_netid):
	print('++++++++++++++++++++++++++++++++++ PLC2: Running')

	try:
		plc2=pyads.Connection(plc2_netid,801,plc2_ip)
		plc2.open()
		plc2.set_timeout(2000)
		part_number = plc2.get_handle('.TP_IW_Recipe_name')
		status_handle = plc2.get_handle('.Running_Automatic_SCADA')

	
	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc2,part_number,status_handle = aux_PLC_comms_2(plc2_ip,plc2_netid)
	while True:
		# get a unit of work
		try:
			item2 = PLC_2_queue_i.get(block=False)
		except:
			item2='0000'
			pass

		# check for stop
		if item2 is None:
			#PLC release and break
			plc2.release_handle(part_number)
			plc2.release_handle(status_handle)
			print(f"handles2 released")
			plc2.close()
			PLC_2_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			plc2_num_parte= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=part_number)
			plc2_stat= plc2.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=status_handle)
			
			# send the data over the queue
			PLC_2_queue_o.put((plc2_num_parte,plc2_stat))
			time.sleep(4)


		except Exception as e:
			print(f"Could not update in PLC: error {e}")
			plc2,part_number,status_handle = aux_PLC_comms_2(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms_2(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc2=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc2.open()
			part_number = plc2.get_handle('.TP_IW_Recipe_name')
			status_handle = plc2.get_handle('.Running_Automatic_SCADA')
		except:	
			print(f"Auxiliary PLC_2: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc2.open()
			print("Success PLC_L2")
			return plc2,part_number,status_handle


def PLC_comms3(PLC_3_queue_i,PLC_3_queue_o,plc3_ip,plc3_netid):
	print('++++++++++++++++++++++++++++++++++ PLC3: Running')

	try:
		plc3=pyads.Connection(plc3_netid,801,plc3_ip)
		plc3.open()
		plc3.set_timeout(3000)
		part_number = plc3.get_handle('.TP_IW_Recipe_name')
		status_handle = plc3.get_handle('.Running_Automatic_SCADA')

	
	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc3,part_number,status_handle = aux_PLC_comms_3(plc3_ip,plc3_netid)
	while True:
		# get a unit of work
		try:
			item3 = PLC_3_queue_i.get(block=False)
		except:
			item3='0000'
			pass

		# check for stop
		if item3 is None:
			#PLC release and break
			plc3.release_handle(part_number)
			plc3.release_handle(status_handle)
			print(f"handles3 released")
			plc3.close()
			PLC_3_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			plc3_num_parte= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_STRING,handle=part_number)
			plc3_stat= plc3.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=status_handle)
			
			# send the data over the queue
			PLC_3_queue_o.put((plc3_num_parte,plc3_stat))
			time.sleep(4)


		except Exception as e:
			print(f"Could not update in PLC: error {e}")
			plc3,part_number,status_handle = aux_PLC_comms_3(plc1_ip,plc1_netid)
			continue


def aux_PLC_comms_3(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc3=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc3.open()
			part_number = plc3.get_handle('.TP_IW_Recipe_name')
			status_handle = plc3.get_handle('.Running_Automatic_SCADA')
		except:	
			print(f"Auxiliary PLC_3: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc3.open()
			print("Success PLC_L3")
			return plc3,part_number,status_handle



def PLC_comms4(PLC_4_queue_i,PLC_4_queue_o,plc4_ip,plc4_netid):
	print('++++++++++++++++++++++++++++++++++ PLC_Torre: Running')

	try:
		plc4=pyads.Connection(plc4_netid,801,plc4_ip)
		plc4.open()
		tower_temp = plc4.get_handle('.TP_IW_Tank_Water_Temperatur_UINT')
		bomba_1_status = plc4.get_handle('.TP_LM_Process_Pump_1_BOOL')
		bomba_2_status = plc4.get_handle('.TP_LM_Process_Pump_2_BOOL')
	
	except Exception as e:
			print(f"Starting error: {e}")
			time.sleep(5)
			plc4,tower_temp,bomba_1_status,bomba_2_status = aux_PLC_comms_4(plc4_ip,plc4_netid)
	while True:
		# get a unit of work
		try:
			item4 = PLC_4_queue_i.get(block=False)
		except:
			item4='0000'
			pass

		# check for stop
		if item4 is None:
			#PLC release and break
			plc4.release_handle(tower_temp)
			plc4.release_handle(bomba_1_status)
			plc4.release_handle(bomba_2_status)			
			print(f"handles4 released")
			plc4.close()
			PLC_4_queue_i.task_done()
			break

		#it's time to work.
		try:
			#Normal program execution
			plc4_temp_torre= plc4.read_by_name("", plc_datatype=pyads.PLCTYPE_UINT,handle=tower_temp)
			plc4_bomba1 = plc4.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=bomba_1_status)
			plc4_bomba2 = plc4.read_by_name("", plc_datatype=pyads.PLCTYPE_BOOL,handle=bomba_2_status)
			
			# send the data over the queue
			PLC_4_queue_o.put((plc4_temp_torre,plc4_bomba1,plc4_bomba2))
			time.sleep(4)


		except Exception as e:
			print(f"Could not update in PLC: error {e}")
			plc4,tower_temp,bomba_1_status,bomba_2_status = aux_PLC_comms_4(plc4_ip,plc4_netid)
			continue


def aux_PLC_comms_4(plc_address_aux,plc_netid_aux):

	while True:
		try:
			plc4=pyads.Connection(plc_netid_aux, 801,plc_address_aux)
			plc4.open()
			tower_temp = plc4.get_handle('.TP_IW_Tank_Water_Temperatur_UINT')
			bomba_1_status = plc4.get_handle('.TP_LM_Process_Pump_1_BOOL')
			bomba_2_status = plc4.get_handle('.TP_LM_Process_Pump_2_BOOL')
		except:	
			print(f"Auxiliary PLC_Torre: Couldn't open")
			time.sleep(4)
			continue
		else:
			plc4.open()
			print("Success PLC_Torre")
			return plc4,tower_temp,bomba_1_status,bomba_2_status


def weather_data(PLC_5_queue_i,PLC_5_queue_o):
	print('++++++++++++++++++++++++++++++++++ Weather_Report: Running')
	# base URL
	#lat=26.8802393&lon=-101.4611757&appid=6d50895f204f425bae667859e605045a
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
			response = requests.get(URL)
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
				#print(f"{CITY:-^30}")
				#print(f"Temperature: {temperature}")
				#print(f"Humidity: {humidity}")
				#print(f"Pressure: {pressure}")
				#print(f"Weather Report: {report[0]['description']}")
				#print(f"sale info {main['temp']}")
				prev_temp = 0
				prev_pressure = 0
				prev_hum = 0
				prev_temp = temperature
				prev_hum = humidity
				prev_pressure = pressure
				#print("updated weather")
			else:
				# showing the error message
				print("Error in the HTTP request")
				time.sleep(3)
				continue
		
		PLC_5_queue_o.put((prev_temp,prev_hum,prev_pressure))
		time.sleep(4)


		











def process_coordinator():

	i_gwk_temp = 0
	i_part_number = '0'
	i_part_number2 = '0'
	i_part_number3 = '0'
	status1 = False
	status2 = False
	status3 = False
	i_temp_torre = 0
	i_bomba1 = False
	i_bomba2 = False
	i_temp = 0
	i_humidity = 0
	i_pressure = 0
	
	while True:

		
		time.sleep(3)
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
			i_gwk_temp,i_part_number,status1 = PLC_1_queue_o.get(block=False)
			PLC_1_queue_o.task_done()
			print("recibido de L1")
			#i_gwk_temp,i_part_number,status1 = 0,'0','0'
		
		if PLC_2_queue_o.qsize()>0:
			i_part_number2,status2 = PLC_2_queue_o.get(block=False)
			PLC_2_queue_o.task_done()
			print("recibido de L2")

		if PLC_3_queue_o.qsize()>0:
			i_part_number3,status3 = PLC_3_queue_o.get(block=False)
			PLC_3_queue_o.task_done()
			print("recibido de L3")

		if PLC_4_queue_o.qsize()>0:
			i_temp_torre,i_bomba1,i_bomba2 = PLC_4_queue_o.get(block=False)
			PLC_4_queue_o.task_done()
			print("recibido de L4")
		
		if PLC_5_queue_o.qsize()>0:
			i_temp,i_humidity,i_pressure = PLC_5_queue_o.get(block=False)
			PLC_5_queue_o.task_done()
			print("recibido de L5")


		print(f"Info recibida {i_gwk_temp} {i_part_number2} {i_part_number3} {i_temp_torre} {i_temp}")
		write_log(i_gwk_temp,i_part_number,i_part_number2,i_part_number3,status1,status2,status3,i_temp_torre,i_bomba1,i_bomba2,i_temp,i_humidity,i_pressure)
		"""
		i_gwk_temp = 0
		i_part_number = '0'
		i_part_number2 = '0'
		i_part_number3 = '0'
		status1 = False
		status2 = False
		status3 = False
		i_temp_torre = 0
		i_bomba1 = False
		i_bomba2 = False
		i_temp = 0
		i_humidity = 0
		i_pressure = 0
		"""		
		#print(f"Stats de las queue input {PLC_1_queue_i.qsize()}, {PLC_2_queue_i.qsize()},{PLC_3_queue_i.qsize()},{PLC_4_queue_i.qsize()},{PLC_5_queue_i.qsize()}")
		print(f"Stats de las queue output {PLC_1_queue_o.qsize()}, {PLC_2_queue_o.qsize()},{PLC_3_queue_o.qsize()},{PLC_4_queue_o.qsize()},{PLC_5_queue_o.qsize()}")



if __name__ == '__main__':

	pd_dict = {'timestamp' : ['dumy'], 'temp_adentro' : ['dumy'], 'ITW1_PN' : ['dumy'], 'ITW2_PN' : ['dumy'], 'ITW3_ON' : ['dumy'], 'ITW1_Auto' : ['dumy'], 'ITW2_Auto' : ['dumy'], 'ITW3_Auto' : ['dumy'],'Temp_Torre' : ['dumy'], 'Bomba_1' : ['dumy'], 'Bomba_2' : ['dumy'], 'Clima_Temp' : ['dumy'], 'Clima_Humedad' : ['dumy'], 'Clima_Presion' : ['dumy']}
	

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
	plc2_netid =  '10.65.96.70.1.1'
	plc1_netid =  '10.65.96.73.1.1'
	plc3_netid =  '10.65.96.88.1.1'
	plc_torre_netid = '10.65.68.130.1.1'
	plc2_ip =  '10.65.96.70'
	plc1_ip =  '10.65.96.73'
	plc3_ip =  '10.65.96.88'
	plc_torre_ip = '10.65.68.130'
	
	
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
	PLC_thread3 = Thread(name="hilo_PLC3",target=PLC_comms3, args=(PLC_3_queue_i,PLC_3_queue_o,plc3_ip,plc3_netid),daemon=True)
	PLC_thread4 = Thread(name="hilo_PLC4",target=PLC_comms4, args=(PLC_4_queue_i,PLC_4_queue_o,plc_torre_ip,plc_torre_netid),daemon=True)
	weather_thread = Thread(name="clima",target=weather_data, args=(PLC_5_queue_i,PLC_5_queue_o),daemon=True)
	
	PLC_thread1.start()
	PLC_thread2.start()
	PLC_thread3.start()
	PLC_thread4.start()
	weather_thread.start()

	monitor_thread = Thread(target=watchdog_t, args=(shutdown_queue,PLC_1_queue_i,PLC_2_queue_i,PLC_3_queue_i,PLC_4_queue_i),daemon=True)
	monitor_thread.start()

	process_coordinator()

	monitor_thread.join()
	PLC_thread1.join()
	PLC_thread2.join()
	PLC_thread3.join()
	PLC_thread4.join()
	weather_thread.join()

	