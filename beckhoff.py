import pyads

# create some constants for connection
CLIENT_NETID = "10.65.2.95.1.1"
CLIENT_IP = "10.51.112.79"
TARGET_IP = "10.65.96.38"
TARGET_USERNAME = "Administrator"
TARGET_PASSWORD = "1"
ROUTE_NAME = "SAL-AUTO-MORAJOCS"
TARGET_NETID = "10.65.96.38.1.1"


# add a new route to the target plc
# If you've already had connected this PC to the PLC through System Manager this step is not necessary.
# Please first try plc.open() before trying to add a new route.
pyads.open_port()
ams_net_id = pyads.get_local_address().netid
print(ams_net_id)


# connect to plc and open connection
# route is added automatically to client on Linux, on Windows use the TwinCAT router


plc = pyads.Connection(TARGET_NETID, 801,TARGET_IP)
plc.open()

# check the connection state
print(plc.read_state())

# PLC vars that are declared in the Global area (Allgemein,Touch_Panel_Allgemein, ASI_Strang, etc) are declared here using .varname,
# otherwise they are declared by stating their location first. Example: PB_Stueckzahl.Sensor_input. Be sure to check in the PLC how is your specific var declared.
# see examples below.

# read int value by name
#i = plc.read_by_name("GVL.int_val")

# write int value by name
#plc.write_by_name("GVL.real_val", 42.0)

# create a symbol that automatically updates to the plc value
#real_val = plc.get_symbol("GVL.real_val", auto_update=True)
#print(real_val.value)
#real_val.value = 5.0
#print(plc.read_by_name("GVL.real_val"))
bool_list = plc.read_by_name('MAIN.Setup_Status_Array_1_2_OF_BOOL', pyads.PLCTYPE_BOOL * 2)

str_list = bytearray(plc.read_by_name('MAIN.Setup_Status_Array_1_2_OF_STRING', pyads.PLCTYPE_BYTE * 18)).decode().replace("\x00\x00",",")
bool_list.extend(str_list.split(","))

print(bool_list)

# close connection
plc.close()