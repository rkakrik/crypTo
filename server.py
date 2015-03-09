#!/usr/bin/env python3

import os
import signal
from uuid import uuid4
import asyncio
import aiomcache
from aiohttp import web

# TODO: num or hash in link vs uuid
# TODO: simple material design
# TODO: send only hash and encrypted data as string
# TODO: short link (disable message)
# TODO: english translations
# TODO: logo animation
# TODO: add unix-socket
# TODO: add args

baseTemplate = '''
	<!DOCTYPE html>
	<html>
		<head>
		<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
		<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
		<style type="text/css">
		body {{text-shadow: 1px 1px 1px #444;
			max-width: 500px; margin-left: auto; margin-right: auto;
			font: 22px sans; background: #555; color: #D3D3D3;}}
		a {{color: #585858; display: block; background: #FFCC02;
			text-shadow: 1px 1px 1px #FFE477; box-shadow: 1px 1px 1px #3D3D3D; 
			padding: 10px 25px 10px 25px; margin-bottom: 1em; text-align: center;}}
		a:hover {{color: #333; background: #EBEBEB;}}
		h1 {{text-align: center;}}
		input[type="password"], textarea {{padding: 5px 0 5px 0; margin-bottom: 1em;
			color: #525252; border: none; width: 100%; outline: 0 none; 
			background: #DFDFDF; line-height:15px;}}
		textarea {{height: 300px;}}
		input[type="submit"], input[type="button"] {{width: 100%; 
			background: #FFCC02; border: none; margin-bottom: 1em;
			color: #585858; text-shadow: 1px 1px 1px #FFE477; font-weight: bold;
			box-shadow: 1px 1px 1px #3D3D3D; padding: 10px 25px 10px 25px;}}
		input[type="submit"]:hover, input[type="button"]:hover 
			{{color: #333; background: #EBEBEB;}}
		</style>
		<title>CrypTo</title>
		</head>
		<body>
			<a href="/"><h1>CrypTo</h1></a>
			{body}
		</body>
	</html>
'''

@asyncio.coroutine
def indexHTML(request):
	body = '''
		<p>КрипТо - это анонимная система шифрованных временных сообщений.</p>
		<p>Текст шифруется и дешифруется паролем на стороне пользователя,
		посылая на сервер лишь кучку символов. После прочтения сообщение сразу 
		удаляется с сервера.</p>
		<p>Чтобы оставить сообщение, нажмите на кнопку внизу и впишите на 
		открывшейся странице пароль и текст сообщения. Затем нажмите на кнопку
		"Сохранить". Сервер покажет уникальную ссылку, которую нужно отправить 
		любым способом другому человеку, которому требуется прочитать это сообщение.
		Пароль желательно сообщить этому человеку через отдельные каналы связи.</p>
		<a href="/message">Написать сообщение</a>
	'''
	html = baseTemplate.format(body=body)
	return web.Response(body=html.encode('utf-8'))


@asyncio.coroutine
def newMessageForm(request):
	body = '''
		<input type="password" name="password" id="password" placeholder="Пароль">
		<textarea name="text" id="text" placeholder="Введите текст"></textarea><br/>
		<form action="/message" method="post">
			<input name="encrypted" id="encrypted" type="hidden"></textarea>
			<input name="encrypt" id="encrypt" type="submit" value="Сохранить" />
		</form>
		<script type="text/javascript" src="/static/sjcl.js"></script>
		<script type="text/javascript">
			var passwordField = document.getElementById("password"),
				textField = document.getElementById("text"),
				encryptedField = document.getElementById("encrypted"),
				encryptButton = document.getElementById("encrypt");
			encryptButton.onclick = function() {{
			  if(!passwordField.value) {{
			    alert("Введите пароль");
			  }} else if(!textField.value) {{
			    alert("Введите текст");
			  }} else {{
			     encryptedField.value = 
			       sjcl.encrypt(
			         passwordField.value, textField.value
			       );
			  }}
			}};
		</script>
	'''
	html = baseTemplate.format(body=body)
	return web.Response(body=html.encode('utf-8'))


@asyncio.coroutine
def newMessage(request):
	data = yield from request.post()
	uuid = str(uuid4())
	yield from request.app.memcache.set(uuid.encode('utf-8'), data['encrypted'].encode('utf-8'))
	body = '''
		<h1>Ссылка: <a href="/message/{uuid}">{uuid}</a></h1>
		<a href="whatsapp://send?text=CrypTo%3A%20http%3A%2F%2Fcrypto.peacedata.ae/message/{uuid}">
		Отправить ссылку по Whatsapp</a>
		<a href="sms:?body=CrypTo%3A%20http%3A%2F%2Fcrypto.peacedata.ae/message/{uuid}">
		Отправить ссылку по SMS</a>
	'''.format(uuid=uuid)
	html = baseTemplate.format(body=body)
	return web.Response(body=html.encode('utf-8'))


@asyncio.coroutine
def showMessage(request):
	uuid = request.match_info.get('uuid', '')
	message = yield from request.app.memcache.get(uuid.encode('utf-8'))
	if message:
		body = '''
			<input type="password" name="password" id="password" placeholder="Пароль">
			<input name="decrypt" id="decrypt" type="button" value="Расшифровать"/><br/>
			<textarea name="decrypted" id="decrypted"></textarea><br/>
			<script type="text/javascript" src="/static/sjcl.js"></script>
			<script type="text/javascript">
				var passwordField = document.getElementById("password"),
					decryptButton = document.getElementById("decrypt"),
					decryptedField = document.getElementById("decrypted");
				decryptButton.onclick = function() {{
				  if(!passwordField.value) {{
				    alert("Введите пароль");
				  }} else {{
				     try {{
				       decryptedField.value = sjcl.decrypt(
				         passwordField.value,
				         '{message}'
				       );
				     }} catch (e) {{
				       alert("Can't decrypt: " + e);
				     }}
				  }}
				}};
			</script>
		'''.format(message=message.decode('utf-8'))
		html = baseTemplate.format(body=body)
		yield from request.app.memcache.delete(uuid.encode('utf-8'))
		return web.Response(body=html.encode('utf-8'))
	else:
		raise web.HTTPNotFound()


@asyncio.coroutine
def init(loop):
	app = web.Application(loop=loop)
	app.memcache = aiomcache.Client('127.0.0.1', 11211, loop=loop)
	app.router.add_static('/static', 'static/')
	app.router.add_route('GET', '/', indexHTML)
	app.router.add_route('GET', '/message', newMessageForm)
	app.router.add_route('POST', '/message', newMessage)
	app.router.add_route('GET', '/message/{uuid}', showMessage)

	srv = yield from loop.create_server(app.make_handler(), '0.0.0.0', 8080)
	print('serving on', srv.sockets[0].getsockname())
	return srv

loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGINT, loop.stop)


loop.run_until_complete(init(loop))
try:
    loop.run_forever()
finally:
	loop.close()