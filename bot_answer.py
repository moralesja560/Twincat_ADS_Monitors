import os
import sys
from dotenv import load_dotenv
from urllib.request import Request, urlopen
import json
from urllib.parse import quote
from datetime import datetime
load_dotenv()
token_Tel = os.getenv('TOK_EN_BOT')
Jorge_Morales = os.getenv('JORGE_MORALES')
Paintgroup = os.getenv('PAINTLINE')

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

now = datetime.now()
day = 29
print(int(now.strftime("%d")))
if day != int(now.strftime("%d")):
	send_message(Paintgroup,quote(f"Hoy es {int(now.strftime(r'%d'))}, no es {day} "),token_Tel)